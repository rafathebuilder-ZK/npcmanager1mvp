"""Ticketing API - Business API that agents interact with through NPC Manager."""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr
from .database import engine, get_db, Base
from .models import Ticket, Customer

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Ticketing API", version="1.0.0")


# Pydantic models for request/response
class CustomerBase(BaseModel):
    name: str
    email: EmailStr
    do_not_contact: bool = False


class CustomerCreate(CustomerBase):
    pass


class CustomerResponse(CustomerBase):
    id: int
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class TicketBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "open"


class TicketCreate(TicketBase):
    customer_id: int


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class TicketResponse(TicketBase):
    id: int
    customer_id: int
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None

    class Config:
        from_attributes = True


class EmailRequest(BaseModel):
    subject: str
    body: str


# Endpoints
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Get customer by ID."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.get("/tickets", response_model=List[TicketResponse])
async def list_tickets(
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List tickets with optional filters."""
    query = db.query(Ticket)
    if status:
        query = query.filter(Ticket.status == status)
    if customer_id:
        query = query.filter(Ticket.customer_id == customer_id)
    tickets = query.all()
    return tickets


@app.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """Get ticket by ID."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@app.patch("/tickets/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: int,
    ticket_update: TicketUpdate,
    db: Session = Depends(get_db)
):
    """Update ticket."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Update fields
    if ticket_update.status is not None:
        ticket.status = ticket_update.status
        # Set resolved_at if status is resolved/closed
        if ticket_update.status in ["resolved", "closed"]:
            ticket.resolved_at = datetime.utcnow()
    if ticket_update.title is not None:
        ticket.title = ticket_update.title
    if ticket_update.description is not None:
        ticket.description = ticket_update.description

    db.commit()
    db.refresh(ticket)
    return ticket


@app.post("/customers/{customer_id}/email")
async def send_customer_email(
    customer_id: int,
    email_request: EmailRequest,
    db: Session = Depends(get_db)
):
    """Send email to customer (mock implementation)."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Mock email sending - in real implementation, this would send an actual email
    return {
        "status": "sent",
        "customer_id": customer_id,
        "customer_email": customer.email,
        "subject": email_request.subject,
        "body": email_request.body
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

