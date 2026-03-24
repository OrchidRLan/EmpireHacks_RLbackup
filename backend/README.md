# Rento

**EmpireHacks 2026** — NYC apartment rental search automation backend.

Rento replaces the manual grind of NYC apartment hunting with a three-agent pipeline: it analyzes listing photos with Claude Vision, semantically ranks apartments against your preferences, and autonomously negotiates with hosts over email — including counter-offers and calendar invite generation.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Tech Stack](#tech-stack)
4. [Quick Start](#quick-start)
5. [Key Workflows](#key-workflows)
6. [API Reference](#api-reference)
7. [Agent Details](#agent-details)
8. [Development](#development)

---

## Overview

Rento automates three distinct phases of the NYC apartment search:

**Image Analysis.** Agent 1 runs on a 2-hour schedule (and on demand) to send listing photos to Claude Vision. It extracts up to 10 style and vibe labels per apartment (e.g. `bright`, `minimalist`, `exposed-brick`) and stores them directly on the apartment record. These labels become the vocabulary that links what a renter wants to what a listing offers.

**Semantic Matching.** Agent 2 takes a user's filtered match candidates and sends them in a single batched Claude call alongside the user's subjective preferences. Claude scores and ranks each apartment on a 0-10 scale with a one-sentence rationale. Scores are normalized to 0-1 and written back to the match record. Separately, the matching service computes a weighted score from three signals — label overlap (Jaccard similarity), price position within budget, and commute estimate — allowing scores to update instantly when a user swipes.

**Autonomous Negotiation.** Agent 3 runs a full negotiation loop for each relevant match. It drafts an inquiry email (proposing three weekday visit slots), sends it via SMTP, polls the messages table for a host reply, and asks Claude to classify the reply as `accepted`, `counter_offer`, or `rejected`. Counter-offers trigger another loop iteration, up to a configurable maximum. On acceptance, the agent generates an ICS calendar invite and emails it to the host, then marks the match completed and notifies the user. On rejection or timeout, it resets the match and notifies the user.

---

## Architecture

```
Rento Backend
├── FastAPI Application (app/main.py)
│   ├── APScheduler — runs Agent 1 batch every 2 hours at startup
│   └── CORS middleware (all origins, for hackathon use)
│
├── Routers
│   ├── users              — user CRUD
│   ├── apartments         — apartment CRUD with query filters
│   ├── neighborhoods      — neighborhood/area CRUD
│   ├── matches            — match CRUD, filter runner, swipe, relevant matches
│   ├── preferences        — objective, subjective, negotiation, notification prefs
│   ├── messages           — message thread CRUD
│   ├── notifications      — notification CRUD + user feed + mark-read
│   ├── agent_logs         — read/write logs for all three agents
│   └── agents             — trigger endpoints + dev simulation endpoint
│
├── Services
│   ├── matching.py        — objective filter, swipe logic, Jaccard scoring, commute scoring
│   └── commute.py         — Haversine distance + mode-specific min/km multipliers
│
└── Agents (LangGraph graphs, each compiled per request with injected DB session)
    ├── Agent 1: Image Analysis
    │   fetch_apartment -> call_claude_vision -> persist_results
    │   Scheduled: every 2 hours via APScheduler
    │   Manual:    POST /agents/apartments/{id}/analyze-images
    │
    ├── Agent 2: Semantic Ranking
    │   fetch_user_context -> fetch_matches -> call_claude_batch -> persist_rankings
    │   Trigger:   POST /agents/users/{id}/rank-matches
    │
    └── Agent 3: Autonomous Negotiation
        fetch_context -> draft_email -> send_email_node -> poll_for_reply -> analyze_reply
                                                                                  |
              +--- [counter_offer + rounds remaining] <---------------------------+
              |                                                                   |
              +--- [accepted] --> generate_ics_node -> finalize_success -> END   |
              |                                                                   |
              +--- [rejected | no_reply | rounds exhausted] --> finalize_no_deal -> END

PostgreSQL 16 (Docker, port 5432)
Mailhog — local SMTP server (port 1025) + web UI (port 8025)
```

---

## Tech Stack

| Component | Library / Version |
|---|---|
| Web framework | FastAPI >= 0.111 |
| ORM | SQLAlchemy >= 2.0 (async, with asyncpg driver) |
| Database | PostgreSQL 16 (Docker) |
| Agent orchestration | LangGraph >= 0.1 |
| LLM | Claude Sonnet (Anthropic >= 0.26) |
| Scheduler | APScheduler >= 3.10 |
| Calendar invites | icalendar >= 5.0 |
| Local email | Mailhog (Docker) |
| Data validation | Pydantic >= 2.7 |
| Seed data | Faker >= 25.0 |

---

## Quick Start

**Prerequisites:** Docker, Docker Compose, Python 3.11+

```bash
# Clone the repository and enter the project directory
git clone <repo-url>
cd rento/src/first-draft

# Copy the environment template and set your API key
cp .env.example .env
# Open .env and set ANTHROPIC_API_KEY to your real key

# Start the database and mail server
docker-compose up -d

# Install Python dependencies
pip install -r requirements.txt

# Seed the database with mock users, apartments, and neighborhoods
python scripts/seed.py

# Start the API server (if running outside Docker)
uvicorn app.main:app --reload
```

**Services once running:**

| Service | URL |
|---|---|
| REST API | http://localhost:8000 |
| Interactive API docs (Swagger) | http://localhost:8000/docs |
| Mailhog web UI (outbound emails) | http://localhost:8025 |
| PostgreSQL | localhost:5432 (user: rento, db: rento) |

> The `api` service in `docker-compose.yml` waits for PostgreSQL to pass its healthcheck before starting, and Mailhog is configured automatically via environment variables. No additional SMTP setup is needed for local development.

---

## Key Workflows

### Workflow 1 — Find apartments

This workflow filters the full apartment inventory down to candidates that match a user's hard constraints, then ranks them semantically.

```
1. POST /users/{user_id}/run-filter
   Runs the objective filter against all apartments.
   Creates Match rows for every qualifying apartment (idempotent — safe to re-run).
   Returns: { "matches_created": N }

2. POST /agents/users/{user_id}/rank-matches     (202 Accepted, runs async)
   Agent 2 sends the top N matches to Claude for semantic scoring.
   Updates match_score (0.0-1.0) and match_reasoning on each Match.

3. GET /users/{user_id}/matches/relevant?min_score=0.8
   Returns all matches above the score threshold, sorted best-first.
```

[IMAGE: Screenshot of the Swagger UI showing the run-filter and rank-matches request/response cycle]

### Workflow 2 — Refine preferences through swiping

Each swipe teaches the system more about what the user wants by updating their style label profile and immediately rescoring all matches.

```
POST /users/{user_id}/swipe
Body: { "apartment_id": "...", "action": "like" | "dislike" | "love" }

- like:    adds the apartment's image_labels to the user's profile (union)
- dislike: removes overlapping labels from the user's profile (difference)
- love:    double-weights the labels (adds them twice for stronger signal)

All match scores recalculate immediately after each swipe.
Returns: { "matches_rescored": N }
```

### Workflow 3 — Start autonomous outreach

Once a user has relevant, scored matches, Agent 3 takes over and manages the entire host communication thread.

```
1. POST /agents/users/{user_id}/contact-relevant?min_score=0.8
   Enqueues Agent 3 for every match at or above the threshold.
   Returns: { "message": "...", "count": N }

   To target a single match instead:
   POST /agents/matches/{match_id}/contact

2. Agent 3 runs in the background:
   - Drafts and sends an opening inquiry email with 3 proposed visit times
   - Polls for a host reply (every AGENT3_REPLY_POLL_INTERVAL_SECONDS seconds)
   - Claude classifies the reply and decides the next action
   - Negotiates up to AGENT3_MAX_NEGOTIATION_ROUNDS rounds
   - On acceptance: sends an ICS calendar invite, marks match "completed"
   - On rejection or timeout: resets match to "not_started"
   - User receives a Notification either way

3. GET /users/{user_id}/notifications
   Check negotiation outcomes and other system events.
```

---

## API Reference

### Health

| Method | Path | Description | Status |
|---|---|---|---|
| GET | /health | Liveness check | 200 |

### Users

| Method | Path | Description | Status |
|---|---|---|---|
| GET | /users/ | List all users | 200 |
| GET | /users/{user_id} | Get a user by ID | 200 |
| POST | /users/ | Create a user | 201 |
| PATCH | /users/{user_id} | Update a user | 200 |
| DELETE | /users/{user_id} | Delete a user | 204 |

### Apartments

Supports query parameters: `bedroom_type`, `min_price`, `max_price`, `neighbor_id`, `pets`.

| Method | Path | Description | Status |
|---|---|---|---|
| GET | /apartments/ | List apartments (filterable) | 200 |
| GET | /apartments/{apartment_id} | Get an apartment by ID | 200 |
| POST | /apartments/ | Create an apartment | 201 |
| PATCH | /apartments/{apartment_id} | Update an apartment | 200 |
| DELETE | /apartments/{apartment_id} | Delete an apartment | 204 |

### Neighborhoods

| Method | Path | Description | Status |
|---|---|---|---|
| GET | /neighborhoods/ | List all neighborhoods | 200 |
| GET | /neighborhoods/{neighborhood_id} | Get a neighborhood by ID | 200 |
| POST | /neighborhoods/ | Create a neighborhood | 201 |
| PATCH | /neighborhoods/{neighborhood_id} | Update a neighborhood | 200 |
| DELETE | /neighborhoods/{neighborhood_id} | Delete a neighborhood | 204 |

### Matches

| Method | Path | Description | Status |
|---|---|---|---|
| GET | /matches | List all matches | 200 |
| GET | /matches/{match_id} | Get a match by ID | 200 |
| POST | /matches | Create a match manually | 201 |
| PATCH | /matches/{match_id} | Update a match | 200 |
| DELETE | /matches/{match_id} | Delete a match | 204 |
| GET | /users/{user_id}/matches | Get all matches for a user | 200 |
| GET | /users/{user_id}/matches/relevant | Get matches above min_score (default 0.8), sorted by score | 200 |
| POST | /users/{user_id}/run-filter | Run objective filter — creates Match rows for qualifying apartments | 200 |
| POST | /users/{user_id}/swipe | Swipe on an apartment to update label profile and rescore all matches | 200 |

### Preferences

All preference endpoints are scoped under `/users/{user_id}/`.

| Method | Path | Description | Status |
|---|---|---|---|
| GET | /users/{user_id}/objective-preferences | List objective preferences | 200 |
| GET | /users/{user_id}/objective-preferences/{pref_id} | Get by ID | 200 |
| POST | /users/{user_id}/objective-preferences | Create (budget, bedroom type, areas, commute, amenities) | 201 |
| PATCH | /users/{user_id}/objective-preferences/{pref_id} | Update | 200 |
| DELETE | /users/{user_id}/objective-preferences/{pref_id} | Delete | 204 |
| GET | /users/{user_id}/subjective-preferences | List subjective preferences | 200 |
| GET | /users/{user_id}/subjective-preferences/{pref_id} | Get by ID | 200 |
| POST | /users/{user_id}/subjective-preferences | Create (style labels, neighborhood labels, priority focus) | 201 |
| PATCH | /users/{user_id}/subjective-preferences/{pref_id} | Update | 200 |
| DELETE | /users/{user_id}/subjective-preferences/{pref_id} | Delete | 204 |
| GET | /users/{user_id}/negotiation-preferences | List negotiation preferences | 200 |
| GET | /users/{user_id}/negotiation-preferences/{pref_id} | Get by ID | 200 |
| POST | /users/{user_id}/negotiation-preferences | Create (enable_automation, goals, max_rent, style) | 201 |
| PATCH | /users/{user_id}/negotiation-preferences/{pref_id} | Update | 200 |
| DELETE | /users/{user_id}/negotiation-preferences/{pref_id} | Delete | 204 |
| GET | /users/{user_id}/notification-preferences | List notification preferences | 200 |
| GET | /users/{user_id}/notification-preferences/{pref_id} | Get by ID | 200 |
| POST | /users/{user_id}/notification-preferences | Create (enable_notifications, types, frequency) | 201 |
| PATCH | /users/{user_id}/notification-preferences/{pref_id} | Update | 200 |
| DELETE | /users/{user_id}/notification-preferences/{pref_id} | Delete | 204 |

### Messages

Messages represent the negotiation email thread. `type` is `agent` for outbound emails and `host` for inbound host replies.

| Method | Path | Description | Status |
|---|---|---|---|
| GET | /messages/ | List all messages | 200 |
| GET | /messages/{message_id} | Get a message by ID | 200 |
| POST | /messages/ | Create a message | 201 |
| PATCH | /messages/{message_id} | Update a message | 200 |
| DELETE | /messages/{message_id} | Delete a message | 204 |

### Notifications

| Method | Path | Description | Status |
|---|---|---|---|
| GET | /notifications | List all notifications | 200 |
| GET | /notifications/{notification_id} | Get a notification by ID | 200 |
| POST | /notifications | Create a notification | 201 |
| PATCH | /notifications/{notification_id} | Update a notification | 200 |
| DELETE | /notifications/{notification_id} | Delete a notification | 204 |
| GET | /users/{user_id}/notifications | Get all notifications for a user | 200 |
| PATCH | /notifications/{notification_id}/read | Mark a notification as read | 200 |

### Agents — Triggers and Status

All trigger endpoints return 202 Accepted immediately. The agent runs as a FastAPI background task.

| Method | Path | Description | Status |
|---|---|---|---|
| POST | /agents/apartments/{apartment_id}/analyze-images | Trigger Agent 1 for one apartment | 202 |
| POST | /agents/apartments/analyze-all | Trigger Agent 1 batch for all un-analyzed apartments | 202 |
| POST | /agents/users/{user_id}/rank-matches | Trigger Agent 2 semantic ranking for a user | 202 |
| POST | /agents/matches/{match_id}/contact | Trigger Agent 3 negotiation for one match | 202 |
| POST | /agents/users/{user_id}/contact-relevant | Trigger Agent 3 for all matches with score >= min_score (default 0.8) | 202 |
| GET | /agents/apartments/{apartment_id}/status | Agent 1 status — image labels and last log entry | 200 |
| GET | /agents/users/{user_id}/match-status | All matches for a user sorted by score descending | 200 |
| POST | /agents/dev/matches/{match_id}/simulate-host-reply | DEV ONLY: inject a host reply to test the Agent 3 negotiation loop | 201 |

### Agent Logs

Read/write access to raw agent execution logs. Useful for debugging.

| Method | Path | Description | Status |
|---|---|---|---|
| GET | /agent-logs/agent1 | List Agent 1 logs | 200 |
| GET | /agent-logs/agent1/{log_id} | Get Agent 1 log by ID | 200 |
| POST | /agent-logs/agent1 | Create Agent 1 log | 201 |
| PATCH | /agent-logs/agent1/{log_id} | Update Agent 1 log | 200 |
| DELETE | /agent-logs/agent1/{log_id} | Delete Agent 1 log | 204 |
| GET | /agent-logs/agent2 | List Agent 2 logs | 200 |
| GET | /agent-logs/agent2/{log_id} | Get Agent 2 log by ID | 200 |
| POST | /agent-logs/agent2 | Create Agent 2 log | 201 |
| PATCH | /agent-logs/agent2/{log_id} | Update Agent 2 log | 200 |
| DELETE | /agent-logs/agent2/{log_id} | Delete Agent 2 log | 204 |
| GET | /agent-logs/agent3 | List Agent 3 logs | 200 |
| GET | /agent-logs/agent3/{log_id} | Get Agent 3 log by ID | 200 |
| POST | /agent-logs/agent3 | Create Agent 3 log | 201 |
| PATCH | /agent-logs/agent3/{log_id} | Update Agent 3 log | 200 |
| DELETE | /agent-logs/agent3/{log_id} | Delete Agent 3 log | 204 |

---

## Agent Details

### Agent 1: Image Analysis

**What it does.** For each apartment, Agent 1 sends up to 5 listing photos to Claude Vision and requests a structured JSON response containing a list of style/vibe labels (e.g. `hardwood-floors`, `high-ceilings`, `natural-light`) and a one-paragraph description of the apartment's feel. The labels are stored in the `image_labels` array on the `Apartment` row and become the semantic vocabulary used by both the matching service and Agent 2.

**When it runs.**
- Automatically on a 2-hour schedule (APScheduler, registered at application startup in `lifespan`).
- Manually for all un-analyzed apartments: `POST /agents/apartments/analyze-all`
- Manually for a single apartment: `POST /agents/apartments/{apartment_id}/analyze-images`

The batch job targets only apartments whose `image_labels` field is null or empty, so it is safe to re-run without redundant API calls.

**What it writes.**
- `Apartment.image_labels` — list of up to 10 short label strings
- `Agent1Log` row — records which apartment was processed, how many images were analyzed, and whether the run succeeded or errored

**LangGraph nodes:** `fetch_apartment` -> `call_claude_vision` -> `persist_results`

---

### Agent 2: Semantic Match Ranking

**What it does.** Agent 2 takes a user's existing match candidates (created by the objective filter) and asks Claude to rank them semantically. It bundles the user's full preference profile and all match data — including apartment image labels, neighborhood name and description, price, bedroom type, and commute estimate — into a single batched prompt. Claude returns a scored and sorted list. Scores on Claude's 0-10 scale are normalized to 0.0-1.0 before being written to the database.

**Input.** The user's `SubjectivePreferences` (style label preferences, neighborhood preferences, priority focus) and `ObjectivePreferences` (budget range, bedroom type), plus the top N Match rows with their associated Apartment and NeighborInfo data. N defaults to 20 and can be overridden with the `top_n` query parameter on the trigger endpoint.

**Output.** Each Match row in the batch gets an updated `match_score` (float, 0.0-1.0) and `match_reasoning` (one-sentence string from Claude). An `Agent2Log` row records the run result.

**Trigger:** `POST /agents/users/{user_id}/rank-matches`

**Prerequisite:** the user must have at least one Match row. Run `POST /users/{user_id}/run-filter` first.

**LangGraph nodes:** `fetch_user_context` -> `fetch_matches` -> `call_claude_batch` -> `persist_rankings`

---

### Agent 3: Autonomous Negotiation

**What it does.** Agent 3 manages a complete email negotiation loop on behalf of the user, from first contact through visit confirmation or rejection.

**Preconditions checked before the loop begins:**
- `NegotiationPreferences.enable_automation` must be `true` for the user
- The apartment must have a `host_email`
- The match status must not already be `completed`

**The negotiation loop:**

```
START
  |
  v
fetch_context
  Load match, apartment, user, and negotiation preferences.
  Validate preconditions. Abort with error on missing data.
  |
  v
draft_email
  Round 0: Opening inquiry.
    Claude drafts a personalized email referencing the apartment's
    image_labels and the user's negotiation goals. Proposes 3 weekday
    visit slots (10 AM on the next 3 business days).
  Round N: Counter-offer.
    Claude drafts a response based on the full conversation history
    and the user's max_rent and negotiable_items.
  |
  v
send_email_node
  Sends the email via SMTP (Mailhog in dev).
  Records a Message(type="agent") row and an Agent3Log entry.
  |
  v
poll_for_reply
  Polls the messages table for a new Message(type="host") row.
  Waits AGENT3_REPLY_POLL_INTERVAL_SECONDS between each attempt.
  Tries up to 3 times before declaring no_reply for this round.
  |
  v
analyze_reply
  If no reply:      analysis = "no_reply"
  If reply present: Claude reads the full conversation history and the
                    host's latest reply, then returns one of:
                      "accepted"      — deal agreed (may include confirmed datetime)
                      "counter_offer" — host proposes different terms
                      "rejected"      — host has declined
  Increments round_number. Appends host message to conversation_history.
  |
  +-- "accepted" ──────────────────────────────────────────────────────+
  |                                                                     v
  |                                                          generate_ics_node
  |                                                            Generates a 1-hour ICS
  |                                                            calendar event at the
  |                                                            agreed datetime (or 3 days
  |                                                            from now at 14:00 UTC as
  |                                                            a fallback).
  |                                                            Sends the ICS as an email
  |                                                            attachment to the host.
  |                                                                     |
  |                                                                     v
  |                                                          finalize_success
  |                                                            match.status = "completed"
  |                                                            Creates Notification for user.
  |                                                                     |
  |                                                                     v
  |                                                                    END
  |
  +-- "counter_offer" + round_number < max_rounds ─────────────────────+
  |                                                                     v
  |                                                              draft_email (loop back)
  |
  +-- "rejected" | "no_reply" | rounds exhausted ───────────────────────+
                                                                         v
                                                              finalize_no_deal
                                                                match.status = "not_started"
                                                                Creates Notification for user
                                                                with reason string.
                                                                         |
                                                                         v
                                                                        END
```

**Configuration (via .env):**

| Variable | Default | Description |
|---|---|---|
| `AGENT3_MAX_NEGOTIATION_ROUNDS` | 5 | Maximum counter-offer rounds before giving up |
| `AGENT3_REPLY_POLL_INTERVAL_SECONDS` | 1800 | Seconds to wait between poll attempts (30 min) |

---

## Development

### Simulating host replies

Agent 3 polls the `messages` table for rows with `type="host"`. In development there is no real inbound email parsing — use the dev endpoint to inject a reply directly:

```bash
curl -X POST http://localhost:8000/agents/dev/matches/{match_id}/simulate-host-reply \
  -H "Content-Type: application/json" \
  -d '{"text": "Hi, thanks for reaching out! We can do $2,800/mo. Does Tuesday the 25th at 10 AM work?"}'
```

This inserts a `Message(type="host")` row that Agent 3 will pick up on its next poll. Use this to exercise all three reply paths: `accepted`, `counter_offer`, and `rejected`.

### Viewing outbound emails

All emails sent by Agent 3 (inquiries, counter-offers, and ICS calendar invites) are captured by Mailhog. Open the Mailhog web interface at http://localhost:8025 to inspect every email's body, subject, recipient, and attachments — no real email infrastructure required.

[IMAGE: Screenshot of the Mailhog web UI showing a captured inquiry email from Agent 3]

### Seeding the database

```bash
python scripts/seed.py
```

This drops and recreates all tables, then populates the database with mock neighborhoods, apartments (with image URLs), users, and all four preference types. Run it any time you want a clean slate.

### End-to-end test sequence

After seeding, this sequence exercises the full pipeline:

```bash
# 1. Get a seeded user ID
curl http://localhost:8000/users/ | python -m json.tool

# 2. Run the objective filter to create matches
curl -X POST http://localhost:8000/users/{user_id}/run-filter

# 3. Trigger Agent 1 to label all apartment images (async)
curl -X POST http://localhost:8000/agents/apartments/analyze-all

# 4. Trigger Agent 2 to semantically rank the matches (async)
curl -X POST "http://localhost:8000/agents/users/{user_id}/rank-matches"

# 5. Check top-scoring matches
curl "http://localhost:8000/users/{user_id}/matches/relevant?min_score=0.7"

# 6. Start outreach on all relevant matches (async)
curl -X POST "http://localhost:8000/agents/users/{user_id}/contact-relevant?min_score=0.7"

# 7. Simulate a host reply on one of the active match IDs
curl -X POST http://localhost:8000/agents/dev/matches/{match_id}/simulate-host-reply \
  -H "Content-Type: application/json" \
  -d '{"text": "Great! Happy to accept. See you Monday at 10 AM."}'

# 8. Check the user's notifications for the outcome
curl "http://localhost:8000/users/{user_id}/notifications"

# 9. Confirm the match is marked completed
curl http://localhost:8000/matches/{match_id}

# 10. Check Mailhog for the ICS calendar invite
open http://localhost:8025
```

### Environment variables

Copy `.env.example` to `.env` and fill in your values. The only required change from the example is `ANTHROPIC_API_KEY`.

| Variable | Description |
|---|---|
| `DATABASE_URL` | asyncpg connection string |
| `ANTHROPIC_API_KEY` | Required — used by all three agents |
| `SMTP_HOST` | SMTP server host (default: `mailhog`) |
| `SMTP_PORT` | SMTP port (default: `1025` for Mailhog) |
| `SMTP_FROM` | From address on outbound emails |
| `SMTP_USE_TLS` | Set to `true` for real SMTP providers |
| `AGENT3_MAX_NEGOTIATION_ROUNDS` | Max counter-offer loops (default: `5`) |
| `AGENT3_REPLY_POLL_INTERVAL_SECONDS` | Poll cadence in seconds (default: `1800`) |
| `AGENT2_TOP_N_MATCHES` | Matches per Agent 2 batch run (default: `20`) |

### Enum reference

| Field | Valid values |
|---|---|
| `bedroom_type` | `studio`, `1b`, `2b`, `3b`, `4plus` |
| `laundry[]` | `in_unit`, `on_site` |
| `parking[]` | `garage`, `street` |
| `commute_method` | `drive`, `transit`, `bike` |
| `priority_focus` | `features`, `location`, `price` |
| `negotiation_style` | `polite`, `professional`, `assertive`, `friendly` |
| `negotiable_items[]` | `rent_price`, `move_in_date`, `lease_length`, `deposit`, `parking_fee`, `pet_fee`, `utilities`, `furnishing`, `application_fee`, `promotions` |
| `goals[]` | `save_money`, `stay_flexible`, `live_better`, `fit_lifestyle`, `hassle_free` |
| `notification type` | `match`, `price_drop`, `negotiation` |
| `frequency` | `realtime`, `daily`, `weekly` |
| `match status` | `not_started`, `in_progress`, `completed` |
| `swipe action` | `like`, `dislike`, `love` |
| `message type` | `agent`, `host` |
