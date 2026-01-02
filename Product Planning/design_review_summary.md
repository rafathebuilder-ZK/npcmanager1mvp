# Design Review Summary

## Review Completed

A comprehensive design review has been conducted and critical issues have been addressed in the updated plan.

## Critical Issues Identified & Fixed

### 1. ✅ API Request Format - **FIXED**
**Issue**: Unclear how agent tool calls map to downstream API endpoints.

**Resolution**: 
- Added explicit request/response schema to plan
- Defined tool → endpoint mapping strategy (hard-coded for MVP)
- Specified request format with `agent_id`, `session_id`, `tool_name`, `tool_args`, `env`

### 2. ✅ Async/Blocking Mismatch - **FIXED**
**Issue**: CLI approval uses blocking `input()`, but FastAPI is async by default.

**Resolution**:
- Changed NPC Manager endpoints to **synchronous** (FastAPI supports sync endpoints)
- Documented as intentional MVP limitation
- Allows blocking CLI approval without event loop issues

### 3. ✅ Session Tracking - **FIXED**
**Issue**: Guardrail `max_ticket_updates_per_run` needs to track "runs" but concept was undefined.

**Resolution**:
- Agent generates `session_id` (UUID) per run, includes in all tool calls
- Guardrail tracks writes per `(agent_id, session_id)`
- Fallback to time-window (5 minutes) if session_id not provided

### 4. ✅ Action Request State Flow - **FIXED**
**Issue**: Unclear behavior when approval is pending or required.

**Resolution**:
- Defined explicit state flow (pending → approved/denied → executing → completed)
- Since endpoints are sync, approval blocks until decision
- Specified HTTP response codes (200 for executed, 403 for denied)

### 5. ✅ Permission Rule Format - **FIXED**
**Issue**: `rules_json` field format was unspecified.

**Resolution**:
- Defined JSON schema with `allowed_tools`, `allowed_endpoints`, `field_restrictions`
- Documented tool → action_type mapping
- Hard-coded mapping for MVP (production would be configurable)

### 6. ✅ Demo Execution Coordination - **FIXED**
**Issue**: Demo needs to run multiple services, coordination unclear.

**Resolution**:
- Added service orchestration details (subprocesses, health checks, ports)
- Specified ports: Ticketing API (8000), NPC Manager (8001)
- Added health check endpoints requirement

## Medium Priority Issues Addressed

### 7. ✅ Error Handling Strategy
**Resolution**: Documented transaction boundaries and MVP limitations (network failures between services may cause inconsistencies).

### 8. ✅ Agent Tool Enforcement
**Resolution**: Documented as configuration-based (environment variables), noted as MVP limitation with production approach.

### 9. ✅ Authentication Simplification
**Resolution**: Documented as MVP limitation (agent_id header only), production would use proper auth.

## Architecture Decisions Documented

All MVP limitations and design choices have been explicitly documented in the updated plan:
- Why synchronous endpoints (allows blocking approval)
- Why two databases (separation of concerns)
- Why hard-coded mappings (simplicity for MVP)
- What production would do differently

## Files Created

1. **design_review.md** - Comprehensive detailed review with all issues, risks, and recommendations
2. **design_review_summary.md** - This summary document
3. **Updated plan file** - All critical fixes applied

## Status: Ready for Implementation

All critical design issues have been resolved. The plan is now:
- ✅ Technically feasible
- ✅ Architecturally sound for MVP
- ✅ Clear enough to implement
- ✅ Documented with limitations and production considerations

The MVP can proceed to implementation.

