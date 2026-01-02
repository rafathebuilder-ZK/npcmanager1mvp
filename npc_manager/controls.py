"""Permission checks, risk classification, and guardrail logic."""
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from .models import Agent, PermissionProfile, ActionRequest, ManagerControl, GuardrailEvent
import uuid
import hashlib
import json


def get_manager_control(db: Session) -> ManagerControl:
    """Get manager controls (singleton pattern)."""
    control = db.query(ManagerControl).first()
    if not control:
        control = ManagerControl(
            id=1,
            global_kill_switch=False
        )
        db.add(control)
        db.commit()
        db.refresh(control)
    return control


def check_kill_switch(db: Session) -> bool:
    """Check if global kill switch is enabled."""
    control = get_manager_control(db)
    return control.global_kill_switch


def classify_risk(tool_name: str, tool_args: Dict[str, Any], env: str) -> tuple[str, str]:
    """
    Classify action type and risk level.
    
    Returns:
        tuple: (action_type, risk_level)
    """
    # Tool to action type mapping
    tool_to_action = {
        "list_tickets": "read",
        "update_ticket": "write",
        "send_customer_email": "external"
    }
    
    action_type = tool_to_action.get(tool_name, "write")
    
    # Risk classification
    if action_type == "read":
        risk_level = "low"
    elif action_type == "write":
        # Check if it's a destructive operation
        if tool_args.get("status") in ["closed", "deleted"]:
            risk_level = "high"
        else:
            risk_level = "medium" if env == "prod" else "low"
    elif action_type == "external":
        risk_level = "high"
    else:
        risk_level = "medium"
    
    return action_type, risk_level


def check_permissions(
    db: Session,
    agent: Agent,
    tool_name: str,
    tool_args: Dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """
    Check if agent has permission to perform action.
    
    Returns:
        tuple: (allowed, reason)
    """
    profile = agent.permission_profile
    
    # Check if tool is allowed
    allowed_tools = profile.rules_json.get("allowed_tools", [])
    if tool_name not in allowed_tools:
        return False, f"Tool '{tool_name}' not in allowed_tools"
    
    # Check field restrictions for update_ticket
    if tool_name == "update_ticket":
        field_restrictions = profile.rules_json.get("field_restrictions", {})
        allowed_fields = field_restrictions.get("update_ticket", [])
        if allowed_fields:
            # Only allow specified fields
            provided_fields = set(tool_args.keys())
            allowed_field_set = set(allowed_fields)
            if not provided_fields.issubset(allowed_field_set):
                disallowed = provided_fields - allowed_field_set
                return False, f"Fields {disallowed} not allowed. Allowed: {allowed_fields}"
    
    return True, None


def requires_approval(action_type: str, risk_level: str, env: str) -> bool:
    """Determine if action requires approval."""
    # Approval logic based on risk and environment
    if risk_level == "high":
        return True
    if risk_level == "medium" and env == "prod":
        return True
    return False


def check_guardrail_max_updates(
    db: Session,
    agent_id: str,
    session_id: Optional[str],
    max_updates: int = 5
) -> tuple[bool, Optional[str]]:
    """
    Check guardrail: max ticket updates per run.
    
    Returns:
        tuple: (allowed, reason)
    """
    # Calculate time window (5 minutes if no session_id)
    if session_id:
        # Count writes in this session
        time_window = datetime.utcnow() - timedelta(hours=24)  # Long window for session tracking
        count = db.query(ActionRequest).filter(
            ActionRequest.agent_id == agent_id,
            ActionRequest.action_type == "write",
            ActionRequest.timestamp >= time_window,
            ActionRequest.decision == "allow"
        ).count()
    else:
        # Use time window (last 5 minutes)
        time_window = datetime.utcnow() - timedelta(minutes=5)
        count = db.query(ActionRequest).filter(
            ActionRequest.agent_id == agent_id,
            ActionRequest.action_type == "write",
            ActionRequest.timestamp >= time_window,
            ActionRequest.decision == "allow"
        ).count()
    
    if count >= max_updates:
        return False, f"Guardrail: max_ticket_updates_per_run ({max_updates}) exceeded. Count: {count}"
    
    return True, None


def check_guardrail_do_not_contact(
    db: Session,
    tool_name: str,
    tool_args: Dict[str, Any]
) -> tuple[bool, Optional[str], Optional[int]]:
    """
    Check guardrail: block email if customer has do_not_contact flag.
    
    Returns:
        tuple: (allowed, reason, customer_id)
    """
    if tool_name != "send_customer_email":
        return True, None, None
    
    customer_id = tool_args.get("customer_id")
    if not customer_id:
        return True, None, None
    
    # Check customer in ticketing database
    # Note: This is a cross-database query - in production would use shared connection
    # For MVP, we'll query the ticketing database directly
    from ticketing_api.database import SessionLocal as TicketingSession
    from ticketing_api.models import Customer as TicketingCustomer
    
    ticketing_db = TicketingSession()
    try:
        customer = ticketing_db.query(TicketingCustomer).filter(
            TicketingCustomer.id == customer_id
        ).first()
        
        if customer and customer.do_not_contact:
            return False, f"Guardrail: Customer {customer_id} has do_not_contact flag set", customer_id
        
        return True, None, customer_id
    finally:
        ticketing_db.close()


def create_guardrail_event(
    db: Session,
    request_id: str,
    guardrail_name: str,
    triggered: bool,
    details: Optional[Dict[str, Any]] = None
):
    """Create a guardrail event record."""
    event = GuardrailEvent(
        event_id=str(uuid.uuid4()),
        request_id=request_id,
        guardrail=guardrail_name,
        triggered=triggered,
        details=details or {}
    )
    db.add(event)
    db.commit()


def hash_payload(payload: Dict[str, Any]) -> str:
    """Create hash of payload for audit immutability."""
    payload_str = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(payload_str.encode()).hexdigest()

