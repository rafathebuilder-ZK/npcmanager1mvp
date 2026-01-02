"""Reset demo databases and clean up services for fresh demo run."""
import sys
import subprocess
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.setup_db import setup_ticketing_db, setup_npc_manager_db


def kill_processes_on_port(port: int) -> bool:
    """Kill any processes using the specified port."""
    try:
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            killed_any = False
            for pid in pids:
                if pid.strip():
                    try:
                        pid_int = int(pid.strip())
                        os.kill(pid_int, 15)  # SIGTERM
                        print(f"  Killed process {pid_int} on port {port}")
                        killed_any = True
                    except (ValueError, ProcessLookupError, PermissionError):
                        pass
            if killed_any:
                import time
                time.sleep(1)  # Give processes time to terminate
            return killed_any
        return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    except Exception:
        return False


def main():
    """Reset demo to initial state."""
    print("=" * 60)
    print("Resetting Demo")
    print("=" * 60)
    
    # Step 1: Kill any running services
    print("\n[1/3] Cleaning up running services...")
    port_8000_killed = kill_processes_on_port(8000)
    port_8001_killed = kill_processes_on_port(8001)
    
    if port_8000_killed or port_8001_killed:
        print("  ✓ Stopped services on ports 8000 and 8001")
    else:
        print("  ✓ No services running on ports 8000 and 8001")
    
    # Step 2: Reset databases
    print("\n[2/3] Resetting databases...")
    try:
        setup_ticketing_db()
        setup_npc_manager_db()
        print("  ✓ Databases reset to initial state")
    except Exception as e:
        print(f"  ✗ Error resetting databases: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Summary
    print("\n[3/3] Reset complete!")
    print("\n" + "=" * 60)
    print("Demo Reset Complete")
    print("=" * 60)
    print("\n✓ Services stopped")
    print("✓ Databases reset to initial state")
    print("✓ Ready for fresh demo run")
    print("\nYou can now run: python scripts/demo.py")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

