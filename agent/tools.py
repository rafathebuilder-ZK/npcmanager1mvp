"""Agent tools that call NPC Manager (not Ticketing API directly)."""
import os
import httpx
from typing import Dict, Any, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


NPC_MANAGER_URL = os.getenv("NPC_MANAGER_URL", "http://localhost:8001")


class ListTicketsInput(BaseModel):
    """Input for list_tickets tool."""
    status: Optional[str] = Field(None, description="Filter by ticket status (open, resolved, closed, etc.)")
    customer_id: Optional[int] = Field(None, description="Filter by customer ID")


class UpdateTicketInput(BaseModel):
    """Input for update_ticket tool."""
    ticket_id: int = Field(description="ID of the ticket to update")
    status: Optional[str] = Field(None, description="New status (e.g., 'closed', 'resolved', 'in_progress')")


class SendCustomerEmailInput(BaseModel):
    """Input for send_customer_email tool."""
    customer_id: int = Field(description="ID of the customer to email")
    subject: str = Field(description="Email subject")
    body: str = Field(description="Email body")


class ListTicketsTool(BaseTool):
    """Tool to list tickets through NPC Manager."""
    name: str = "list_tickets"
    description: str = "List support tickets. Can filter by status or customer_id. Returns a list of tickets with their details."
    args_schema: type = ListTicketsInput
    
    def _run(self, status: Optional[str] = None, customer_id: Optional[int] = None) -> str:
        """Execute the tool."""
        tool_args = {}
        if status:
            tool_args["status"] = status
        if customer_id:
            tool_args["customer_id"] = customer_id
        
        # Call NPC Manager
        try:
            with httpx.Client() as client:
                # Get session_id from environment (set by agent)
                session_id = os.getenv("AGENT_SESSION_ID")
                response = client.post(
                    f"{NPC_MANAGER_URL}/action",
                    json={
                        "agent_id": "agent-support-001",
                        "session_id": session_id,
                        "tool_name": "list_tickets",
                        "tool_args": tool_args,
                        "env": "prod"
                    },
                    headers={"X-Agent-ID": "agent-support-001"},
                    timeout=300.0  # Long timeout for approval blocking
                )
                if response.status_code == 200:
                    result = response.json()
                    if result.get("decision") == "allow" and result.get("result"):
                        tickets = result["result"]
                        if isinstance(tickets, list):
                            return f"Found {len(tickets)} tickets: {tickets}"
                        return str(result["result"])
                    else:
                        return f"Request denied: {result.get('reason', 'Unknown reason')}"
                else:
                    return f"Error: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Error calling NPC Manager: {str(e)}"
    
    async def _arun(self, status: Optional[str] = None, customer_id: Optional[int] = None) -> str:
        """Async execution (not used in sync context)."""
        return self._run(status, customer_id)


class UpdateTicketTool(BaseTool):
    """Tool to update tickets through NPC Manager."""
    name: str = "update_ticket"
    description: str = "Update a support ticket (e.g., change status to 'closed' or 'resolved'). Requires ticket_id and status."
    args_schema: type = UpdateTicketInput
    
    def _run(self, ticket_id: int, status: Optional[str] = None) -> str:
        """Execute the tool."""
        tool_args = {"ticket_id": ticket_id}
        if status:
            tool_args["status"] = status
        
        # Call NPC Manager
        try:
            with httpx.Client() as client:
                # Get session_id from environment (set by agent)
                session_id = os.getenv("AGENT_SESSION_ID")
                response = client.post(
                    f"{NPC_MANAGER_URL}/action",
                    json={
                        "agent_id": "agent-support-001",
                        "session_id": session_id,
                        "tool_name": "update_ticket",
                        "tool_args": tool_args,
                        "env": "prod"
                    },
                    headers={"X-Agent-ID": "agent-support-001"},
                    timeout=300.0  # Long timeout for approval blocking
                )
                if response.status_code == 200:
                    result = response.json()
                    if result.get("decision") == "allow" and result.get("result"):
                        return f"Ticket {ticket_id} updated successfully: {result['result']}"
                    else:
                        return f"Request denied: {result.get('reason', 'Unknown reason')}"
                else:
                    return f"Error: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Error calling NPC Manager: {str(e)}"
    
    async def _arun(self, ticket_id: int, status: Optional[str] = None) -> str:
        """Async execution (not used in sync context)."""
        return self._run(ticket_id, status)


class SendCustomerEmailTool(BaseTool):
    """Tool to send emails to customers through NPC Manager."""
    name: str = "send_customer_email"
    description: str = "Send an email to a customer. Requires customer_id, subject, and body. Will be blocked if customer has do_not_contact flag."
    args_schema: type = SendCustomerEmailInput
    
    def _run(self, customer_id: int, subject: str, body: str) -> str:
        """Execute the tool."""
        tool_args = {
            "customer_id": customer_id,
            "subject": subject,
            "body": body
        }
        
        # Call NPC Manager
        try:
            with httpx.Client() as client:
                # Get session_id from environment (set by agent)
                session_id = os.getenv("AGENT_SESSION_ID")
                response = client.post(
                    f"{NPC_MANAGER_URL}/action",
                    json={
                        "agent_id": "agent-support-001",
                        "session_id": session_id,
                        "tool_name": "send_customer_email",
                        "tool_args": tool_args,
                        "env": "prod"
                    },
                    headers={"X-Agent-ID": "agent-support-001"},
                    timeout=300.0  # Long timeout for approval blocking
                )
                if response.status_code == 200:
                    result = response.json()
                    if result.get("decision") == "allow" and result.get("result"):
                        return f"Email sent successfully: {result['result']}"
                    else:
                        return f"Request denied: {result.get('reason', 'Unknown reason')}"
                else:
                    return f"Error: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Error calling NPC Manager: {str(e)}"
    
    async def _arun(self, customer_id: int, subject: str, body: str) -> str:
        """Async execution (not used in sync context)."""
        return self._run(customer_id, subject, body)


def get_tools(session_id: Optional[str] = None):
    """
    Get list of tools for the agent.
    
    Args:
        session_id: Optional session ID to include in requests (not used in MVP but structure supports it)
    
    Returns:
        List of tool instances
    """
    return [
        ListTicketsTool(),
        UpdateTicketTool(),
        SendCustomerEmailTool()
    ]

