"""Agent 3: Autonomous Negotiation.

Runs a full negotiation loop with apartment hosts via email:

1. Draft and send an opening inquiry email.
2. Poll the ``messages`` table for a host reply (type="host").
3. Claude analyzes the reply: "accepted" | "counter_offer" | "rejected" | "no_reply".
4. If counter_offer and rounds remain: draft a counter-email, send, poll again.
5. If accepted: generate an ICS calendar invite, email it, mark match completed,
   and notify the user.
6. If rejected or timeout: reset match to not_started and notify the user.

Host replies are simulated via the dev endpoint POST /agents/dev/matches/{id}/simulate-host-reply,
which inserts a Message(type="host") row that this agent polls.
"""

import asyncio
import json
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import TypedDict

from app.agents.shared.claude_client import MODEL, get_claude_client
from app.constants import AGENT3_MAX_ROUNDS, AGENT3_POLL_INTERVAL_S
from app.agents.shared.ics_generator import generate_ics
from app.agents.shared.smtp_client import send_email
from app.models.agent_logs import Agent3Log
from app.models.match import Match
from app.models.message import Message
from app.models.notification import Notification
from app.models.preferences import NegotiationPreferences
from app.models.user import User
from app.models.apartment import Apartment


class Agent3State(TypedDict):
    match_id: str
    # Loaded context
    match: dict
    apartment: dict
    user: dict
    negotiation_prefs: dict
    # Negotiation loop counters and history
    round_number: int
    max_rounds: int
    conversation_history: list[dict]  # [{role: "agent"|"host", text: str}]
    email_subject: str
    # Per-iteration data
    email_draft: Optional[str]
    host_reply: Optional[str]
    reply_analysis: Optional[str]  # "accepted" | "counter_offer" | "rejected" | "no_reply"
    agreed_datetime: Optional[str]  # ISO8601 for ICS generation
    # Error propagation
    error: Optional[str]


def build_agent3_graph(session: AsyncSession):
    """Build and compile an Agent 3 LangGraph. Session injected via closure.

    Args:
        session: An open AsyncSession. The caller is responsible for its lifecycle.

    Returns:
        A compiled LangGraph graph ready for ``ainvoke``.
    """
    max_rounds = AGENT3_MAX_ROUNDS
    poll_interval_seconds = AGENT3_POLL_INTERVAL_S

    async def fetch_context(state: Agent3State) -> dict:
        match: Match | None = await session.get(Match, state["match_id"])
        if not match:
            return {"error": f"Match {state['match_id']} not found"}

        apt: Apartment | None = await session.get(Apartment, match.apartment_id)
        user: User | None = await session.get(User, match.user_id)
        nego: NegotiationPreferences | None = (
            await session.execute(
                select(NegotiationPreferences)
                .where(NegotiationPreferences.user_id == match.user_id)
                .limit(1)
            )
        ).scalar_one_or_none()

        if not apt or not user:
            return {"error": "Apartment or user not found"}
        if not nego or not nego.enable_automation:
            return {"error": "Automation disabled for this user"}
        if not apt.host_email:
            return {"error": "Apartment has no host email"}

        return {
            "max_rounds": max_rounds,
            "email_subject": f"Apartment Inquiry: {apt.name}",
            "match": {
                "id": match.id,
                "user_id": match.user_id,
                "apartment_id": match.apartment_id,
                "match_score": match.match_score,
                "match_reasoning": match.match_reasoning,
            },
            "apartment": {
                "id": apt.id,
                "name": apt.name,
                "price": apt.price,
                "host_email": apt.host_email,
                "host_phone": apt.host_phone,
                "image_labels": apt.image_labels or [],
                "bedroom_type": apt.bedroom_type,
            },
            "user": {
                "id": user.id,
                "name": user.name,
                "phone": user.phone,
            },
            "negotiation_prefs": {
                "style": nego.negotiation_style or "professional",
                "goals": nego.goals or [],
                "negotiable_items": nego.negotiable_items or [],
                "max_rent": nego.max_rent,
            },
        }

    async def draft_email(state: Agent3State) -> dict:
        if state.get("error"):
            return {}

        client = get_claude_client()
        nego = state["negotiation_prefs"]
        apt = state["apartment"]
        user = state["user"]

        is_counter = state["round_number"] > 0 and state.get("host_reply")

        if is_counter:
            history_text = "\n".join(
                f"{'Agent' if h['role'] == 'agent' else 'Host'}: {h['text']}"
                for h in state["conversation_history"]
            )
            prompt = (
                f"You are drafting a {nego['style']} counter-offer email for a NYC apartment negotiation.\n\n"
                f"Renter: {user['name']}\n"
                f"Apartment: {apt['name']} at ${apt['price']}/mo\n"
                f"Negotiation goals: {', '.join(nego['goals'])}\n"
                f"Maximum acceptable rent: ${nego['max_rent']}\n"
                f"Negotiable items: {', '.join(nego['negotiable_items'])}\n\n"
                f"Conversation so far:\n{history_text}\n\n"
                "Write a brief, professional counter-offer email body. "
                "Be specific about what terms you're proposing. "
                "Return ONLY the email body text, no subject line."
            )
        else:
            # Opening email: propose 3 weekday morning slots next week
            today = date.today()
            slots: list[str] = []
            d = today + timedelta(days=1)
            while len(slots) < 3:
                if d.weekday() < 5:  # Monday=0 ... Friday=4
                    slots.append(d.strftime("%A, %B %d at 10:00 AM"))
                d += timedelta(days=1)

            prompt = (
                f"Draft a {nego['style']} apartment inquiry email for a NYC rental.\n\n"
                f"From: {user['name']}\n"
                f"Apartment: {apt['name']}, ${apt['price']}/mo, {apt['bedroom_type']}\n"
                f"Style features: {', '.join(apt['image_labels'])}\n"
                f"Goals: {', '.join(nego['goals'])}\n"
                f"Open to negotiating: {', '.join(nego['negotiable_items'])}\n"
                f"Proposed visit times: {'; '.join(slots)}\n\n"
                "The email must: (1) introduce the renter, (2) express genuine interest "
                "referencing the apartment's style, (3) propose the visit times, "
                "(4) subtly mention openness to discussing terms.\n"
                "Return ONLY the email body text, no subject line, no markdown."
            )

        try:
            response = await client.messages.create(
                model=MODEL,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            return {"email_draft": response.content[0].text.strip()}
        except Exception as exc:
            return {"error": str(exc)}

    async def send_email_node(state: Agent3State) -> dict:
        if state.get("error") or not state.get("email_draft"):
            return {}

        apt = state["apartment"]
        user_id = state["match"]["user_id"]
        match_id = state["match_id"]

        try:
            send_email(
                to=apt["host_email"],
                subject=state["email_subject"],
                body=state["email_draft"],
            )
        except Exception as exc:
            return {"error": f"SMTP error: {exc}"}

        # Record the outbound message in the messages table
        msg = Message(
            id=str(uuid.uuid4()),
            match_id=match_id,
            type="agent",
            timestamp=datetime.utcnow(),
            text=state["email_draft"],
        )
        session.add(msg)

        # Write an Agent3Log entry
        is_counter = state["round_number"] > 0
        ai_reasoning = (
            f"Counter-offer drafted for round {state['round_number']} in response to host's previous message."
            if is_counter
            else f"Opening inquiry drafted for {apt['name']} at ${apt['price']}/mo."
        )
        log = Agent3Log(
            id=str(uuid.uuid4()),
            user_id=user_id,
            apartment_id=apt["id"],
            message_id=msg.id,
            timestamp=datetime.utcnow(),
            result=json.dumps({
                "status": "sent",
                "round": state["round_number"],
                "contact_channel": "email",
                "contact_address": apt["host_email"],
                "ai_reasoning": ai_reasoning,
                "message": state["email_draft"],
            }),
        )
        session.add(log)
        await session.commit()

        new_history = list(state.get("conversation_history", []))
        new_history.append({"role": "agent", "text": state["email_draft"]})
        return {"conversation_history": new_history}

    async def poll_for_reply(state: Agent3State) -> dict:
        if state.get("error"):
            return {}

        # How many agent messages have been sent so far
        history_agent_count = sum(
            1 for h in state.get("conversation_history", []) if h["role"] == "agent"
        )
        history_host_count = sum(
            1 for h in state.get("conversation_history", []) if h["role"] == "host"
        )

        # Poll up to 3 times before declaring no_reply for this round
        for _ in range(3):
            await asyncio.sleep(poll_interval_seconds)

            # Expire the session cache so we see rows committed by other
            # sessions (e.g. inject-email-reply) since the last query.
            session.expire_all()

            result = await session.execute(
                select(Message)
                .where(
                    Message.match_id == state["match_id"],
                    Message.type == "host",
                )
                .order_by(Message.timestamp.desc())
                .limit(1)
            )
            msg: Message | None = result.scalar_one_or_none()

            # A new host reply exists when there are more agent turns than host turns
            if msg and history_agent_count > history_host_count:
                return {"host_reply": msg.text}

        return {"host_reply": None}

    async def analyze_reply(state: Agent3State) -> dict:
        if state.get("error"):
            return {"reply_analysis": "rejected"}
        if not state.get("host_reply"):
            return {"reply_analysis": "no_reply"}

        client = get_claude_client()
        history_text = "\n".join(
            f"{'Agent' if h['role'] == 'agent' else 'Host'}: {h['text']}"
            for h in state.get("conversation_history", [])
        )

        prompt = (
            "Analyze this apartment negotiation reply from the host.\n\n"
            f"Context — negotiation so far:\n{history_text}\n\n"
            f"Host's latest reply:\n{state['host_reply']}\n\n"
            "Return ONLY valid JSON with:\n"
            '- "analysis": one of "accepted" | "counter_offer" | "rejected"\n'
            '- "agreed_datetime": ISO8601 datetime if accepted and a time was agreed (else null)\n'
            '- "summary": one sentence summary of the host\'s position\n'
            "No markdown."
        )
        try:
            response = await client.messages.create(
                model=MODEL,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            # Claude sometimes wraps JSON in markdown code fences; strip them.
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw.strip())
            analysis = parsed.get("analysis", "rejected")
            summary = parsed.get("summary", "")
            new_history = list(state.get("conversation_history", []))
            new_history.append({"role": "host", "text": state["host_reply"]})

            # Log the received reply and AI analysis
            apt = state["apartment"]
            log = Agent3Log(
                id=str(uuid.uuid4()),
                user_id=state["match"]["user_id"],
                apartment_id=apt["id"],
                timestamp=datetime.utcnow(),
                result=json.dumps({
                    "status": analysis,
                    "round": state["round_number"],
                    "contact_channel": "email",
                    "contact_address": apt["host_email"],
                    "ai_reasoning": summary,
                    "message": state["host_reply"],
                }),
            )
            session.add(log)
            await session.commit()

            return {
                "reply_analysis": analysis,
                "agreed_datetime": parsed.get("agreed_datetime"),
                "conversation_history": new_history,
                "round_number": state["round_number"] + 1,
            }
        except Exception as exc:
            return {"reply_analysis": "rejected", "error": str(exc)}

    def route_after_analysis(state: Agent3State) -> str:
        analysis = state.get("reply_analysis", "rejected")
        if analysis == "accepted":
            return "generate_ics_node"
        if analysis == "counter_offer" and state["round_number"] < state["max_rounds"]:
            return "draft_email"
        return "finalize_no_deal"

    async def generate_ics_node(state: Agent3State) -> dict:
        """Generate an ICS file and send a calendar invite to the host."""
        apt = state["apartment"]
        user = state["user"]

        try:
            if state.get("agreed_datetime"):
                visit_dt = datetime.fromisoformat(state["agreed_datetime"])
            else:
                # Default: 3 days from now at 14:00 UTC
                visit_dt = (datetime.utcnow() + timedelta(days=3)).replace(
                    hour=14, minute=0, second=0, microsecond=0
                )
        except (ValueError, TypeError):
            visit_dt = (datetime.utcnow() + timedelta(days=3)).replace(
                hour=14, minute=0, second=0, microsecond=0
            )

        ics_bytes = generate_ics(
            summary=f"Apartment Visit — {apt['name']}",
            start_dt=visit_dt,
            duration_minutes=60,
            organizer_email=apt["host_email"],
            attendee_email="",
            description=f"Apartment visit for {apt['name']} at ${apt['price']}/mo.",
            location=apt["name"],
        )

        ics_subject = f"Visit Confirmed — {apt['name']}"
        ics_body = (
            f"Dear Host,\n\nThis email confirms our apartment visit on "
            f"{visit_dt.strftime('%A, %B %d at %I:%M %p')}.\n\n"
            f"Renter: {user['name']}\n\n"
            "Please find the calendar invite attached.\n\nBest regards,\nRento"
        )

        try:
            send_email(
                to=apt["host_email"],
                subject=ics_subject,
                body=ics_body,
                attachments=[("visit.ics", ics_bytes)],
            )
        except Exception as exc:
            return {"error": f"Failed to send ICS: {exc}"}

        # Record the ICS confirmation in the messages table so the DB stays
        # in sync with what Mailpit captured via SMTP.
        ics_msg = Message(
            id=str(uuid.uuid4()),
            match_id=state["match_id"],
            type="agent",
            timestamp=datetime.utcnow(),
            text=ics_body,
        )
        session.add(ics_msg)
        await session.commit()

        return {}

    async def finalize_success(state: Agent3State) -> dict:
        """Mark the match completed and notify the user after a successful negotiation."""
        match: Match | None = await session.get(Match, state["match_id"])
        if match:
            match.status = "completed"
            session.add(match)

        notif = Notification(
            id=str(uuid.uuid4()),
            user_id=state["match"]["user_id"],
            timestamp=datetime.utcnow(),
            content=(
                f"Visit confirmed for {state['apartment']['name']}! "
                "Calendar invite sent to the host."
            ),
            type="negotiation",
            read=False,
        )
        session.add(notif)
        await session.commit()
        return {}

    async def finalize_no_deal(state: Agent3State) -> dict:
        """Reset match status and notify the user when negotiation ends without agreement."""
        match: Match | None = await session.get(Match, state["match_id"])
        if match:
            match.status = "not_started"
            session.add(match)

        reason_map = {
            "rejected": "The host declined your inquiry.",
            "no_reply": "No response received from the host after multiple attempts.",
            "counter_offer": "Negotiation rounds exhausted without agreement.",
        }
        reason = reason_map.get(
            state.get("reply_analysis", "no_reply"),
            "Negotiation ended without agreement.",
        )

        notif = Notification(
            id=str(uuid.uuid4()),
            user_id=state["match"]["user_id"],
            timestamp=datetime.utcnow(),
            content=f"Outreach for {state['apartment']['name']}: {reason}",
            type="negotiation",
            read=False,
        )
        session.add(notif)
        await session.commit()
        return {}

    g: StateGraph = StateGraph(Agent3State)
    g.add_node("fetch_context", fetch_context)
    g.add_node("draft_email", draft_email)
    g.add_node("send_email_node", send_email_node)
    g.add_node("poll_for_reply", poll_for_reply)
    g.add_node("analyze_reply", analyze_reply)
    g.add_node("generate_ics_node", generate_ics_node)
    g.add_node("finalize_success", finalize_success)
    g.add_node("finalize_no_deal", finalize_no_deal)

    g.add_edge(START, "fetch_context")
    g.add_edge("fetch_context", "draft_email")
    g.add_edge("draft_email", "send_email_node")
    g.add_edge("send_email_node", "poll_for_reply")
    g.add_edge("poll_for_reply", "analyze_reply")
    g.add_conditional_edges(
        "analyze_reply",
        route_after_analysis,
        {
            "generate_ics_node": "generate_ics_node",
            "draft_email": "draft_email",
            "finalize_no_deal": "finalize_no_deal",
        },
    )
    g.add_edge("generate_ics_node", "finalize_success")
    g.add_edge("finalize_success", END)
    g.add_edge("finalize_no_deal", END)
    return g.compile()


async def run_agent3(match_id: str) -> None:
    """Entry point for background task. Creates its own DB session.

    Args:
        match_id: Primary key of the Match to negotiate on.
    """
    from app.database import async_session_factory

    async with async_session_factory() as session:
        graph = build_agent3_graph(session)
        initial_state: Agent3State = {
            "match_id": match_id,
            "match": {},
            "apartment": {},
            "user": {},
            "negotiation_prefs": {},
            "round_number": 0,
            "max_rounds": AGENT3_MAX_ROUNDS,
            "conversation_history": [],
            "email_subject": "",
            "email_draft": None,
            "host_reply": None,
            "reply_analysis": None,
            "agreed_datetime": None,
            "error": None,
        }
        await graph.ainvoke(initial_state)
