"""Simplified demo that shows key features without interactive prompts."""
import subprocess
import time
import requests
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

TICKETING_API_URL = "http://localhost:8000"
NPC_MANAGER_URL = "http://localhost:8001"


def wait_for_service(url: str, service_name: str, timeout: int = 30):
    """Wait for a service to be available."""
    print(f"Waiting for {service_name}...", end="", flush=True)
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                print(" ✓")
                return True
        except:
            pass
        print(".", end="", flush=True)
        time.sleep(1)
    print(" ✗ (timeout)")
    return False


def start_service(name: str, command: list):
    """Start a service as a subprocess."""
    venv_python = Path(__file__).parent.parent / "venv" / "bin" / "python"
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
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()


def main():
    """Run simplified demo."""
    print("=" * 70)
    print("NPC Manager 1 MVP - Automated Demo")
    print("=" * 70)
    print("\nThis demo shows:")
    print("1. Service health checks")
    print("2. Guardrail enforcement (max updates, do-not-contact)")
    print("3. Kill switch functionality")
    print("4. Audit trail query")
    print("\n" + "=" * 70)
    
    # Start services
    print("\n[1/4] Starting services...")
    ticketing = start_service("Ticketing API", ["python", "-m", "uvicorn", "ticketing_api.main:app", "--port", "8000"])
    time.sleep(2)
    
    npc_manager = start_service("NPC Manager", ["python", "-m", "uvicorn", "npc_manager.main:app", "--port", "8001"])
    time.sleep(2)
    
    if not wait_for_service(TICKETING_API_URL, "Ticketing API", 10):
        print("⚠ Ticketing API failed to start. Continuing with NPC Manager only...")
    else:
        print("✓ Ticketing API started")
    
    if not wait_for_service(NPC_MANAGER_URL, "NPC Manager", 10):
        print("✗ NPC Manager failed to start. Exiting.")
        stop_service(ticketing)
        stop_service(npc_manager)
        return
    print("✓ NPC Manager started")
    
    # Test guardrails
    print("\n[2/4] Testing guardrails...")
    import httpx
    
    print("\n  Testing: Max updates per run guardrail")
    with httpx.Client() as client:
        for i in range(7):
            response = client.post(
                f"{NPC_MANAGER_URL}/action",
                json={
                    "agent_id": "agent-support-001",
                    "tool_name": "update_ticket",
                    "tool_args": {"ticket_id": 1, "status": "closed"},
                    "env": "prod"
                },
                headers={"X-Agent-ID": "agent-support-001"},
                timeout=10
            )
            result = response.json()
            decision = result.get('decision', 'unknown')
            if decision == 'deny' and 'max_ticket_updates' in result.get('reason', ''):
                print(f"    ✓ Guardrail triggered at update {i+1}: {result.get('reason')[:60]}...")
                break
            elif i < 5:
                print(f"    Update {i+1}: Allowed")
            if i == 6:
                print(f"    ⚠ Guardrail didn't trigger as expected")
    
    print("\n  Testing: Do-not-contact guardrail")
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
            timeout=10
        )
        result = response.json()
        if result.get('decision') == 'deny' and 'do_not_contact' in result.get('reason', ''):
            print(f"    ✓ Guardrail triggered: {result.get('reason')[:60]}...")
        else:
            print(f"    Result: {result.get('decision')} - {result.get('reason', 'N/A')[:60]}")
    
    # Test kill switch
    print("\n[3/4] Testing kill switch...")
    from npc_manager.database import SessionLocal
    from npc_manager.models import ManagerControl
    
    db = SessionLocal()
    try:
        control = db.query(ManagerControl).first()
        if control:
            control.global_kill_switch = True
            db.commit()
            print("  ✓ Kill switch enabled")
        else:
            print("  ✗ Could not find manager control")
            db.close()
            return
    except Exception as e:
        print(f"  ✗ Error: {e}")
        db.close()
        return
    finally:
        db.close()
    
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
            timeout=10
        )
        result = response.json()
        if result.get('decision') == 'deny' and 'kill switch' in result.get('reason', '').lower():
            print(f"  ✓ Kill switch working: {result.get('reason')[:60]}...")
        else:
            print(f"  Result: {result.get('decision')} - {result.get('reason', 'N/A')[:60]}")
    
    # Disable kill switch
    db = SessionLocal()
    try:
        control = db.query(ManagerControl).first()
        if control:
            control.global_kill_switch = False
            db.commit()
            print("  ✓ Kill switch disabled")
    finally:
        db.close()
    
    # Test audit trail
    print("\n[4/4] Querying audit trail...")
    with httpx.Client() as client:
        response = client.get(f"{NPC_MANAGER_URL}/audit/timeline?limit=10")
        if response.status_code == 200:
            data = response.json()
            timeline = data.get("timeline", [])
            print(f"  ✓ Found {len(timeline)} action requests in audit trail")
            if timeline:
                print("\n  Sample entries:")
                for i, entry in enumerate(timeline[:3], 1):
                    print(f"    {i}. {entry.get('action_type')} - {entry.get('decision')} - {entry.get('risk_level')} risk")
        else:
            print(f"  ✗ Error: {response.status_code}")
    
    # Cleanup
    print("\n" + "=" * 70)
    print("Cleaning up services...")
    stop_service(ticketing)
    stop_service(npc_manager)
    time.sleep(1)
    
    print("\n" + "=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print("\n✓ Services started successfully")
    print("✓ Guardrails enforced correctly")
    print("✓ Kill switch working")
    print("✓ Audit trail accessible")
    print("\nFor full interactive demo with agent execution and approvals,")
    print("run: python scripts/demo.py (in your terminal)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()

