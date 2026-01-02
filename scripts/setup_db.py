"""Database setup and seeding script."""
import sys
import os
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from datetime import datetime
import json

# Import database and models
from ticketing_api.database import engine as ticketing_engine, Base as TicketingBase
from ticketing_api.models import Customer, Ticket

from npc_manager.database import engine as npc_engine, Base as NPCMgrBase, SessionLocal
from npc_manager.models import (
    PermissionProfile, Agent, ManagerControl, ActionRequest, Approval, Execution, GuardrailEvent
)


def setup_ticketing_db():
    """Initialize and seed ticketing database."""
    print("Setting up ticketing database...")
    
    # Create tables
    TicketingBase.metadata.create_all(bind=ticketing_engine)
    
    # Create session
    from ticketing_api.database import SessionLocal as TicketingSession
    db = TicketingSession()
    
    try:
        # Clear existing data (for re-running)
        db.query(Ticket).delete()
        db.query(Customer).delete()
        db.commit()
        
        # Create customers
        customer1 = Customer(
            id=1,
            name="John Doe",
            email="john.doe@example.com",
            do_not_contact=False
        )
        
        customer2 = Customer(
            id=2,
            name="Jane Smith",
            email="jane.smith@example.com",
            do_not_contact=True  # This customer should not be contacted
        )
        
        db.add(customer1)
        db.add(customer2)
        db.commit()
        
        # Create tickets
        tickets_data = [
            # Resolvable tickets
            {"id": 1, "customer_id": 1, "title": "Password reset request", "description": "Need to reset password", "status": "resolved"},
            {"id": 2, "customer_id": 1, "title": "Feature question", "description": "How do I use feature X?", "status": "resolved"},
            {"id": 3, "customer_id": 1, "title": "Billing inquiry", "description": "Question about invoice", "status": "resolved"},
            {"id": 4, "customer_id": 1, "title": "Account setup", "description": "Need help setting up account", "status": "resolved"},
            {"id": 5, "customer_id": 1, "title": "Technical support", "description": "Issue resolved via email", "status": "resolved"},
            {"id": 6, "customer_id": 1, "title": "Refund request", "description": "Processing refund", "status": "resolved"},
            
            # Ambiguous tickets
            {"id": 7, "customer_id": 1, "title": "Service outage", "description": "Experiencing intermittent issues", "status": "open"},
            {"id": 8, "customer_id": 1, "title": "Feature request", "description": "Would like to see new feature", "status": "open"},
            {"id": 9, "customer_id": 1, "title": "Performance concern", "description": "System seems slow sometimes", "status": "open"},
            
            # Open tickets that might be closable
            {"id": 10, "customer_id": 2, "title": "Account question", "description": "Question answered in documentation", "status": "open"},
            {"id": 11, "customer_id": 2, "title": "Setup help", "description": "Already provided via email", "status": "open"},
            {"id": 12, "customer_id": 1, "title": "General inquiry", "description": "Customer satisfied with response", "status": "open"},
        ]
        
        for ticket_data in tickets_data:
            ticket = Ticket(
                id=ticket_data["id"],
                customer_id=ticket_data["customer_id"],
                title=ticket_data["title"],
                description=ticket_data["description"],
                status=ticket_data["status"],
                created_at=datetime.utcnow()
            )
            if ticket_data["status"] == "resolved":
                ticket.resolved_at = datetime.utcnow()
            db.add(ticket)
        
        db.commit()
        print(f"✓ Created {len(tickets_data)} tickets and 2 customers")
        
    finally:
        db.close()


def setup_npc_manager_db():
    """Initialize and seed NPC Manager database."""
    print("Setting up NPC Manager database...")
    
    # Create tables
    NPCMgrBase.metadata.create_all(bind=npc_engine)
    
    db = SessionLocal()
    
    try:
        # Clear existing data (for re-running)
        # Clear in order to respect foreign key constraints
        db.query(Execution).delete()
        db.query(Approval).delete()
        db.query(GuardrailEvent).delete()
        db.query(ActionRequest).delete()
        db.query(Agent).delete()
        db.query(PermissionProfile).delete()
        db.query(ManagerControl).delete()
        db.commit()
        
        # Create permission profiles
        read_only_profile = PermissionProfile(
            permission_profile_id="read_only",
            name="Read Only",
            env="prod",
            rules_json={
                "allowed_tools": ["list_tickets"],
                "allowed_endpoints": ["GET /tickets", "GET /tickets/*"],
                "field_restrictions": {},
                "env": "prod"
            },
            created_at=datetime.utcnow()
        )
        
        write_nonprod_profile = PermissionProfile(
            permission_profile_id="write_nonprod",
            name="Write Non-Prod",
            env="dev",
            rules_json={
                "allowed_tools": ["list_tickets", "update_ticket"],
                "allowed_endpoints": ["GET /tickets", "GET /tickets/*", "PATCH /tickets/*"],
                "field_restrictions": {
                    "update_ticket": ["status"]
                },
                "env": "dev"
            },
            created_at=datetime.utcnow()
        )
        
        write_prod_with_approval_profile = PermissionProfile(
            permission_profile_id="write_prod_with_approval",
            name="Write Prod With Approval",
            env="prod",
            rules_json={
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
            },
            created_at=datetime.utcnow()
        )
        
        db.add(read_only_profile)
        db.add(write_nonprod_profile)
        db.add(write_prod_with_approval_profile)
        db.commit()
        
        # Create agent
        agent = Agent(
            agent_id="agent-support-001",
            name="Support Ticket Manager Agent",
            owner_team="SupportOps",
            owner_oncall="support-oncall@example.com",
            permission_profile_id="write_prod_with_approval",
            status="active",
            created_at=datetime.utcnow()
        )
        
        db.add(agent)
        db.commit()
        
        # Create manager controls
        control = ManagerControl(
            id=1,
            global_kill_switch=False,
            updated_at=datetime.utcnow()
        )
        
        db.add(control)
        db.commit()
        
        print("✓ Created 3 permission profiles, 1 agent, and manager controls")
        
    finally:
        db.close()


def main():
    """Main setup function."""
    print("=" * 60)
    print("Database Setup and Seeding")
    print("=" * 60)
    
    setup_ticketing_db()
    setup_npc_manager_db()
    
    print("=" * 60)
    print("Database setup complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

