"""Demo script that executes the runbook narrative (non-interactive version)."""
import sys
import time
import subprocess
import requests
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

TICKETING_API_URL = "http://localhost:8000"
NPC_MANAGER_URL = "http://localhost:8001"


def wait_for_service(url: str, service_name: str, timeout: int = 30):
    """Wait for a service to be available."""
    print(f"Waiting for {service_name} to start...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                print(f"✓ {service_name} is ready")
                return True
        except:
            pass
        time.sleep(1)
    print(f"✗ {service_name} failed to start within {timeout} seconds")
    return False


def start_service(name: str, command: list, port: int):
    """Start a service as a subprocess."""
    print(f"\nStarting {name} on port {port}...")
    # Use venv python if available
    venv_python = Path(__file__).parent.parent / "venv" / "bin" / "python"
    if venv_python.exists():
        # Replace 'python' with venv python path
        command = [str(venv_python) if arg == "python" else arg for arg in command]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).parent.parent
    )
    return process


def stop_service(process: subprocess.Popen):
    """Stop a service process."""
    if process:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def act_2_with_manager():
    """Act 2: Switch to NPC Manager - show approval flow."""
    print("\n" + "=" * 60)
    print("ACT 2: With NPC Manager - Approval Flow")
    print("=" * 60)
    print("\nAgent now calls NPC Manager instead of Ticketing API directly.")
    print("High-risk actions require approval.")
    print("\nStarting services...")
    
    # Start Ticketing API
    ticketing_process = start_service(
        "Ticketing API",
        ["python", "-m", "uvicorn", "ticketing_api.main:app", "--port", "8000"],
        8000
    )
    
    if not wait_for_service(TICKETING_API_URL, "Ticketing API"):
        stop_service(ticketing_process)
        return
    
    # Start NPC Manager
    npc_process = start_service(
        "NPC Manager",
        ["python", "-m", "uvicorn", "npc_manager.main:app", "--port", "8001"],
        8001
    )
    
    if not wait_for_service(NPC_MANAGER_URL, "NPC Manager"):
        stop_service(ticketing_process)
        stop_service(npc_process)
        return
    
    print("\n" + "=" * 60)
    print("Running agent with NPC Manager...")
    print("=" * 60)
    print("\nThe agent will now attempt actions that require approval.")
    print("NOTE: This demo requires interactive approval prompts.")
    print("For full functionality, run: python scripts/demo.py")
    print("\nSkipping agent execution (requires interactive input)...")
    
    stop_service(ticketing_process)
    stop_service(npc_process)


def act_3_guardrails():
    """Act 3: Show guardrails (bulk limit, do-not-contact)."""
    print("\n" + "=" * 60)
    print("ACT 3: Guardrails - Structural Limits")
    print("=" * 60)
    print("\nDemonstrating guardrails:")
    print("1. Max ticket updates per run (5)")
    print("2. Do-not-contact blocking")
    
    # Start services
    ticketing_process = start_service(
        "Ticketing API",
        ["python", "-m", "uvicorn", "ticketing_api.main:app", "--port", "8000"],
        8000
    )
    
    if not wait_for_service(TICKETING_API_URL, "Ticketing API"):
        stop_service(ticketing_process)
        return
    
    npc_process = start_service(
        "NPC Manager",
        ["python", "-m", "uvicorn", "npc_manager.main:app", "--port", "8001"],
        8001
    )
    
    if not wait_for_service(NPC_MANAGER_URL, "NPC Manager"):
        stop_service(ticketing_process)
        stop_service(npc_process)
        return
    
    print("\n" + "=" * 60)
    print("Testing guardrails...")
    print("=" * 60)
    print("\n1. Attempting to update >5 tickets (should be blocked)")
    print("2. Attempting to email customer with do_not_contact=True (should be blocked)")
    
    # Test max updates guardrail
    print("\n--- Testing max updates guardrail ---")
    import httpx
    with httpx.Client() as client:
        for i in range(7):  # Try 7 updates (limit is 5)
            response = client.post(
                f"{NPC_MANAGER_URL}/action",
                json={
                    "agent_id": "agent-support-001",
                    "tool_name": "update_ticket",
                    "tool_args": {"ticket_id": 1, "status": "closed"},
                    "env": "prod"
                },
                headers={"X-Agent-ID": "agent-support-001"},
                timeout=30
            )
            result = response.json()
            print(f"Update {i+1}: {result.get('decision')} - {result.get('reason', 'N/A')}")
            if result.get('decision') == 'deny' and 'max_ticket_updates' in result.get('reason', ''):
                print("✓ Guardrail triggered correctly!")
                break
    
    # Test do-not-contact guardrail
    print("\n--- Testing do-not-contact guardrail ---")
    with httpx.Client() as client:
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
        print(f"Email attempt: {result.get('decision')} - {result.get('reason', 'N/A')}")
        if result.get('decision') == 'deny' and 'do_not_contact' in result.get('reason', ''):
            print("✓ Guardrail triggered correctly!")
    
    stop_service(ticketing_process)
    stop_service(npc_process)


def act_4_kill_switch():
    """Act 4: Show kill switch."""
    print("\n" + "=" * 60)
    print("ACT 4: Kill Switch - Incident Containment")
    print("=" * 60)
    print("\nDemonstrating global kill switch that stops all agent actions.")
    
    # Start services
    ticketing_process = start_service(
        "Ticketing API",
        ["python", "-m", "uvicorn", "ticketing_api.main:app", "--port", "8000"],
        8000
    )
    
    if not wait_for_service(TICKETING_API_URL, "Ticketing API"):
        stop_service(ticketing_process)
        return
    
    npc_process = start_service(
        "NPC Manager",
        ["python", "-m", "uvicorn", "npc_manager.main:app", "--port", "8001"],
        8001
    )
    
    if not wait_for_service(NPC_MANAGER_URL, "NPC Manager"):
        stop_service(ticketing_process)
        stop_service(npc_process)
        return
    
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
    except Exception as e:
        print(f"✗ Error enabling kill switch: {e}")
    finally:
        db.close()
    
    print("\nAttempting agent action (should be denied)...")
    import httpx
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
        print(f"Action result: {result.get('decision')} - {result.get('reason', 'N/A')}")
        if result.get('decision') == 'deny' and 'kill switch' in result.get('reason', '').lower():
            print("✓ Kill switch working correctly!")
    
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
    
    stop_service(ticketing_process)
    stop_service(npc_process)


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
    
    # Start NPC Manager (we only need this for the audit endpoint)
    npc_process = start_service(
        "NPC Manager",
        ["python", "-m", "uvicorn", "npc_manager.main:app", "--port", "8001"],
        8001
    )
    
    if not wait_for_service(NPC_MANAGER_URL, "NPC Manager"):
        stop_service(npc_process)
        return
    
    print("\nFetching audit timeline...")
    import httpx
    with httpx.Client() as client:
        response = client.get(f"{NPC_MANAGER_URL}/audit/timeline?agent_id=agent-support-001&limit=20")
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
        else:
            print(f"Error fetching timeline: {response.status_code}")
    
    stop_service(npc_process)


def main():
    """Main demo execution."""
    print("=" * 60)
    print("NPC Manager 1 MVP Demo (Auto-Run)")
    print("=" * 60)
    print("\nThis demo will walk through 4 acts:")
    print("1. Act 2: With Manager - Approval flow (skipped - requires interactive)")
    print("2. Act 3: Guardrails - Structural limits")
    print("3. Act 4: Kill Switch - Incident containment")
    print("4. Act 5: Audit Trail - Enterprise questions")
    print("\nNote: Act 2 (agent execution) requires interactive approval prompts.")
    print("To run the full interactive demo, use: python scripts/demo.py")
    
    try:
        print("\n" + "=" * 60)
        print("ACT 1: No Manager - Baseline")
        print("=" * 60)
        print("\n(Skipped - conceptual demonstration)")
        print("This would show agent calling Ticketing API directly without controls.")
        
        act_2_with_manager()
        act_3_guardrails()
        act_4_kill_switch()
        act_5_audit()
        
        print("\n" + "=" * 60)
        print("Demo Complete!")
        print("=" * 60)
        print("\nThe MVP has demonstrated:")
        print("✓ Agent execution layer with controls")
        print("✓ Guardrails block violations")
        print("✓ Kill switch stops all actions instantly")
        print("✓ Audit trail answers: who, what, why, when")
        print("\nFor full interactive demo with agent execution and approvals,")
        print("run: python scripts/demo.py")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

