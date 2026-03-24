# 🏠 Rento

**Agent-powered apartment hunting and negotiation for NYC renters.**

Rento scrapes listings from Craigslist and StreetEasy, analyzes them with Claude AI (vision + text), matches them to your preferences, and autonomously negotiates with landlords via email — all from a single dashboard.

Built for **[EmpireHacks 2026](https://cornell-tech-hackathon.vercel.app/)**.

---

## ⚡ Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- An [Anthropic API key](https://console.anthropic.com/)

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/cornell-projects-alexgravx/rento.git
cd rento

# 2. Configure environment
cp .env.example .env
# Edit .env
# -> set ANTHROPIC_API_KEY
# -> set POSTGRES_PASSWORD
# -> set SMTP_USERNAME
# -> set SMTP_PASSWORD
# -> set JWT_SECRET

# 3. Start everything
docker compose up -d

# 4. Open the app (locally)
open http://localhost:5173
```

| Service   | URL                     |
|-----------|-------------------------|
| Frontend  | http://localhost:5173    |
| API       | http://localhost:8000    |
| API Docs  | http://localhost:8000/docs |
| Mailpit   | http://localhost:8025    |

---

## 🏗️ Architecture

```mermaid
graph TB
    subgraph Frontend
        UI["React + Vite + Tailwind"]
        Store["Zustand Store"]
        UI --- Store
    end

    subgraph Backend
        API["FastAPI REST API"]
        subgraph AI_Agents["AI Agents"]
            A1["Agent 1 — Image Analysis"]
            A2["Agent 2 — Semantic Matching"]
            A3["Agent 3 — Autonomous Negotiation"]
        end
        Services["Matching & Scoring Services"]
    end

    subgraph Infrastructure
        DB[("PostgreSQL")]
        SMTP["Mailpit SMTP Server"]
        Claude["Claude API — Anthropic"]
    end

    subgraph Data_Sources["Data Sources"]
        CL["Craigslist Parser"]
        SE["StreetEasy Parser"]
    end

    UI -- "REST /api/v1" --> API
    API --> Services
    API --> AI_Agents
    A1 -- "Vision API" --> Claude
    A2 -- "Text API" --> Claude
    A3 -- "Text API" --> Claude
    A3 -- "Sends emails" --> SMTP
    Services --> DB
    AI_Agents --> DB
    API --> DB
    CL --> DB
    SE --> DB
```

### Agent Pipeline

| Agent | Role | How it works |
|-------|------|--------------|
| **Agent 1** — Image Analysis | Analyzes apartment photos for style/vibe labels | Sends images to Claude Vision → stores labels like `"bright"`, `"minimalist"`, `"hardwood-floors"` on each apartment |
| **Agent 2** — Semantic Matching | Ranks apartments against user preferences | Cross-references image labels, neighborhood data, budget, and commute with user profile via Claude → outputs 0–10 scores |
| **Agent 3** — Autonomous Negotiation | Handles landlord outreach end-to-end | Drafts inquiry emails → sends via SMTP → polls for host replies → analyzes responses → counter-offers or confirms → generates ICS calendar invites |

All three agents are implemented as **LangGraph** state machines.

### Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Backend | Python 3.12, FastAPI, SQLAlchemy |
| AI | Claude 3.5 Sonnet, LangGraph |
| Database | PostgreSQL 16 |
| Email | Mailpit (dev), SMTP |
| Infra | Docker Compose |

### Project Structure

```
rento/
├── frontend/               # React SPA
│   └── src/
│       ├── pages/           # Onboarding, Dashboard (Match, AgentLog)
│       ├── store/           # Zustand global state
│       ├── lib/             # API client, utilities
│       └── components/      # Shared UI components
├── backend/
│   └── app/
│       ├── agents/          # LangGraph AI agents (1, 2, 3)
│       ├── routers/         # FastAPI route handlers
│       ├── models/          # SQLAlchemy ORM models
│       ├── services/        # Matching, scoring, commute
│       └── schemas/         # Pydantic validation schemas
│   └── parsers/             # Craigslist & StreetEasy scrapers
└── docker-compose.yml
```

---

## 👥 Contributors

| Contributor | GitHub |
|-------------|--------|
| Ruolan Chen | [@OrchidRLan](https://github.com/OrchidRLan) |
| Kerui Bai | [@KrisssWW](https://github.com/KrisssWW) |
| Max Lytovka | [@Reymer249](https://github.com/Reymer249) |
| Alexandre Gravereaux | [@alexgravx](https://github.com/alexgravx) |

---

## 📄 License

This project is licensed under the [MIT License](./LICENSE).
