# NPC Manager 1 MVP - Final Design Document

**Version:** 1.0 (As-Built)  
**Date:** January 2025  
**Status:** Implemented and Functional

This document reflects the actual implemented design of NPC Manager 1 MVP, including all corrections, adjustments, and decisions made during implementation.

---

## Executive Summary

NPC Manager 1 MVP is an execution management layer for autonomous agents that enforces enterprise controls (identity, permissions, approvals, guardrails, audit) between agents and business systems. The system has been successfully implemented and tested.

**Key Achievement:** All core functionality is operational, demonstrating agent control, guardrails, kill switch, and audit capabilities.

---

## Architecture Overview

```
Agent (LangChain/LangGraph) → NPC Manager (FastAPI) → Ticketing API (FastAPI) → SQLite DB
                                    ↓
                              Approval (CLI)
                              Audit Trail
                              Guardrails
```

### Technology Stack (As-Implemented)

- **Language:** Python 3.14.0
- **Web Framework:** FastAPI 0.128.0
- **Database:** SQLite 3 (built-in, no external setup required)
- **Agent Framework:** LangChain 1.2.0 + LangGraph 1.0.5
- **LLM:** OpenAI API (via langchain-openai 1.1.6)
- **ORM:** SQLAlchemy 2.0.45
- **HTTP Client:** httpx 0.28.1
- **Environment:** python-dotenv 1.2.1
- **Validation:** Pydantic 2.12.5

**Note:** Updated from original plan to use LangChain 1.2.0 (LangGraph) instead of 0.1.4 due to Python 3.14 compatibility requirements.

---

## Project Structure (Actual Implementation)

```
NPC Manager 1/
├── Product Planning/              # Planning and design documents
│   ├── design_review.md
│   ├── design_review_summary.md
│   ├── setup_requirements.md
│   ├── git_setup_summary.md
│   └── final_design_document.md   # This document
├── ticketing_api/                 # Business API (the system agents interact with)
│   ├── __init__.py
│   ├── main.py                    # FastAPI app with ticket/customer CRUD
│   ├── models.py                  # SQLAlchemy models (Ticket, Customer)
│   └── database.py                # DB connection setup
├── npc_manager/                   # The manager service (proxy with controls)
│   ├── __init__.py
│   ├── main.py                    # FastAPI proxy endpoints
│   ├── models.py                  # SQLAlchemy models (Agent, ActionRequest, etc.)
│   ├── controls.py                # Permission checks, risk classification, guardrails
│   ├── approval.py                # CLI approval workflow
│   └── database.py                # DB connection setup
├── agent/                         # LangChain/LangGraph agent implementation
│   ├── __init__.py
│   ├── agent.py                   # Agent setup using LangGraph
│   └── tools.py                   # Tool definitions (call NPC Manager)
├── scripts/
│   ├── setup_db.py                # Database initialization and seeding
│   ├── demo.py                    # Full interactive demo script
│   ├── demo_auto.py               # Automated demo (non-interactive)
│   └── demo_simple.py             # Simplified automated demo
├── database/                      # SQLite databases (created at runtime)
│   ├── ticketing.db               # Business data
│   └── npc_manager.db             # Manager control/audit data
├── venv/                          # Python virtual environment
├── .git/                          # Git repository
├── .gitignore                     # Git ignore rules
├── env.example                    # Environment variable template
├── .env                           # Environment variables (not in repo)
├── requirements.txt               # Python dependencies
├── README.md                      # Setup and run instructions
├── SETUP_GUIDE.md                 # Quick setup guide
├── IMPLEMENTATION_SUMMARY.md      # Implementation summary
└── test_services.py               # Service testing script
```

---

## Database Schema (Implemented)

### Database: `npc_manager.db`

**Tables:**

1. **agents**
   - `agent_id` (PK, String) - Stable agent identity
   - `name` (String)
   - `owner_team` (String)
   - `owner_oncall` (String)
   - `permission_profile_id` (FK)
   - `status` (String: active|paused|revoked)
   - `created_at` (DateTime)

2. **permission_profiles**
   - `permission_profile_id` (PK, String)
   - `name` (String)
   - `env` (String: dev|staging|prod)
   - `rules_json` (JSON) - Permission rules
   - `created_at` (DateTime)

3. **action_requests**
   - `request_id` (PK, String/UUID)
   - `agent_id` (FK)
   - `timestamp` (DateTime)
   - `env` (String)
   - `action_type` (String: read|write|destructive|external)
   - `resource` (String)
   - `operation` (String)
   - `payload_hash` (String)
   - `payload_json` (JSON)
   - `risk_level` (String: low|medium|high)
   - `approval_required` (Boolean)
   - `decision` (String: allow|deny|pending)
   - `decision_reason` (Text)

4. **approvals**
   - `approval_id` (PK, String/UUID)
   - `request_id` (FK)
   - `status` (String: approved|rejected|expired)
   - `approver` (String)
   - `channel` (String: cli|slack|servicenow_mock)
   - `comment` (Text)
   - `timestamp` (DateTime)

5. **executions**
   - `execution_id` (PK, String/UUID)
   - `request_id` (FK)
   - `downstream_system` (String)
   - `downstream_status` (Integer)
   - `downstream_response_hash` (String)
   - `executed_at` (DateTime)
   - `error` (Text, nullable)

6. **guardrail_events**
   - `event_id` (PK, String/UUID)
   - `request_id` (FK)
   - `guardrail` (String)
   - `triggered` (Boolean)
   - `details` (JSON)
   - `timestamp` (DateTime)

7. **manager_controls**
   - `id` (PK, Integer)
   - `global_kill_switch` (Boolean)
   - `updated_at` (DateTime)

### Database: `ticketing.db`

**Tables:**

1. **customers**
   - `id` (PK, Integer)
   - `name` (String)
   - `email` (String, unique)
   - `do_not_contact` (Boolean)
   - `created_at` (DateTime)

2. **tickets**
   - `id` (PK, Integer)
   - `customer_id` (FK)
   - `title` (String)
   - `description` (Text)
   - `status` (String: open|in_progress|resolved|closed)
   - `created_at` (DateTime)
   - `resolved_at` (DateTime, nullable)

---

## API Design (Implemented)

### Ticketing API Endpoints

**Base URL:** `http://localhost:8000`

- `GET /health` - Health check
- `GET /tickets` - List tickets (with optional filters: status, customer_id)
- `GET /tickets/{id}` - Get ticket details
- `PATCH /tickets/{id}` - Update ticket (status, title, description)
- `GET /customers/{id}` - Get customer details
- `POST /customers/{id}/email` - Send email to customer (mock implementation)

### NPC Manager API Endpoints

**Base URL:** `http://localhost:8001`

#### `POST /action` (Main Proxy Endpoint)

**Request Schema:**
```json
{
  "agent_id": "agent-support-001",
  "session_id": "uuid-string (optional)",
  "tool_name": "list_tickets|update_ticket|send_customer_email",
  "tool_args": {
    "ticket_id": 123,
    "status": "closed"
  },
  "env": "prod"
}
```

**Headers:**
- `X-Agent-ID: agent-support-001` (optional, can also be in body)

**Response Schema:**
```json
{
  "request_id": "uuid",
  "status": "executed|denied|error",
  "decision": "allow|deny",
  "result": { ... },
  "reason": "string (if denied)"
}
```

**Status Codes:**
- `200 OK`: Action executed or denied (check `decision` field)
- `403 Forbidden`: Action denied (guardrail, kill switch, or approval rejected)
- `404 Not Found`: Agent not found
- `500 Internal Server Error`: Execution error

**Note:** Endpoint is **synchronous** (blocks for approval). This is an MVP limitation documented in the design.

#### `GET /health`
Health check endpoint.

#### `GET /audit/timeline`
Query audit trail with optional parameters:
- `agent_id` (optional): Filter by agent
- `limit` (optional, default 50): Limit results

Returns timeline of action requests with associated approvals, executions, and guardrail events.

---

## Tool → Endpoint Mapping (Implemented)

The mapping is hard-coded in `npc_manager/main.py`:

- `list_tickets` → `GET /tickets?{query_params}`
  - Query params: status, customer_id (from tool_args)
  
- `update_ticket` → `PATCH /tickets/{ticket_id}`
  - Path param: ticket_id (from tool_args.ticket_id)
  - Body: tool_args excluding ticket_id
  
- `send_customer_email` → `POST /customers/{customer_id}/email`
  - Path param: customer_id (from tool_args.customer_id)
  - Body: tool_args excluding customer_id (subject, body)

---

## Permission Profile Rules Format (Implemented)

The `rules_json` field in `permission_profiles` table uses this schema:

```json
{
  "allowed_tools": ["list_tickets", "update_ticket", "send_customer_email"],
  "allowed_endpoints": [
    "GET /tickets",
    "GET /tickets/*",
    "PATCH /tickets/*",
    "POST /customers/*/email"
  ],
  "field_restrictions": {
    "update_ticket": ["status"]
  },
  "env": "prod"
}
```

**Note:** `allowed_endpoints` is included for documentation but not actively enforced in MVP (tool-level enforcement is used).

---

## Control Logic (Implemented)

### Risk Classification

**Tool → Action Type Mapping:**
- `list_tickets` → `read` (low risk)
- `update_ticket` → `write` (medium/high risk based on field)
- `send_customer_email` → `external` (high risk)

**Risk Level Rules:**
- `read` → `low`
- `write` → `medium` (non-prod) or `high` (prod, or if status change is destructive)
- `external` → `high`

### Approval Requirements

Approval is required if:
- `risk_level == "high"`, OR
- `risk_level == "medium"` AND `env == "prod"`

### Guardrails (Implemented)

1. **max_ticket_updates_per_run**
   - Limit: 5 updates per session
   - Tracking: By `(agent_id, session_id)` if session_id provided, else time-window (last 5 minutes)
   - **Status:** Implemented, may need refinement (see known issues)

2. **block_external_email_if_customer_do_not_contact**
   - Checks customer table in ticketing database
   - Blocks immediately if `do_not_contact == True`
   - **Status:** Working correctly

### Kill Switch

- Global flag in `manager_controls` table
- When enabled, all actions are denied immediately
- **Status:** Working correctly

---

## Agent Implementation (As-Built)

### Technology Changes

**Original Plan:** LangChain 0.1.4 with `AgentExecutor` and `create_openai_functions_agent`

**Actual Implementation:** LangChain 1.2.0 with LangGraph using `create_react_agent`

**Reason:** Python 3.14 compatibility - older LangChain versions had dependency conflicts.

### Agent Structure

**File:** `agent/agent.py`

- Uses `langchain_openai.ChatOpenAI` for LLM
- Uses `langgraph.prebuilt.create_react_agent` for agent creation
- Model: `gpt-4o-mini` (cost-efficient for MVP)
- Session ID: Generated per run, passed via environment variable to tools

### Tools Implementation

**File:** `agent/tools.py`

Three tools implemented:
1. `ListTicketsTool` - List tickets through NPC Manager
2. `UpdateTicketTool` - Update tickets through NPC Manager
3. `SendCustomerEmailTool` - Send emails through NPC Manager

**Tool Base Class:** Uses `langchain.tools.BaseTool` with proper type annotations for Pydantic 2.x compatibility.

**Note:** Tools call NPC Manager (`POST /action`), NOT Ticketing API directly.

---

## Approval Mechanism (Implemented)

**File:** `npc_manager/approval.py`

**Implementation:** CLI-based, synchronous blocking prompt

**Flow:**
1. Manager detects approval required
2. Blocks request thread (sync endpoint)
3. Displays approval prompt in terminal
4. Waits for user input (y/n)
5. Records approval decision
6. Updates action_request
7. Continues or denies execution

**MVP Limitation:** Blocks entire request thread. Production would use async workflow with polling/webhooks.

---

## State Flow (Implemented)

1. Create `action_request` with status `pending`
2. Check kill switch → deny if true
3. Check permissions → deny if not allowed
4. Check guardrails → deny if violation
5. Classify risk → set `approval_required` flag
6. If approval required: **block and prompt CLI** (sync endpoint)
7. Record approval decision
8. Execute downstream API call (if allowed)
9. Update `action_request.decision` to `allow`/`deny`
10. Create `execution` record
11. Return response

---

## Design Decisions & Corrections Made

### 1. LangChain Version Upgrade

**Decision:** Upgraded from LangChain 0.1.4 to 1.2.0

**Reason:** Python 3.14 compatibility issues with older versions (pydantic-core build failures)

**Impact:** 
- Changed from `AgentExecutor` + `create_openai_functions_agent` to LangGraph `create_react_agent`
- Updated agent code structure
- Updated tool type annotations for Pydantic 2.x

**Status:** ✅ Working

### 2. Python Version

**Actual:** Python 3.14.0

**Note:** Some packages show deprecation warnings for Python 3.14 (pydantic v1 compatibility), but functionality works correctly.

### 3. Synchronous Approval

**Decision:** Use sync FastAPI endpoints for approval

**Reason:** Simplest implementation for MVP, allows blocking CLI approval

**Production Consideration:** Would use async workflow with polling/webhooks

**Status:** ✅ Working as designed

### 4. Session ID Implementation

**Decision:** Pass session_id via environment variable from agent to tools

**Implementation:** Agent sets `AGENT_SESSION_ID` env var, tools read it

**Note:** Works but not ideal architecture - acceptable for MVP

**Production Consideration:** Would use proper context passing

### 5. Cross-Database Query

**Decision:** NPC Manager queries Ticketing database directly for do-not-contact check

**Implementation:** Import ticketing_api models and use separate session

**Note:** Works for MVP, but tight coupling

**Production Consideration:** Would use shared connection or service call

### 6. Tool Type Annotations

**Correction:** Added type annotations to BaseTool subclasses for Pydantic 2.x

**Fields:** `name: str`, `description: str`, `args_schema: type`

**Status:** ✅ Fixed

---

## Known Issues & Limitations

### 1. Max Updates Guardrail

**Issue:** Guardrail logic may not count correctly in all scenarios

**Status:** Needs refinement - counts all write actions, should count only approved ones in current session

**Workaround:** Time-window fallback works for demonstration

### 2. Database DateTime Deprecation

**Issue:** Using `datetime.utcnow()` which is deprecated in Python 3.14

**Status:** Non-critical warnings, functionality works

**Fix Needed:** Update to `datetime.now(datetime.UTC)`

### 3. Service Startup Timing

**Issue:** Services may need more time to start in automated scripts

**Status:** Works with manual startup, timing issues in automated demos

**Workaround:** Increased sleep times, or run services manually

### 4. Interactive Demo Requirements

**Issue:** Full demo requires interactive terminal for approval prompts

**Status:** Working as designed (CLI approval requires interaction)

**Solution:** Created `demo_simple.py` for automated testing

---

## MVP Limitations (As Documented)

These are intentional MVP simplifications:

1. **Synchronous Approval:** Blocks request thread (production: async workflow)
2. **CLI Approval Channel:** Terminal input only (production: Slack, ServiceNow, etc.)
3. **Hard-coded Mappings:** Tool → endpoint mapping in code (production: configurable)
4. **Simple Authentication:** agent_id header only (production: API keys, mTLS, OAuth)
5. **Two Separate Databases:** SQLite files (production: single DB with schemas or distributed)
6. **Local Only:** All services run locally (production: distributed deployment)
7. **Session ID via Env Var:** Not ideal architecture (production: proper context)

---

## Testing & Validation

### Automated Tests

**File:** `scripts/demo_simple.py`

Tests:
- ✅ Service health checks
- ✅ Do-not-contact guardrail
- ✅ Kill switch functionality
- ✅ Audit trail query

### Manual Testing

**File:** `scripts/demo.py`

Full interactive demo with:
- Agent execution
- Approval prompts
- All guardrails
- Kill switch
- Audit trail

### Service Testing

**File:** `test_services.py`

Quick service startup verification.

---

## Seed Data (Implemented)

**File:** `scripts/setup_db.py`

**Ticketing Database:**
- 2 customers (one with `do_not_contact=True`)
- 12 tickets (mix of resolved/open, resolvable/ambiguous)

**NPC Manager Database:**
- 3 permission profiles:
  - `read_only` - Read-only access
  - `write_nonprod` - Write access in dev
  - `write_prod_with_approval` - Write access in prod with approval
- 1 agent: `agent-support-001` with `write_prod_with_approval` profile
- Manager controls (global_kill_switch=False)

---

## Environment Configuration

**File:** `.env` (not in repo, use `env.example` as template)

**Variables:**
- `OPENAI_API_KEY` - Required for agent
- `NPC_MANAGER_URL` - Default: http://localhost:8001
- `TICKETING_API_URL` - Default: http://localhost:8000
- `TICKETING_DB_PATH` - Default: database/ticketing.db
- `NPC_MANAGER_DB_PATH` - Default: database/npc_manager.db

---

## Success Criteria (Achieved)

The MVP successfully demonstrates:

- ✅ Agent executes write operations autonomously
- ✅ Every action is attributed to agent_id with ownership
- ✅ High-risk actions require approval before execution
- ✅ Guardrails block violations (do-not-contact working, max-updates needs refinement)
- ✅ Kill switch stops all agent actions instantly
- ✅ Audit trail answers: who, what, why, when, who approved
- ✅ Agent code unchanged when controls are added (tools call manager, not API)

---

## Future Enhancements (Post-MVP)

These are documented but not implemented in MVP:

1. Replace hard-coded permissions with configurable rules
2. Swap CLI approval for real ServiceNow / Slack integration
3. Introduce environment separation
4. Add proper authentication (API keys, mTLS, OAuth)
5. Implement async approval workflow
6. Add distributed deployment support
7. Refine max-updates guardrail logic
8. Update datetime usage to remove deprecation warnings
9. Add unit tests and integration tests
10. Add monitoring and alerting

---

## Documentation Files

- `README.md` - Setup and run instructions
- `SETUP_GUIDE.md` - Quick setup guide
- `IMPLEMENTATION_SUMMARY.md` - Implementation summary
- `Product Planning/design_review.md` - Initial design review
- `Product Planning/design_review_summary.md` - Design review summary
- `Product Planning/final_design_document.md` - This document

---

## Conclusion

NPC Manager 1 MVP has been successfully implemented according to the design plan, with necessary adjustments for Python 3.14 and LangChain 1.2.0 compatibility. All core functionality is operational and demonstrates the key concepts:

- Agent execution management
- Permission enforcement
- Approval workflows
- Guardrail enforcement
- Incident containment (kill switch)
- Complete audit trail

The system is ready for demonstration and further development.

