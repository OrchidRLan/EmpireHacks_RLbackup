"""Agent 2: Semantic Match Ranking.

Uses a single batched Claude call to score and rank a user's existing Match rows
by cross-referencing apartment style labels and neighborhood context with the
user's subjective and objective preferences. Updates match_score and
match_reasoning in place.
"""

import json
import uuid
from datetime import datetime
from typing import Optional

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing_extensions import TypedDict

from app.agents.shared.claude_client import MODEL, get_claude_client
from app.models.agent_logs import Agent2Log
from app.models.apartment import Apartment, NeighborInfo
from app.models.match import Match
from app.models.preferences import ObjectivePreferences, SubjectivePreferences


class Agent2State(TypedDict):
    user_id: str
    top_n: int
    user_profile: dict
    matches_data: list[dict]
    rankings: list[dict]
    error: Optional[str]


def build_agent2_graph(session: AsyncSession):
    """Build and compile an Agent 2 LangGraph. Session injected via closure.

    Args:
        session: An open AsyncSession. The caller is responsible for its lifecycle.

    Returns:
        A compiled LangGraph graph ready for ``ainvoke``.
    """

    async def fetch_user_context(state: Agent2State) -> dict:
        subj = (
            await session.execute(
                select(SubjectivePreferences)
                .where(SubjectivePreferences.user_id == state["user_id"])
                .limit(1)
            )
        ).scalar_one_or_none()
        obj = (
            await session.execute(
                select(ObjectivePreferences)
                .where(ObjectivePreferences.user_id == state["user_id"])
                .limit(1)
            )
        ).scalar_one_or_none()

        if not subj or not obj:
            return {
                "error": "User missing SubjectivePreferences or ObjectivePreferences"
            }
        return {
            "user_profile": {
                "image_labels": subj.image_labels or [],
                "neighborhood_labels": subj.neighborhood_labels or [],
                "priority_focus": subj.priority_focus,
                "min_budget": obj.min_budget,
                "max_budget": obj.max_budget,
                "bedroom_type": obj.bedroom_type,
            }
        }

    async def fetch_matches(state: Agent2State) -> dict:
        if state.get("error"):
            return {}

        result = await session.execute(
            select(Match)
            .where(Match.user_id == state["user_id"])
            .options(selectinload(Match.apartment))
            .order_by(Match.match_score.desc().nulls_first())
            .limit(state["top_n"])
        )
        matches = result.scalars().all()

        matches_data: list[dict] = []
        for m in matches:
            apt: Apartment | None = m.apartment
            if not apt:
                continue
            hood_name, hood_desc = "", ""
            if apt.neighbor_id:
                hood: NeighborInfo | None = await session.get(
                    NeighborInfo, apt.neighbor_id
                )
                if hood:
                    hood_name = hood.name
                    hood_desc = hood.description
            matches_data.append(
                {
                    "match_id": m.id,
                    "apartment_id": apt.id,
                    "name": apt.name,
                    "price": apt.price,
                    "bedroom_type": apt.bedroom_type,
                    "image_labels": apt.image_labels or [],
                    "neighborhood_name": hood_name,
                    "neighborhood_description": hood_desc,
                    "commute_minutes": m.commute_minutes,
                }
            )
        return {"matches_data": matches_data}

    async def call_claude_batch(state: Agent2State) -> dict:
        if state.get("error") or not state.get("matches_data"):
            return {"rankings": []}

        client = get_claude_client()
        profile = state["user_profile"]
        prompt = (
            "You are a NYC apartment matching expert.\n\n"
            "User profile:\n"
            f"- Budget: ${profile['min_budget']}-${profile['max_budget']}/mo\n"
            f"- Bedroom type: {profile['bedroom_type']}\n"
            f"- Priority: {profile.get('priority_focus', 'features')}\n"
            f"- Style preferences: {', '.join(profile['image_labels']) or 'none yet'}\n"
            f"- Neighborhood preferences: {', '.join(profile['neighborhood_labels']) or 'none yet'}\n\n"
            f"Apartments to rank:\n{json.dumps(state['matches_data'], indent=2)}\n\n"
            "Return ONLY a valid JSON array (no markdown), one object per apartment, sorted best-first:\n"
            '[{"apartment_id": "...", "score": 0.0-10.0, "reasoning": "one concise sentence"}]'
        )
        try:
            response = await client.messages.create(
                model=MODEL,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            rankings = json.loads(raw)
            return {"rankings": rankings}
        except Exception as exc:
            return {"error": str(exc), "rankings": []}

    async def persist_rankings(state: Agent2State) -> dict:
        for rank in state.get("rankings", []):
            apt_id = rank.get("apartment_id")
            score_raw = rank.get("score", 0)
            reasoning = rank.get("reasoning", "")
            # Normalize score from 0-10 scale to 0-1
            score = max(0.0, min(1.0, score_raw / 10.0))

            match_result = await session.execute(
                select(Match).where(
                    Match.user_id == state["user_id"],
                    Match.apartment_id == apt_id,
                )
            )
            match: Match | None = match_result.scalar_one_or_none()
            if match:
                match.match_score = round(score, 4)
                match.match_reasoning = reasoning

        rankings = state.get("rankings", [])
        reasoning_description = "; ".join(
            r["reasoning"] for r in rankings[:3] if r.get("reasoning")
        )
        if state.get("error"):
            result_dict = {"status": "error", "error": state.get("error")}
        else:
            result_dict = {
                "status": "success",
                "ranked_count": len(rankings),
                "reasoning_description": reasoning_description,
            }
        log = Agent2Log(
            id=str(uuid.uuid4()),
            user_id=state["user_id"],
            timestamp=datetime.utcnow(),
            result=json.dumps(result_dict),
        )
        session.add(log)
        await session.commit()
        return {}

    g: StateGraph = StateGraph(Agent2State)
    g.add_node("fetch_user_context", fetch_user_context)
    g.add_node("fetch_matches", fetch_matches)
    g.add_node("call_claude_batch", call_claude_batch)
    g.add_node("persist_rankings", persist_rankings)
    g.add_edge(START, "fetch_user_context")
    g.add_edge("fetch_user_context", "fetch_matches")
    g.add_edge("fetch_matches", "call_claude_batch")
    g.add_edge("call_claude_batch", "persist_rankings")
    g.add_edge("persist_rankings", END)
    return g.compile()


async def run_agent2(user_id: str, top_n: int = 20) -> None:
    """Entry point for background task. Creates its own DB session.

    Args:
        user_id: Primary key of the User to rank matches for.
        top_n: Maximum number of matches to rank in a single pass.
    """
    from app.database import async_session_factory

    async with async_session_factory() as session:
        graph = build_agent2_graph(session)
        initial_state: Agent2State = {
            "user_id": user_id,
            "top_n": top_n,
            "user_profile": {},
            "matches_data": [],
            "rankings": [],
            "error": None,
        }
        await graph.ainvoke(initial_state)
