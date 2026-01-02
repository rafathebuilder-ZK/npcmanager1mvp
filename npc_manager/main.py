"""NPC Manager - Execution management layer for autonomous agents."""
from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import uuid
import httpx
import os
from datetime import datetime
from pydantic import BaseModel

from .database import engine, get_db, Base
from .models import ActionRequest, Execution
from .controls import (
    check_kill_switch,
    classify_risk,
    check_permissions,
    requires_approval,
    check_guardrail_max_updates,
    check_guardrail_do_not_contact,
    create_guardrail_event,
    hash_payload
)
from .approval import request_approval

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="NPC Manager", version="1.0.0")

# Configuration
TICKETING_API_URL = os.getenv("TICKETING_API_URL", "http://localhost:8000")


# Request/Response models
class ActionRequestModel(BaseModel):
    agent_id: str
    session_id: Optional[str] = None
    tool_name: str
    tool_args: Dict[str, Any]
    env: str = "prod"


class ActionResponse(BaseModel):
    request_id: str
    status: str
    decision: str
    result: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None


# Tool to endpoint mapping
TOOL_ENDPOINT_MAP = {
    "list_tickets": {
        "method": "GET",
        "path_template": "/tickets",
        "query_params": True
    },
    "update_ticket": {
        "method": "PATCH",
        "path_template": "/tickets/{ticket_id}",
        "body": True
    },
    "send_customer_email": {
        "method": "POST",
        "path_template": "/customers/{customer_id}/email",
        "body": True
    }
}


def get_agent(db: Session, agent_id: str):
    """Get agent by ID."""
    from .models import Agent
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    if agent.status != "active":
        raise HTTPException(status_code=403, detail=f"Agent {agent_id} is not active (status: {agent.status})")
    return agent


def map_tool_to_endpoint(tool_name: str, tool_args: Dict[str, Any]) -> tuple[str, str, Optional[Dict[str, Any]]]:
    """
    Map tool call to downstream API endpoint.
    
    Returns:
        tuple: (method, path, body)
    """
    mapping = TOOL_ENDPOINT_MAP.get(tool_name)
    if not mapping:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
    
    method = mapping["method"]
    path = mapping["path_template"]
    
    # Replace path parameters
    if tool_name == "list_tickets":
        # GET /tickets with query params
        path = "/tickets"
        body = None
    elif tool_name == "update_ticket":
        ticket_id = tool_args.get("ticket_id")
        if not ticket_id:
            raise HTTPException(status_code=400, detail="ticket_id required for update_ticket")
        path = f"/tickets/{ticket_id}"
        body = {k: v for k, v in tool_args.items() if k != "ticket_id"}
    elif tool_name == "send_customer_email":
        customer_id = tool_args.get("customer_id")
        if not customer_id:
            raise HTTPException(status_code=400, detail="customer_id required for send_customer_email")
        path = f"/customers/{customer_id}/email"
        body = {k: v for k, v in tool_args.items() if k != "customer_id"}
    
    return method, path, body


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/action", response_model=ActionResponse)
def execute_action(
    action_request: ActionRequestModel,
    x_agent_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Main proxy endpoint - receives agent tool calls and enforces controls.
    SYNC endpoint (blocks for approval).
    """
    # Use header if provided, otherwise use body
    agent_id = x_agent_id or action_request.agent_id
    
    # Get agent
    agent = get_agent(db, agent_id)
    
    # 1. Check kill switch
    if check_kill_switch(db):
        return ActionResponse(
            request_id="",
            status="denied",
            decision="deny",
            reason="Global kill switch is enabled"
        )
    
    # 2. Classify risk
    action_type, risk_level = classify_risk(
        action_request.tool_name,
        action_request.tool_args,
        action_request.env
    )
    
    # 3. Create action request record
    request_id = str(uuid.uuid4())
    payload_hash = hash_payload(action_request.tool_args)
    resource = f"{action_request.tool_name}/{action_request.tool_args}"
    
    # Map tool to operation
    mapping = TOOL_ENDPOINT_MAP.get(action_request.tool_name, {})
    operation = mapping.get("method", "UNKNOWN")
    
    action_request_record = ActionRequest(
        request_id=request_id,
        agent_id=agent_id,
        timestamp=datetime.utcnow(),
        env=action_request.env,
        action_type=action_type,
        resource=resource,
        operation=operation,
        payload_hash=payload_hash,
        payload_json=action_request.tool_args,
        risk_level=risk_level,
        approval_required=False,  # Will be set below
        decision="pending",
        decision_reason=None
    )
    
    # 4. Check permissions
    allowed, permission_reason = check_permissions(
        db,
        agent,
        action_request.tool_name,
        action_request.tool_args
    )
    
    if not allowed:
        action_request_record.decision = "deny"
        action_request_record.decision_reason = permission_reason
        db.add(action_request_record)
        db.commit()
        return ActionResponse(
            request_id=request_id,
            status="denied",
            decision="deny",
            reason=permission_reason
        )
    
    # 5. Check guardrails
    # Guardrail: max updates per run
    if action_type == "write":
        allowed_updates, guardrail_reason = check_guardrail_max_updates(
            db,
            agent_id,
            action_request.session_id
        )
        if not allowed_updates:
            create_guardrail_event(db, request_id, "max_ticket_updates_per_run", True, {"reason": guardrail_reason})
            action_request_record.decision = "deny"
            action_request_record.decision_reason = guardrail_reason
            db.add(action_request_record)
            db.commit()
            return ActionResponse(
                request_id=request_id,
                status="denied",
                decision="deny",
                reason=guardrail_reason
            )
        create_guardrail_event(db, request_id, "max_ticket_updates_per_run", False)
    
    # Guardrail: do not contact
    allowed_contact, contact_reason, customer_id = check_guardrail_do_not_contact(
        db,
        action_request.tool_name,
        action_request.tool_args
    )
    if not allowed_contact:
        create_guardrail_event(db, request_id, "block_external_email_if_customer_do_not_contact", True, {"customer_id": customer_id})
        action_request_record.decision = "deny"
        action_request_record.decision_reason = contact_reason
        db.add(action_request_record)
        db.commit()
        return ActionResponse(
            request_id=request_id,
            status="denied",
            decision="deny",
            reason=contact_reason
        )
    if action_request.tool_name == "send_customer_email":
        create_guardrail_event(db, request_id, "block_external_email_if_customer_do_not_contact", False)
    
    # 6. Check if approval required
    approval_required = requires_approval(action_type, risk_level, action_request.env)
    action_request_record.approval_required = approval_required
    
    db.add(action_request_record)
    db.commit()
    db.refresh(action_request_record)
    
    # 7. Request approval if needed
    if approval_required:
        approved = request_approval(db, action_request_record)
        if not approved:
            return ActionResponse(
                request_id=request_id,
                status="denied",
                decision="deny",
                reason="Approval rejected"
            )
        # Refresh to get updated decision
        db.refresh(action_request_record)
    
    # 8. Execute downstream API call
    try:
        method, path, body = map_tool_to_endpoint(action_request.tool_name, action_request.tool_args)
        url = f"{TICKETING_API_URL}{path}"
        
        with httpx.Client() as client:
            if method == "GET":
                # Build query params for list_tickets
                if action_request.tool_name == "list_tickets":
                    params = {k: v for k, v in action_request.tool_args.items()}
                    response = client.get(url, params=params)
                else:
                    response = client.get(url)
            elif method == "PATCH":
                response = client.patch(url, json=body)
            elif method == "POST":
                response = client.post(url, json=body)
            else:
                raise HTTPException(status_code=500, detail=f"Unsupported method: {method}")
            
            response_data = response.json() if response.status_code < 400 else {"error": response.text}
            
    except Exception as e:
        # Create execution record for error
        execution = Execution(
            execution_id=str(uuid.uuid4()),
            request_id=request_id,
            downstream_system="business_api",
            downstream_status=500,
            executed_at=datetime.utcnow(),
            error=str(e)
        )
        db.add(execution)
        action_request_record.decision = "deny"
        action_request_record.decision_reason = f"Execution error: {str(e)}"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Downstream API error: {str(e)}")
    
    # 9. Create execution record
    execution = Execution(
        execution_id=str(uuid.uuid4()),
        request_id=request_id,
        downstream_system="business_api",
        downstream_status=response.status_code,
        downstream_response_hash=hash_payload(response_data) if isinstance(response_data, dict) else None,
        executed_at=datetime.utcnow(),
        error=None
    )
    db.add(execution)
    
    # 10. Update action request
    action_request_record.decision = "allow" if response.status_code < 400 else "deny"
    action_request_record.decision_reason = f"Executed successfully" if response.status_code < 400 else f"HTTP {response.status_code}"
    db.commit()
    
    # 11. Return response
    if response.status_code >= 400:
        return ActionResponse(
            request_id=request_id,
            status="error",
            decision="deny",
            result=response_data,
            reason=f"Downstream API returned {response.status_code}"
        )
    
    return ActionResponse(
        request_id=request_id,
        status="executed",
        decision="allow",
        result=response_data
    )


@app.get("/audit/timeline")
def get_audit_timeline(
    agent_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get audit timeline for demo."""
    query = db.query(ActionRequest).order_by(ActionRequest.timestamp.desc())
    if agent_id:
        query = query.filter(ActionRequest.agent_id == agent_id)
    
    requests = query.limit(limit).all()
    
    timeline = []
    for req in requests:
        # Get approvals
        approvals = [{
            "status": a.status,
            "approver": a.approver,
            "channel": a.channel,
            "timestamp": a.timestamp.isoformat()
        } for a in req.approvals]
        
        # Get executions
        executions = [{
            "status": e.downstream_status,
            "executed_at": e.executed_at.isoformat(),
            "error": e.error
        } for e in req.executions]
        
        # Get guardrail events
        guardrails = [{
            "guardrail": g.guardrail,
            "triggered": g.triggered,
            "details": g.details
        } for g in req.guardrail_events]
        
        timeline.append({
            "request_id": req.request_id,
            "agent_id": req.agent_id,
            "timestamp": req.timestamp.isoformat(),
            "action_type": req.action_type,
            "resource": req.resource,
            "risk_level": req.risk_level,
            "approval_required": req.approval_required,
            "decision": req.decision,
            "decision_reason": req.decision_reason,
            "approvals": approvals,
            "executions": executions,
            "guardrail_events": guardrails
        })
    
    return {"timeline": timeline}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

