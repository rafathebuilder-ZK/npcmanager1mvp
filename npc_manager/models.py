"""SQLAlchemy models for NPC Manager."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class PermissionProfile(Base):
    """Permission profile model."""
    __tablename__ = "permission_profiles"

    permission_profile_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    env = Column(String, nullable=False)  # dev, staging, prod
    rules_json = Column(JSON, nullable=False)  # Permission rules
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    agents = relationship("Agent", back_populates="permission_profile")


class Agent(Base):
    """Agent identity model."""
    __tablename__ = "agents"

    agent_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    owner_team = Column(String, nullable=False)
    owner_oncall = Column(String, nullable=True)
    permission_profile_id = Column(String, ForeignKey("permission_profiles.permission_profile_id"), nullable=False)
    status = Column(String, default="active", nullable=False)  # active, paused, revoked
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    permission_profile = relationship("PermissionProfile", back_populates="agents")
    action_requests = relationship("ActionRequest", back_populates="agent")


class ActionRequest(Base):
    """Action request - intent-to-act record."""
    __tablename__ = "action_requests"

    request_id = Column(String, primary_key=True)
    agent_id = Column(String, ForeignKey("agents.agent_id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    env = Column(String, nullable=False)
    action_type = Column(String, nullable=False)  # read, write, destructive, external
    resource = Column(String, nullable=False)  # e.g., tickets/123, customers/42
    operation = Column(String, nullable=False)  # e.g., PATCH, SEND_EMAIL
    payload_hash = Column(String, nullable=True)
    payload_json = Column(JSON, nullable=True)
    risk_level = Column(String, nullable=False)  # low, medium, high
    approval_required = Column(Boolean, default=False, nullable=False)
    decision = Column(String, default="pending", nullable=False)  # allow, deny, pending
    decision_reason = Column(Text, nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="action_requests")
    approvals = relationship("Approval", back_populates="action_request")
    executions = relationship("Execution", back_populates="action_request")
    guardrail_events = relationship("GuardrailEvent", back_populates="action_request")


class Approval(Base):
    """Approval decision record."""
    __tablename__ = "approvals"

    approval_id = Column(String, primary_key=True)
    request_id = Column(String, ForeignKey("action_requests.request_id"), nullable=False)
    status = Column(String, nullable=False)  # approved, rejected, expired
    approver = Column(String, nullable=False)  # user/email
    channel = Column(String, nullable=False)  # cli, slack, servicenow_mock
    comment = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    action_request = relationship("ActionRequest", back_populates="approvals")


class Execution(Base):
    """Execution record - what actually happened downstream."""
    __tablename__ = "executions"

    execution_id = Column(String, primary_key=True)
    request_id = Column(String, ForeignKey("action_requests.request_id"), nullable=False)
    downstream_system = Column(String, nullable=False)  # business_api
    downstream_status = Column(Integer, nullable=False)  # HTTP code
    downstream_response_hash = Column(String, nullable=True)
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    error = Column(Text, nullable=True)

    # Relationships
    action_request = relationship("ActionRequest", back_populates="executions")


class GuardrailEvent(Base):
    """Guardrail event record."""
    __tablename__ = "guardrail_events"

    event_id = Column(String, primary_key=True)
    request_id = Column(String, ForeignKey("action_requests.request_id"), nullable=False)
    guardrail = Column(String, nullable=False)  # e.g., max_rows_written, no_external_email_on_friday
    triggered = Column(Boolean, default=False, nullable=False)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    action_request = relationship("ActionRequest", back_populates="guardrail_events")


class ManagerControl(Base):
    """Manager controls (singleton-ish config)."""
    __tablename__ = "manager_controls"

    id = Column(Integer, primary_key=True)
    global_kill_switch = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

