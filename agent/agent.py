"""LangChain agent implementation."""
import os
import uuid
from typing import Optional
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from .tools import get_tools

# Load environment variables
load_dotenv()

# Agent configuration
AGENT_ID = "agent-support-001"


def create_agent(session_id: Optional[str] = None):
    """
    Create and return an agent.
    
    Args:
        session_id: Optional session ID for this run
    
    Returns:
        Agent (LangGraph graph)
    """
    # Get OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    # Initialize LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",  # Using mini for cost efficiency in MVP
        temperature=0,
        api_key=api_key
    )
    
    # Get tools
    tools = get_tools(session_id)
    
    # Create agent using LangGraph (LangChain 1.x approach)
    agent = create_react_agent(
        llm,
        tools,
        state_modifier="""You are a support ticket management agent. Your goal is to review open support tickets 
        and close any that meet resolution criteria, then notify customers.

        Guidelines:
        - Review tickets carefully before closing them
        - Only close tickets that are clearly resolved
        - Be cautious about ambiguous cases
        - Always notify customers when you close their tickets
        - Use the available tools to list tickets, update ticket status, and send emails
        
        When closing tickets, use the update_ticket tool to set status to "closed".
        Then use send_customer_email to notify the customer."""
    )
    
    return agent


def run_agent(goal: str, session_id: Optional[str] = None):
    """
    Run the agent with a given goal.
    
    Args:
        goal: The goal/task for the agent
        session_id: Optional session ID (generated if not provided)
    
    Returns:
        Agent execution result
    """
    if session_id is None:
        session_id = str(uuid.uuid4())
    
    # Set session_id in environment for tools to access
    os.environ["AGENT_SESSION_ID"] = session_id
    
    agent = create_agent(session_id)
    
    # LangGraph agents use invoke with messages format
    from langchain_core.messages import HumanMessage
    result = agent.invoke({"messages": [HumanMessage(content=goal)]})
    
    # Clean up
    os.environ.pop("AGENT_SESSION_ID", None)
    
    return result


if __name__ == "__main__":
    # Example usage
    goal = "Review open support tickets and close any that meet resolution criteria, then notify customers."
    result = run_agent(goal)
    print("\n" + "="*60)
    print("AGENT EXECUTION COMPLETE")
    print("="*60)
    print(result)

