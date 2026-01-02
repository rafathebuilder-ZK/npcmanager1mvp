"""CLI-based approval mechanism for MVP."""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from .models import Approval, ActionRequest


def request_approval(
    db: Session,
    action_request: ActionRequest,
    channel: str = "cli"
) -> bool:
    """
    Request approval via CLI (blocking).
    
    Returns:
        bool: True if approved, False if rejected
    """
    # Display approval request
    print("\n" + "=" * 60)
    print("APPROVAL REQUEST")
    print("=" * 60)
    print(f"Agent ID: {action_request.agent_id}")
    print(f"Action Type: {action_request.action_type}")
    print(f"Resource: {action_request.resource}")
    print(f"Operation: {action_request.operation}")
    print(f"Risk Level: {action_request.risk_level}")
    print(f"Environment: {action_request.env}")
    if action_request.payload_json:
        print(f"Payload: {action_request.payload_json}")
    print("=" * 60)
    
    # Get user input
    while True:
        response = input(f"\nApprove {action_request.action_type} on {action_request.resource}? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            approved = True
            break
        elif response in ['n', 'no']:
            approved = False
            break
        else:
            print("Please enter 'y' for yes or 'n' for no")
    
    # Get optional comment
    comment = input("Comment (optional, press Enter to skip): ").strip()
    if not comment:
        comment = None
    
    # Create approval record
    approval = Approval(
        approval_id=str(uuid.uuid4()),
        request_id=action_request.request_id,
        status="approved" if approved else "rejected",
        approver="cli_user",  # MVP: hard-coded
        channel=channel,
        comment=comment,
        timestamp=datetime.utcnow()
    )
    
    db.add(approval)
    db.commit()
    
    # Update action request
    action_request.decision = "allow" if approved else "deny"
    action_request.decision_reason = f"Approval {'approved' if approved else 'rejected'} via {channel}"
    db.commit()
    
    return approved

