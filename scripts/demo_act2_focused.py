"""
Focused demo script for debugging ACT II CLI approval process.

This script focuses only on ACT II - the approval flow, with extra debugging
to help identify why approvals aren't working correctly.

Usage:
    python scripts/demo_act2_focused.py [--reset]

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


def validate_act_2_success() -> tuple[bool, dict]:
    """Validate that Act 2 actually succeeded.
    
    Returns:
        tuple: (success: bool, checks: dict) - success is True if all checks pass
    """
    checks = {
        "agent_executed": False,
        "actions_in_audit": False,
        "at_least_one_action": False,
        "at_least_one_approval": False,
        "at_least_one_executed": False
    }
    
    try:
        with httpx.Client() as client:
            response = client.get(f"{NPC_MANAGER_URL}/audit/timeline?agent_id=agent-support-001&limit=50", timeout=10)
            if response.status_code == 200:
                data = response.json()
                timeline = data.get("timeline", [])
                checks["actions_in_audit"] = len(timeline) > 0
                checks["agent_executed"] = True  # If we got the timeline, agent made calls
                
                accepted = [e for e in timeline if e.get('decision') == 'allow']
                checks["at_least_one_action"] = len(accepted) > 0
                
                # Check for approvals
                has_approvals = False
                for entry in accepted:
                    if entry.get('approvals') and len(entry.get('approvals', [])) > 0:
                        has_approvals = True
                        break
                checks["at_least_one_approval"] = has_approvals
                
                # Check for executions
                has_executions = False
                for entry in accepted:
                    if entry.get('executions') and len(entry.get('executions', [])) > 0:
                        exec_statuses = [e.get('status') for e in entry.get('executions', [])]
                        # Check if any execution has a successful status (< 400)
                        if any(s and s < 400 for s in exec_statuses):
                            has_executions = True
                            break
                checks["at_least_one_executed"] = has_executions
    except Exception as e:
        print(f"[DEBUG] Error validating: {e}")
        import traceback
        traceback.print_exc()
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
    print("ACT 2: With NPC Manager - Approval Flow (DEBUG MODE)")
    print("=" * 60)
    print("\nAgent now calls NPC Manager instead of Ticketing API directly.")
    print("High-risk actions require approval.")
    print("\n⚠️  DEBUG MODE: This script focuses on debugging the approval process.")
    print("   Watch for approval prompts and check if they're working correctly.")
    
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
            print("\n[DEBUG] About to start agent - stdin/stdout/stderr should be available")
            print(f"[DEBUG] stdin.isatty(): {sys.stdin.isatty()}")
            print(f"[DEBUG] stdout.isatty(): {sys.stdout.isatty()}")
            print(f"[DEBUG] stderr.isatty(): {sys.stderr.isatty()}")
            input("\nPress Enter to start the agent...")
            
            # Run agent
            from agent.agent import run_agent
            goal = "Review open support tickets and close any that meet resolution criteria, then notify customers."
            print("\n[AGENT] Starting ticket review...")
            print("[DEBUG] Agent process started - monitoring for approval requests...")
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
            
            # Query audit timeline with detailed debugging
            print("\n" + "=" * 60)
            print("Action Request Summary (DETAILED)")
            print("=" * 60)
            with httpx.Client() as client:
                response = client.get(f"{NPC_MANAGER_URL}/audit/timeline?agent_id=agent-support-001&limit=50", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    timeline = data.get("timeline", [])
                    
                    accepted = [e for e in timeline if e.get('decision') == 'allow']
                    denied = [e for e in timeline if e.get('decision') == 'deny']
                    pending = [e for e in timeline if e.get('decision') == 'pending']
                    
                    print(f"\nTotal requests: {len(timeline)}")
                    print(f"✓ Accepted/Executed: {len(accepted)}")
                    print(f"✗ Denied: {len(denied)}")
                    print(f"⏳ Pending: {len(pending)}")
                    
                    if accepted:
                        print("\n" + "-" * 60)
                        print("ACCEPTED & EXECUTED REQUESTS:")
                        print("-" * 60)
                        for i, entry in enumerate(accepted[:10], 1):  # Show first 10
                            print(f"\n{i}. {entry.get('action_type', 'Unknown')} - {entry.get('resource', 'N/A')}")
                            print(f"   Request ID: {entry['request_id']}")
                            print(f"   Risk Level: {entry.get('risk_level', 'N/A')}")
                            print(f"   Approval Required: {entry.get('approval_required', 'N/A')}")
                            
                            # DEBUG: Show approval details
                            approvals = entry.get('approvals', [])
                            if approvals:
                                print(f"   Approvals ({len(approvals)}):")
                                for approval in approvals:
                                    print(f"     - Status: {approval.get('status', 'N/A')}")
                                    print(f"       Approver: {approval.get('approver', 'N/A')}")
                                    print(f"       Channel: {approval.get('channel', 'N/A')}")
                                    print(f"       Comment: {approval.get('comment', 'N/A')}")
                            else:
                                print(f"   ⚠️  No approvals found (but decision is 'allow')")
                            
                            # DEBUG: Show execution details
                            executions = entry.get('executions', [])
                            if executions:
                                print(f"   Executions ({len(executions)}):")
                                for exec_entry in executions:
                                    status = exec_entry.get('status', 'N/A')
                                    error = exec_entry.get('error', 'N/A')
                                    print(f"     - Status: {status}")
                                    if error and error != 'N/A':
                                        print(f"       Error: {error}")
                                    if status != 'N/A' and status < 400:
                                        print(f"       ✓ Executed successfully")
                                    elif status != 'N/A':
                                        print(f"       ⚠ Execution returned HTTP {status}")
                            else:
                                print(f"   ⚠️  No executions found (but decision is 'allow')")
                            
                            if entry.get('decision_reason'):
                                print(f"   Decision Reason: {entry.get('decision_reason')}")
                    else:
                        print("\n⚠️  No accepted requests found!")
                    
                    if denied:
                        print("\n" + "-" * 60)
                        print("DENIED REQUESTS:")
                        print("-" * 60)
                        for i, entry in enumerate(denied[:5], 1):
                            print(f"\n{i}. {entry.get('action_type', 'Unknown')} - {entry.get('resource', 'N/A')}")
                            print(f"   Request ID: {entry['request_id']}")
                            print(f"   Risk Level: {entry.get('risk_level', 'N/A')}")
                            print(f"   ✗ Denied: {entry.get('decision_reason', 'No reason provided')}")
                            approvals = entry.get('approvals', [])
                            if approvals:
                                for approval in approvals:
                                    if approval.get('status') == 'denied' or approval.get('status') == 'rejected':
                                        print(f"   ✗ Denied by {approval.get('approver', 'Unknown')} via {approval.get('channel', 'Unknown')}")
                else:
                    print(f"\n⚠ Could not fetch audit timeline: {response.status_code}")
            
            # Validate success with detailed reporting
            print("\n" + "=" * 60)
            print("[ACT 2] Validating results...")
            print("=" * 60)
            success, checks = validate_act_2_success()
            if success:
                print("[ACT 2] ✓ Validation passed - all checks successful")
            else:
                print("[ACT 2] ✗ Validation failed - some checks did not pass:")
                for check, passed in checks.items():
                    status = "✓" if passed else "✗"
                    print(f"  {status} {check}")
                print("\n[DEBUG] This indicates that:")
                if not checks["actions_in_audit"]:
                    print("  - No actions were recorded in audit log")
                if not checks["at_least_one_action"]:
                    print("  - No actions were approved/allowed")
                if not checks["at_least_one_approval"]:
                    print("  - Actions were approved but no approval records exist (BUG!)")
                if not checks["at_least_one_executed"]:
                    print("  - Actions were approved but not executed (BUG!)")
            
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
    """Main demo execution - focused on ACT II approval debugging."""
    parser = argparse.ArgumentParser(description="NPC Manager 1 MVP Demo - ACT II Focus (Approval Debug)")
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
    print("NPC Manager 1 MVP Demo - ACT II FOCUS")
    print("=" * 60)
    print("\nThis focused demo script runs only ACT II to debug the approval process.")
    print("It includes extra debugging output to help identify approval issues.")
    
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
    
    input("\nPress Enter to start the focused demo...")
    
    # Track act results
    act_results = {}
    
    try:
        print("\n" + "=" * 60)
        print("Starting Focused Demo (ACT II Only)")
        print("=" * 60)
        
        act_results[2] = act_2_with_manager()
        
        # Print summary
        print("\n" + "=" * 60)
        print("Demo Summary")
        print("=" * 60)
        
        status = "✓ Passed" if act_results[2] else "✗ Failed"
        print(f"Act 2 (Approval Flow): {status}")
        
        if act_results[2]:
            print("\n" + "=" * 60)
            print("Focused Demo Complete!")
            print("=" * 60)
            print("\nThe approval flow appears to be working correctly.")
        else:
            print("\n" + "=" * 60)
            print("Focused Demo Completed with Issues")
            print("=" * 60)
            print("\n⚠ The approval process has issues. Review the detailed output above.")
            print("Check for:")
            print("  - Approval prompts appearing correctly")
            print("  - Approval records being created in the database")
            print("  - Actions being executed after approval")
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

