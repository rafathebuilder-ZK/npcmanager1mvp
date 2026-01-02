# NPC Manager 1 MVP

An execution management layer for autonomous agents that enforces enterprise controls (identity, permissions, approvals, guardrails, audit) between agents and business systems.

## Architecture

```
Agent (LangChain) → NPC Manager (FastAPI) → Ticketing API (FastAPI) → SQLite DB
                        ↓
                   Approval (CLI)
                   Audit Trail
                   Guardrails
```

## Prerequisites

### Required

1. **Python 3.10+**
   - Check: `python3 --version`
   - Install: https://www.python.org/downloads/

2. **OpenAI API Key**
   - Sign up at https://platform.openai.com (free account works)
   - Go to API Keys section
   - Create new API key
   - You'll add this to `.env` file (see Setup section)

### Optional

- Git (for version control)
- Code editor

## Setup

### 1. Clone or Navigate to Project

```bash
cd "NPC Manager 1"
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the project root (copy from `env.example`):

```bash
cp env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-api-key-here
NPC_MANAGER_URL=http://localhost:8001
TICKETING_API_URL=http://localhost:8000
TICKETING_DB_PATH=database/ticketing.db
NPC_MANAGER_DB_PATH=database/npc_manager.db
```

### 5. Initialize Databases

```bash
python scripts/setup_db.py
```

This will:
- Create both SQLite databases (`database/ticketing.db` and `database/npc_manager.db`)
- Create all tables
- Seed data:
  - 12 tickets (mix of resolvable/ambiguous)
  - 2 customers (one with `do_not_contact=True`)
  - Agent: `agent-support-001`
  - 3 permission profiles
  - Manager controls

## Running the Services

### Start Ticketing API

```bash
python -m uvicorn ticketing_api.main:app --port 8000
```

Or:

```bash
cd ticketing_api
python main.py
```

The API will be available at http://localhost:8000

### Start NPC Manager

In a separate terminal:

```bash
python -m uvicorn npc_manager.main:app --port 8001
```

Or:

```bash
cd npc_manager
python main.py
```

The manager will be available at http://localhost:8001

### Run the Agent

With both services running, in another terminal:

```bash
python -m agent.agent
```

Or:

```bash
cd agent
python agent.py
```

## Running the Demo

The demo script orchestrates all services and walks through the runbook narrative:

```bash
python scripts/demo.py
```

The demo includes 5 acts:
1. **Act 1**: No Manager - Baseline failure mode
2. **Act 2**: With Manager - Approval flow
3. **Act 3**: Guardrails - Structural limits (bulk limits, do-not-contact)
4. **Act 4**: Kill Switch - Incident containment
5. **Act 5**: Audit Trail - Enterprise questions

## Project Structure

```
NPC Manager 1/
├── Product Planning/          # Planning documents
├── ticketing_api/             # Business API
│   ├── main.py               # FastAPI endpoints
│   ├── models.py             # SQLAlchemy models
│   └── database.py           # DB setup
├── npc_manager/              # Manager service
│   ├── main.py               # Proxy endpoints
│   ├── models.py             # Audit/control models
│   ├── controls.py           # Permission/risk/guardrail logic
│   ├── approval.py           # CLI approval handler
│   └── database.py           # DB setup
├── agent/                     # LangChain agent
│   ├── agent.py              # Agent setup
│   └── tools.py              # Tool definitions
├── scripts/
│   ├── setup_db.py           # Database initialization
│   └── demo.py               # Demo script
├── database/                  # SQLite databases
│   ├── ticketing.db
│   └── npc_manager.db
├── requirements.txt
├── env.example
└── README.md
```

## Key Components

### Ticketing API

Business API exposing:
- `GET /tickets` - List tickets (with filters)
- `GET /tickets/{id}` - Get ticket details
- `PATCH /tickets/{id}` - Update ticket
- `GET /customers/{id}` - Get customer details
- `POST /customers/{id}/email` - Send email to customer

### NPC Manager

Proxy service that enforces:
- **Agent Identity**: First-class machine identity
- **Permissions**: Environment-aware profiles
- **Approvals**: Required for high-risk actions (CLI-based in MVP)
- **Guardrails**: Structural limits (max updates, do-not-contact)
- **Audit Trail**: Complete action history

Endpoints:
- `POST /action` - Main proxy endpoint (agent tools call this)
- `GET /health` - Health check
- `GET /audit/timeline` - Audit query

### Agent

LangChain agent with tools:
- `list_tickets` - List tickets through NPC Manager
- `update_ticket` - Update tickets through NPC Manager
- `send_customer_email` - Send emails through NPC Manager

**Critical**: Agent tools call NPC Manager, NOT Ticketing API directly.

## MVP Limitations

This MVP demonstrates the core concepts with intentional simplifications:

1. **Synchronous Approval**: Uses blocking CLI prompts (production would use async workflow)
2. **Simple Permission Rules**: Hard-coded tool → endpoint mapping (production would be configurable)
3. **CLI Approval Channel**: Blocking terminal input (production would use Slack, ServiceNow, etc.)
4. **No Real Authentication**: Uses `agent_id` header only (production would use API keys, mTLS, OAuth)
5. **Two Separate Databases**: SQLite files (production could use single DB with schemas)
6. **Local Only**: All services run locally (production would be distributed)

## Success Criteria

The MVP demonstrates:
- ✅ Agent executes write operations autonomously
- ✅ Every action is attributed to agent_id with ownership
- ✅ High-risk actions require approval before execution
- ✅ Guardrails block violations (bulk limits, do-not-contact)
- ✅ Kill switch stops all agent actions instantly
- ✅ Audit trail answers: who, what, why, when, who approved
- ✅ Agent code unchanged when controls are added

## Troubleshooting

### Database Errors

If you get database errors, try re-running the setup:

```bash
rm database/*.db
python scripts/setup_db.py
```

### Service Won't Start

- Check if ports 8000 and 8001 are already in use
- Make sure virtual environment is activated
- Verify all dependencies are installed: `pip install -r requirements.txt`

### OpenAI API Errors

- Verify your API key is set in `.env` file
- Check that you have credits in your OpenAI account
- Ensure `OPENAI_API_KEY` environment variable is loaded (use `python-dotenv`)

### Import Errors

Make sure you're running commands from the project root, or use:

```bash
python -m ticketing_api.main
python -m npc_manager.main
python -m agent.agent
```

## License

AGPL-3.0

## Repository

https://github.com/rafathebuilder-ZK/npcmanager1mvp

