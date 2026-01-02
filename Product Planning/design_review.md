# NPC Manager 1 MVP Design Review

## Critical Challenges & Design Issues

### 1. **API Request Format Ambiguity** ⚠️ HIGH PRIORITY

**Issue**: The plan specifies `POST /action` but doesn't define how the manager maps agent tool calls to downstream API endpoints.

**Problem**: 
- Agent calls `update_ticket(ticket_id=123, status="closed")` 
- How does NPC Manager know this should become `PATCH /tickets/123` to Ticketing API?
- What's the request payload structure?

**Impact**: Cannot implement the proxy without this specification.

**Recommendation**: 
- Define explicit request schema: `{agent_id, tool_name, tool_args, env}`
- Create a mapping layer: `tool_name` → `downstream_endpoint + method + transformation`
- Example: `update_ticket` → `PATCH /tickets/{ticket_id}` with body transformation

### 2. **Blocking Approval in Async FastAPI** ⚠️ HIGH PRIORITY

**Issue**: CLI approval uses blocking `input()`, but FastAPI is async. Blocking calls freeze the event loop.

**Problem**:
```python
# This will block entire server
approval = input("Approve? [y/n]: ")  # BAD in async context
```

**Impact**: Entire NPC Manager service freezes during approval, can't handle other requests.

**Recommendation Options**:
1. **Option A (MVP-friendly)**: Make approval endpoint synchronous (remove async)
   - FastAPI allows sync endpoints
   - Acceptable for MVP since approval blocks anyway
   - Simplest fix

2. **Option B**: Use background task + polling
   - Return `request_id` immediately with status "pending"
   - Agent polls for approval status
   - CLI runs in separate process/thread
   - More complex, but more "correct"

3. **Option C**: Separate approval service
   - Manager writes to approval queue
   - Separate CLI tool reads queue, writes decisions
   - Manager polls for decisions
   - Most architecture-clean, but adds complexity

**Recommendation**: **Option A** for MVP (sync endpoint), document as MVP limitation.

### 3. **Session/Run Tracking for Guardrails** ⚠️ MEDIUM PRIORITY

**Issue**: `max_ticket_updates_per_run` guardrail needs to track writes across a "run", but what defines a run?

**Problem**:
- Agent makes multiple tool calls (list_tickets, update_ticket, update_ticket, ...)
- How does manager know these are part of one "run"?
- No session identifier in the design

**Impact**: Guardrail can't be enforced correctly.

**Recommendation**:
- Add `session_id` to agent tool calls (agent generates UUID at start of run)
- Track writes per `(agent_id, session_id)` 
- Alternative: Use time window (last N minutes) - simpler but less precise
- For MVP: Time window (e.g., last 5 minutes) is acceptable

### 4. **Agent Tool Enforcement** ⚠️ MEDIUM PRIORITY

**Issue**: Plan says "agent tools call NPC Manager" but there's no enforcement. Agent code could be modified to call Ticketing API directly.

**Problem**: This is a demo/educational issue, not a security issue. But for the demo narrative to work, we need clear separation.

**Impact**: Demo might not clearly show "agent unchanged" narrative if it's easy to bypass.

**Recommendation**:
- Document this as a limitation: "In production, network policies would enforce routing"
- For demo: Use different base URLs in config, make it obvious when wrong path is taken
- Consider: Agent config specifies manager URL, tools are hardcoded to use it

### 5. **Action Request State Machine** ⚠️ MEDIUM PRIORITY

**Issue**: Flow is: create request → check approval → execute. But what if approval is pending?

**Problem**:
- If approval required and pending, does manager return immediately?
- Does it block and wait (problematic with async)?
- How does agent know action is pending vs. denied vs. executed?

**Impact**: Unclear behavior, hard to implement correctly.

**Recommendation**:
- Define clear states: `pending` → `approved/denied` → `executing` → `completed/failed`
- For CLI approval (blocking): Manager blocks until approval decision, then executes
- Return appropriate HTTP status: 202 (Accepted) if pending, 200 if executed immediately, 403 if denied
- Document: "MVP uses synchronous approval; production would use async workflow"

### 6. **Two Separate Databases** ⚠️ LOW PRIORITY

**Issue**: Two SQLite files (`ticketing.db`, `npc_manager.db`) adds operational complexity.

**Problem**: Need to manage two DB connections, migrations, etc. SQLite doesn't support schemas.

**Impact**: Minor - adds slight complexity but keeps separation of concerns clear.

**Recommendation**: 
- Keep as-is for MVP (clear separation demonstrates the concept)
- Document: "Production would use single database with schemas or separate databases by design"
- Alternative: Single database with table prefixes - simpler but less clean separation

### 7. **Permission Profile Rule Format** ⚠️ MEDIUM PRIORITY

**Issue**: Schema has `rules_json` but format is unspecified.

**Problem**: 
- How do we encode "allow PATCH /tickets/* but only status field"?
- How do we map tool names to permissions?

**Impact**: Permission checks can't be implemented without format specification.

**Recommendation**:
- Define simple JSON schema for MVP:
```json
{
  "allowed_tools": ["list_tickets", "update_ticket"],
  "allowed_endpoints": ["GET /tickets", "PATCH /tickets/*"],
  "field_restrictions": {
    "update_ticket": ["status"]  // only allow status field
  }
}
```
- Hard-code mapping: `tool_name` → `endpoint pattern`
- Document as MVP simplification

### 8. **Demo Script Execution Coordination** ⚠️ MEDIUM PRIORITY

**Issue**: Demo needs to run Ticketing API, NPC Manager, and agent - how do they coordinate?

**Problem**: 
- Three processes need to start in order
- Port conflicts need to be managed
- Demo script needs to know when services are ready

**Impact**: Demo might be hard to run, breaks user experience.

**Recommendation**:
- Use fixed ports: Ticketing API (8000), NPC Manager (8001)
- Add health check endpoints to both services
- Demo script: Start services as subprocesses, wait for health checks, then run agent
- Provide simple shell script alternative: `./run_demo.sh`
- Document: "For production demos, use docker-compose or process manager"

### 9. **Error Handling & Audit Integrity** ⚠️ MEDIUM PRIORITY

**Issue**: What if Ticketing API succeeds but execution record write fails?

**Problem**: 
- Action executed but not recorded
- Audit trail incomplete
- Hard to recover

**Impact**: Audit trail loses integrity, can't answer "what executed?"

**Recommendation**:
- Use database transactions where possible
- For NPC Manager → Ticketing API: Write execution record in same transaction as action_request update
- Document limitation: "Network failures between manager and business API can cause inconsistencies; production would use distributed transactions or compensation"
- Add: Log all operations even if DB write fails (at minimum)

### 10. **Authentication Simplification** ⚠️ LOW PRIORITY (Acceptable for MVP)

**Issue**: Plan says "agent_id from request header" but no real auth.

**Problem**: Any client can claim to be any agent_id.

**Impact**: Not a security issue for MVP (local/demo), but worth documenting.

**Recommendation**: 
- Document: "MVP uses agent_id header only; production would use API keys, mTLS, or OAuth"
- For demo: This is acceptable - the point is attribution, not security

## Recommended Revisions

### Critical Revisions (Must Fix)

1. **Define API Request Schema**:
   - Add explicit request/response format to plan
   - Define tool → endpoint mapping strategy

2. **Fix Async/Blocking Issue**:
   - Use sync FastAPI endpoints for approval flow
   - Document as MVP limitation

3. **Define Session Tracking**:
   - Add `session_id` parameter or use time-window approach
   - Document in guardrail implementation

4. **Clarify Action Request Flow**:
   - Define state machine explicitly
   - Specify HTTP response codes for each state

### Medium Priority Revisions (Should Fix)

5. **Define Permission Rule Format**:
   - Specify JSON schema for `rules_json`
   - Document tool → endpoint mapping

6. **Clarify Demo Execution**:
   - Add process coordination strategy
   - Specify ports and health checks

7. **Add Error Handling Strategy**:
   - Document transaction boundaries
   - Specify audit integrity guarantees

### Low Priority (Nice to Have)

8. Consider single database vs. two (keep as-is for clarity)
9. Document authentication limitations
10. Add agent tool enforcement notes (documentation only)

## Architecture Decisions to Document

1. **Why separate databases?** - Clear separation of concerns, demonstrates manager as separate system
2. **Why blocking approval?** - Simplest for MVP, demonstrates concept without async complexity
3. **Why single /action endpoint?** - Unified control point, easier to audit and control
4. **Why tool-based rather than endpoint-based?** - Agent abstraction level (tools) vs. implementation level (endpoints)

## Risk Assessment

**High Risk Areas**:
- Async/blocking mismatch (could prevent demo from working)
- Unclear API contract (could block implementation)

**Medium Risk Areas**:
- Session tracking (guardrail might not work correctly)
- State machine ambiguity (incorrect behavior)

**Low Risk Areas**:
- Two databases (operational annoyance, not blocker)
- Authentication (acceptable for MVP)

## Questions for Clarification

1. Should approval be blocking (simpler) or async (more realistic)?
2. What defines a "run" for guardrail tracking - session_id or time window?
3. What's the exact request format for `POST /action`?
4. Should demo script handle service orchestration, or provide manual instructions?

