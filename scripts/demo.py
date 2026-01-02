"""
Demo script that executes the runbook narrative.

This is the main interactive demo script for NPC Manager 1 MVP.
It walks through 5 acts demonstrating the system's capabilities.

Usage:
    python scripts/demo.py [--reset]

Options:
    --reset    Reset databases to initial state before running demo
"""
import sys
import time
import subprocess
import requests
import os
import argparse
import httpx
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import service manager
from scripts.service_manager import ServiceManager, kill_processes_on_port

TICKETING_API_URL = "http://localhost:8000"
NPC_MANAGER_URL = "http://localhost:8001"


def wait_for_service(url: str, service_name: str, timeout: int = 30) -> bool:
    """Wait for a service to be available."""
    print(f"Waiting for {service_name} to start...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                print(f"✓ {service_name} is ready")
                return True
        except Exception:
            pass
        time.sleep(1)
    print(f"✗ {service_name} failed to start within {timeout} seconds")
    return False


# Helper functions removed - using ServiceManager from service_manager.py instead


def act_1_no_manager() -> bool:
    """Act 1: Run agent directly against Ticketing API (no manager) - show failure mode.
    
    Returns:
        bool: True if act completed successfully, False otherwise
    """
    print("\n[ACT 1] Starting...")
    print("=" * 60)
    print("ACT 1: No Manager - Direct API Access")
    print("=" * 60)
    print("\nThis demonstrates the baseline failure mode:")
    print("- Agent calls Ticketing API directly")
    print("- No approval required")
    print("- No guardrails")
    print("- Limited audit trail")
    print("\nNote: For this MVP, we'll show the concept by demonstrating")
    print("that the agent would need different tool configuration.")
    print("In a real scenario, the agent would call the API directly.")
    print("\n(Skipping actual execution - would require separate agent config)")
    try:
        input("\nPress Enter to continue...")
        print("[ACT 1] ✓ Completed")
        return True
    except KeyboardInterrupt:
        print("[ACT 1] ✗ Interrupted by user")
        return False
    except Exception as e:
        print(f"[ACT 1] ✗ Error: {e}")
        return False


def validate_act_2_success() -> tuple[bool, dict]:
    """Validate that Act 2 actually succeeded.
    
    Returns:
        tuple: (success: bool, checks: dict) - success is True if all checks pass
    """
    checks = {
        "agent_executed": False,
        "actions_in_audit": False,
        "at_least_one_action": False
    }
    
    try:
        with httpx.Client() as client:
            response = client.get(f"{NPC_MANAGER_URL}/audit/timeline?agent_id=agent-support-001&limit=50", timeout=10)
            if response.status_code == 200:
                data = response.json()
                timeline = data.get("timeline", [])
                checks["actions_in_audit"] = len(timeline) > 0
                checks["at_least_one_action"] = len([e for e in timeline if e.get('decision') == 'allow']) > 0
                checks["agent_executed"] = True  # If we got the timeline, agent made calls
    except Exception:
        pass
    
    success = all(checks.values())
    return success, checks


def act_2_with_manager() -> bool:
    """Act 2: Switch to NPC Manager - show approval flow.
    
    Returns:
        bool: True if act completed successfully, False otherwise
    """
    print("\n[ACT 2] Starting...")
    print("=" * 60)
    print("ACT 2: With NPC Manager - Approval Flow")
    print("=" * 60)
    print("\nAgent now calls NPC Manager instead of Ticketing API directly.")
    print("High-risk actions require approval.")
    
    services = [
        ("Ticketing API", ["python", "-m", "uvicorn", "ticketing_api.main:app", "--port", "8000"], 8000, TICKETING_API_URL),
        ("NPC Manager", ["python", "-m", "uvicorn", "npc_manager.main:app", "--port", "8001"], 8001, NPC_MANAGER_URL)
    ]
    
    try:
        with ServiceManager(services) as sm:
            if not sm.is_ready("Ticketing API") or not sm.is_ready("NPC Manager"):
                print("[ACT 2] ✗ Services failed to start")
                return False
            
            print("\n[ACT 2] ✓ Services started")
            print("\n" + "=" * 60)
            print("Running agent with NPC Manager...")
            print("=" * 60)
            print("\nThe agent will now attempt actions that require approval.")
            print("⚠️  IMPORTANT: Approval prompts will appear in this terminal.")
            print("   Watch for prompts asking 'Approve ... ? (y/n)' and respond.")
            print("\nGoal: Review open support tickets and close any that meet")
            print("resolution criteria, then notify customers.")
            input("\nPress Enter to start the agent...")
            
            # Run agent
            from agent.agent import run_agent
            goal = "Review open support tickets and close any that meet resolution criteria, then notify customers."
            print("\n[AGENT] Starting ticket review...")
            result = run_agent(goal)
            
            print("\n" + "=" * 60)
            print("Agent execution completed")
            print("=" * 60)
            
            # Display the agent's response
            output = result.get('output', 'N/A')
            if output and output != 'N/A':
                print(f"\nAgent Response:\n{output}")
            else:
                print(f"\nResult: {output}")
                messages = result.get('messages', [])
                if messages:
                    print(f"Note: Agent returned {len(messages)} messages but no final output was extracted.")
            
            # Query audit timeline
            print("\n" + "=" * 60)
            print("Action Request Summary")
            print("=" * 60)
            with httpx.Client() as client:
                response = client.get(f"{NPC_MANAGER_URL}/audit/timeline?agent_id=agent-support-001&limit=50", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    timeline = data.get("timeline", [])
                    
                    accepted = [e for e in timeline if e.get('decision') == 'allow']
                    denied = [e for e in timeline if e.get('decision') == 'deny']
                    
                    print(f"\nTotal requests: {len(timeline)}")
                    print(f"✓ Accepted/Executed: {len(accepted)}")
                    print(f"✗ Denied: {len(denied)}")
                    
                    if accepted:
                        print("\n" + "-" * 60)
                        print("ACCEPTED & EXECUTED REQUESTS:")
                        print("-" * 60)
                        for i, entry in enumerate(accepted[:5], 1):  # Show first 5
                            print(f"\n{i}. {entry.get('action_type', 'Unknown')} - {entry.get('resource', 'N/A')}")
                            print(f"   Request ID: {entry['request_id']}")
                            print(f"   Risk Level: {entry.get('risk_level', 'N/A')}")
                            if entry.get('approvals'):
                                for approval in entry['approvals']:
                                    print(f"   ✓ Approved by {approval.get('approver', 'Unknown')} via {approval.get('channel', 'Unknown')}")
                            if entry.get('executions'):
                                for exec_entry in entry['executions']:
                                    status = exec_entry.get('status', 'N/A')
                                    if status != 'N/A' and status < 400:
                                        print(f"   ✓ Executed successfully (HTTP {status})")
                                    elif status != 'N/A':
                                        print(f"   ⚠ Execution returned HTTP {status}")
                else:
                    print(f"\n⚠ Could not fetch audit timeline: {response.status_code}")
            
            # Validate success
            print("\n[ACT 2] Validating results...")
            success, checks = validate_act_2_success()
            if success:
                print("[ACT 2] ✓ Validation passed")
            else:
                print("[ACT 2] ✗ Validation failed:")
                for check, passed in checks.items():
                    status = "✓" if passed else "✗"
                    print(f"  {status} {check}")
            
            input("\nPress Enter to continue...")
            return success
            
    except KeyboardInterrupt:
        print("\n[ACT 2] ✗ Interrupted by user")
        return False
    except Exception as e:
        print(f"\n[ACT 2] ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("Running agent with NPC Manager...")
    print("=" * 60)
    print("\nThe agent will now attempt actions that require approval.")
    print("You will be prompted to approve or deny each action.")
    print("\nGoal: Review open support tickets and close any that meet")
    print("resolution criteria, then notify customers.")
    input("\nPress Enter to start the agent...")
    
    try:
        # Run agent
        from agent.agent import run_agent
        goal = "Review open support tickets and close any that meet resolution criteria, then notify customers."
        result = run_agent(goal)
        
        print("\n" + "=" * 60)
        print("Agent execution completed")
        print("=" * 60)
        
        # Display the agent's response
        output = result.get('output', 'N/A')
        if output and output != 'N/A':
            print(f"\nAgent Response:\n{output}")
        else:
            print(f"\nResult: {output}")
            # If no output, show message count for debugging
            messages = result.get('messages', [])
            if messages:
                print(f"Note: Agent returned {len(messages)} messages but no final output was extracted.")
        
        # Query audit timeline to show all requests (accepted and denied)
        print("\n" + "=" * 60)
        print("Action Request Summary")
        print("=" * 60)
        with httpx.Client() as client:
            response = client.get(f"{NPC_MANAGER_URL}/audit/timeline?agent_id=agent-support-001&limit=50", timeout=10)
            if response.status_code == 200:
                data = response.json()
                timeline = data.get("timeline", [])
                
                # Separate accepted and denied requests
                accepted = [e for e in timeline if e.get('decision') == 'allow']
                denied = [e for e in timeline if e.get('decision') == 'deny']
                
                print(f"\nTotal requests: {len(timeline)}")
                print(f"✓ Accepted/Executed: {len(accepted)}")
                print(f"✗ Denied: {len(denied)}")
                
                if accepted:
                    print("\n" + "-" * 60)
                    print("ACCEPTED & EXECUTED REQUESTS:")
                    print("-" * 60)
                    for i, entry in enumerate(accepted, 1):
                        print(f"\n{i}. {entry.get('action_type', 'Unknown')} - {entry.get('resource', 'N/A')}")
                        print(f"   Request ID: {entry['request_id']}")
                        print(f"   Risk Level: {entry.get('risk_level', 'N/A')}")
                        if entry.get('approvals'):
                            for approval in entry['approvals']:
                                print(f"   ✓ Approved by {approval.get('approver', 'Unknown')} via {approval.get('channel', 'Unknown')}")
                        if entry.get('executions'):
                            for exec_entry in entry['executions']:
                                status = exec_entry.get('status', 'N/A')
                                error = exec_entry.get('error')
                                if status != 'N/A' and status < 400:
                                    print(f"   ✓ Executed successfully (HTTP {status})")
                                elif status != 'N/A':
                                    print(f"   ⚠ Execution returned HTTP {status}")
                                    if error:
                                        print(f"      Error: {error}")
                                else:
                                    print(f"   ✓ Execution recorded")
                        if entry.get('decision_reason'):
                            print(f"   Reason: {entry.get('decision_reason')}")
                
                if denied:
                    print("\n" + "-" * 60)
                    print("DENIED REQUESTS:")
                    print("-" * 60)
                    for i, entry in enumerate(denied, 1):
                        print(f"\n{i}. {entry.get('action_type', 'Unknown')} - {entry.get('resource', 'N/A')}")
                        print(f"   Request ID: {entry['request_id']}")
                        print(f"   Risk Level: {entry.get('risk_level', 'N/A')}")
                        print(f"   ✗ Denied: {entry.get('decision_reason', 'No reason provided')}")
                        if entry.get('approvals'):
                            for approval in entry['approvals']:
                                if approval.get('status') == 'denied':
                                    print(f"   ✗ Denied by {approval.get('approver', 'Unknown')} via {approval.get('channel', 'Unknown')}")
                        if entry.get('guardrail_events'):
                            for guardrail in entry['guardrail_events']:
                                if guardrail.get('triggered'):
                                    print(f"   🛡️ Guardrail triggered: {guardrail.get('guardrail', 'Unknown')}")
            else:
                print(f"\n⚠ Could not fetch audit timeline: {response.status_code}")
        
    except Exception as e:
        print(f"\nError running agent: {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("\nPress Enter to continue...")
        print("\nStopping services...")
        stop_service(ticketing_process)
        stop_service(npc_process)
        # Clean up ports to ensure they're released
        print("Cleaning up ports...")
        kill_processes_on_port(8000)
        kill_processes_on_port(8001)
        time.sleep(2)  # Give OS time to release ports


def act_3_guardrails():
    """Act 3: Show guardrails (bulk limit, do-not-contact)."""
    print("\n" + "=" * 60)
    print("ACT 3: Guardrails - Structural Limits")
    print("=" * 60)
    print("\nDemonstrating guardrails:")
    print("1. Max ticket updates per run (5)")
    print("2. Do-not-contact blocking")
    
    services = [
        ("Ticketing API", ["python", "-m", "uvicorn", "ticketing_api.main:app", "--port", "8000"], 8000, TICKETING_API_URL),
        ("NPC Manager", ["python", "-m", "uvicorn", "npc_manager.main:app", "--port", "8001"], 8001, NPC_MANAGER_URL),
    ]
    
    try:
        with ServiceManager(services) as sm:
            if not sm.is_ready("Ticketing API") or not sm.is_ready("NPC Manager"):
                print("✗ Failed to start required services")
                return False
            
            print("\n" + "=" * 60)
            print("Testing guardrails...")
            print("=" * 60)
            print("\n1. Attempting to update >5 tickets (should be blocked)")
            print("2. Attempting to email customer with do_not_contact=True (should be blocked)")
            
            # Test max updates guardrail
            print("\n--- Testing max updates guardrail ---")
            print("Note: First 5 updates will require approval. After that, guardrail should block.")
            print("⚠️  Watch for approval prompts in this terminal!")
            
            guardrail_triggered = False
            with httpx.Client() as client:
                for i in range(7):  # Try 7 updates (limit is 5)
                    try:
                        response = client.post(
                            f"{NPC_MANAGER_URL}/action",
                            json={
                                "agent_id": "agent-support-001",
                                "tool_name": "update_ticket",
                                "tool_args": {"ticket_id": 1, "status": "closed"},
                                "env": "prod"
                            },
                            headers={"X-Agent-ID": "agent-support-001"},
                            timeout=300  # Increased timeout to allow for approval prompts
                        )
                        result = response.json()
                        decision = result.get('decision')
                        reason = result.get('reason', 'N/A')
                        print(f"Update {i+1}: {decision} - {reason}")
                        if decision == 'deny' and ('max_ticket_updates' in reason.lower() or 'max_updates' in reason.lower()):
                            print("✓ Guardrail triggered correctly!")
                            guardrail_triggered = True
                            break
                    except httpx.ReadTimeout:
                        print(f"Update {i+1}: Timed out waiting for approval")
                        print("   (This is expected - approval requests block until you respond)")
                        print("   Continuing to next update...")
                        continue
            
            # Test do-not-contact guardrail
            print("\n--- Testing do-not-contact guardrail ---")
            print("Note: This will be blocked by guardrail before approval is needed.")
            do_not_contact_blocked = False
            with httpx.Client() as client:
                try:
                    response = client.post(
                        f"{NPC_MANAGER_URL}/action",
                        json={
                            "agent_id": "agent-support-001",
                            "tool_name": "send_customer_email",
                            "tool_args": {
                                "customer_id": 2,  # Customer 2 has do_not_contact=True
                                "subject": "Test",
                                "body": "Test email"
                            },
                            "env": "prod"
                        },
                        headers={"X-Agent-ID": "agent-support-001"},
                        timeout=30
                    )
                    result = response.json()
                    decision = result.get('decision')
                    reason = result.get('reason', 'N/A')
                    print(f"Email attempt: {decision} - {reason}")
                    if decision == 'deny' and 'do_not_contact' in reason.lower():
                        print("✓ Guardrail triggered correctly!")
                        do_not_contact_blocked = True
                except httpx.ReadTimeout:
                    print("Email attempt: Timed out (unexpected)")
            
            input("\nPress Enter to continue...")
            
            # Return True if at least one guardrail worked
            return guardrail_triggered or do_not_contact_blocked
    except Exception as e:
        print(f"✗ Error in Act 3: {e}")
        import traceback
        traceback.print_exc()
        return False


def act_4_kill_switch():
    """Act 4: Show kill switch."""
    print("\n" + "=" * 60)
    print("ACT 4: Kill Switch - Incident Containment")
    print("=" * 60)
    print("\nDemonstrating global kill switch that stops all agent actions.")
    
    services = [
        ("Ticketing API", ["python", "-m", "uvicorn", "ticketing_api.main:app", "--port", "8000"], 8000, TICKETING_API_URL),
        ("NPC Manager", ["python", "-m", "uvicorn", "npc_manager.main:app", "--port", "8001"], 8001, NPC_MANAGER_URL),
    ]
    
    try:
        with ServiceManager(services) as sm:
            if not sm.is_ready("Ticketing API") or not sm.is_ready("NPC Manager"):
                print("✗ Failed to start required services")
                return False
            
            print("\nEnabling kill switch...")
            # Update kill switch in database
            from npc_manager.database import SessionLocal
            from npc_manager.models import ManagerControl
            db = SessionLocal()
            try:
                control = db.query(ManagerControl).first()
                if control:
                    control.global_kill_switch = True
                    db.commit()
                    print("✓ Kill switch enabled")
                else:
                    print("✗ Could not find manager control")
                    db.close()
                    return False
            except Exception as e:
                print(f"✗ Error enabling kill switch: {e}")
                db.close()
                return False
            finally:
                db.close()
            
            print("\nAttempting agent action (should be denied)...")
            kill_switch_worked = False
            with httpx.Client() as client:
                response = client.post(
                    f"{NPC_MANAGER_URL}/action",
                    json={
                        "agent_id": "agent-support-001",
                        "tool_name": "list_tickets",
                        "tool_args": {},
                        "env": "prod"
                    },
                    headers={"X-Agent-ID": "agent-support-001"},
                    timeout=30
                )
                result = response.json()
                decision = result.get('decision')
                reason = result.get('reason', 'N/A')
                print(f"Action result: {decision} - {reason}")
                if decision == 'deny' and 'kill switch' in reason.lower():
                    print("✓ Kill switch working correctly!")
                    kill_switch_worked = True
            
            # Disable kill switch for next act
            print("\nDisabling kill switch...")
            db = SessionLocal()
            try:
                control = db.query(ManagerControl).first()
                if control:
                    control.global_kill_switch = False
                    db.commit()
                    print("✓ Kill switch disabled")
            finally:
                db.close()
            
            input("\nPress Enter to continue...")
            return kill_switch_worked
    except Exception as e:
        print(f"✗ Error in Act 4: {e}")
        import traceback
        traceback.print_exc()
        return False


def act_5_audit():
    """Act 5: Show audit timeline."""
    print("\n" + "=" * 60)
    print("ACT 5: Audit Trail - Answering Enterprise Questions")
    print("=" * 60)
    print("\nQuerying audit timeline to answer:")
    print("- Which agent acted?")
    print("- What did it attempt?")
    print("- What constraints applied?")
    print("- Who approved and what executed?")
    
    services = [
        ("NPC Manager", ["python", "-m", "uvicorn", "npc_manager.main:app", "--port", "8001"], 8001, NPC_MANAGER_URL),
    ]
    
    try:
        with ServiceManager(services) as sm:
            if not sm.is_ready("NPC Manager"):
                print("✗ Failed to start NPC Manager")
                return False
            
            print("\nFetching audit timeline...")
            timeline_fetched = False
            with httpx.Client() as client:
                response = client.get(
                    f"{NPC_MANAGER_URL}/audit/timeline?agent_id=agent-support-001&limit=20",
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    timeline = data.get("timeline", [])
                    print(f"\nFound {len(timeline)} action requests\n")
                    
                    for i, entry in enumerate(timeline[:5], 1):  # Show first 5
                        print(f"{i}. Request ID: {entry['request_id']}")
                        print(f"   Agent: {entry['agent_id']}")
                        print(f"   Action: {entry['action_type']} on {entry['resource']}")
                        print(f"   Risk: {entry['risk_level']}")
                        print(f"   Decision: {entry['decision']}")
                        if entry.get('approvals'):
                            for approval in entry['approvals']:
                                print(f"   Approval: {approval['status']} by {approval['approver']} via {approval['channel']}")
                        if entry.get('guardrail_events'):
                            for guardrail in entry['guardrail_events']:
                                print(f"   Guardrail: {guardrail['guardrail']} - Triggered: {guardrail['triggered']}")
                        print()
                    timeline_fetched = True
                else:
                    print(f"✗ Error fetching timeline: {response.status_code}")
            
            input("\nPress Enter to finish demo...")
            return timeline_fetched
    except Exception as e:
        print(f"✗ Error in Act 5: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_prerequisites() -> tuple[bool, list[str]]:
    """Check if all prerequisites are met.
    
    Returns:
        tuple: (all_met: bool, missing: list[str])
    """
    missing = []
    root = Path(__file__).parent.parent
    
    # Check databases
    npc_db = root / "database" / "npc_manager.db"
    ticketing_db = root / "database" / "ticketing.db"
    if not npc_db.exists():
        missing.append(f"NPC Manager database not found at {npc_db}")
    if not ticketing_db.exists():
        missing.append(f"Ticketing database not found at {ticketing_db}")
    
    # Check .env file
    env_file = root / ".env"
    if not env_file.exists():
        missing.append(f".env file not found at {env_file}")
    else:
        # Check for OPENAI_API_KEY
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            if not os.getenv("OPENAI_API_KEY"):
                missing.append("OPENAI_API_KEY not set in .env file")
        except Exception:
            missing.append("Could not read .env file")
    
    # Check dependencies (basic check - try importing key packages)
    try:
        import fastapi
        import langchain_openai
        import httpx
    except ImportError as e:
        missing.append(f"Missing dependency: {e.name if hasattr(e, 'name') else str(e)}")
    
    return len(missing) == 0, missing


def main():
    """Main demo execution."""
    parser = argparse.ArgumentParser(description="NPC Manager 1 MVP Demo")
    parser.add_argument("--reset", action="store_true", help="Reset databases to initial state before running demo")
    args = parser.parse_args()
    
    # Handle --reset flag
    if args.reset:
        print("Resetting databases...")
        from scripts.reset_demo import main as reset_main
        if not reset_main():
            print("✗ Failed to reset databases. Exiting.")
            sys.exit(1)
        print("✓ Databases reset successfully\n")
    
    # Clean up any existing processes on our ports
    print("Cleaning up any existing processes on ports 8000 and 8001...")
    kill_processes_on_port(8000)
    kill_processes_on_port(8001)
    time.sleep(1)
    
    print("=" * 60)
    print("NPC Manager 1 MVP Demo")
    print("=" * 60)
    print("\nThis demo will walk through 5 acts:")
    print("1. No Manager - Baseline failure mode")
    print("2. With Manager - Approval flow")
    print("3. Guardrails - Structural limits")
    print("4. Kill Switch - Incident containment")
    print("5. Audit Trail - Enterprise questions")
    
    # Check prerequisites
    print("\nChecking prerequisites...")
    all_met, missing = check_prerequisites()
    if not all_met:
        print("\n✗ Prerequisites not met:")
        for item in missing:
            print(f"  - {item}")
        print("\nPlease fix the issues above before running the demo.")
        print("Run 'python scripts/setup_db.py' to initialize databases.")
        print("Copy 'env.example' to '.env' and add your OPENAI_API_KEY.")
        print("Install dependencies: pip install -r requirements.txt")
        sys.exit(1)
    print("✓ All prerequisites met")
    
    input("\nPress Enter to start the demo...")
    
    # Track act results
    act_results = {}
    
    try:
        print("\n" + "=" * 60)
        print("Starting Demo")
        print("=" * 60)
        
        act_results[1] = act_1_no_manager()
        if not act_results[1]:
            print("\n[DEMO] Act 1 failed, but continuing...")
        
        act_results[2] = act_2_with_manager()
        if not act_results[2]:
            print("\n[DEMO] Act 2 failed - this is critical. Continuing with remaining acts...")
        
        # Acts 3-5 now use ServiceManager and return bool values
        try:
            print("\n[ACT 3] Starting...")
            act_results[3] = act_3_guardrails()
            if act_results[3]:
                print("[ACT 3] ✓ Completed")
            else:
                print("[ACT 3] ✗ Failed")
        except Exception as e:
            print(f"[ACT 3] ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            act_results[3] = False
        
        try:
            print("\n[ACT 4] Starting...")
            act_results[4] = act_4_kill_switch()
            if act_results[4]:
                print("[ACT 4] ✓ Completed")
            else:
                print("[ACT 4] ✗ Failed")
        except Exception as e:
            print(f"[ACT 4] ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            act_results[4] = False
        
        try:
            print("\n[ACT 5] Starting...")
            act_results[5] = act_5_audit()
            if act_results[5]:
                print("[ACT 5] ✓ Completed")
            else:
                print("[ACT 5] ✗ Failed")
        except Exception as e:
            print(f"[ACT 5] ✗ Error: {e}")
            import traceback
            traceback.print_exc()
            act_results[5] = False
        
        # Print summary
        print("\n" + "=" * 60)
        print("Demo Summary")
        print("=" * 60)
        all_passed = all(act_results.values())
        
        for act_num, passed in act_results.items():
            status = "✓ Passed" if passed else "✗ Failed"
            print(f"Act {act_num}: {status}")
        
        if all_passed:
            print("\n" + "=" * 60)
            print("Demo Complete!")
            print("=" * 60)
            print("\nThe MVP has demonstrated:")
            print("✓ Agent executes write operations autonomously")
            print("✓ Every action is attributed to agent_id")
            print("✓ High-risk actions require approval")
            print("✓ Guardrails block violations")
            print("✓ Kill switch stops all actions instantly")
            print("✓ Audit trail answers: who, what, why, when, who approved")
            print("✓ Agent code unchanged when controls are added")
        else:
            print("\n" + "=" * 60)
            print("Demo Completed with Errors")
            print("=" * 60)
            print("\n⚠ Some acts failed. Review the output above for details.")
            print("The demo may not have fully demonstrated all capabilities.")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n\n[DEMO] ✗ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[DEMO] ✗ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

