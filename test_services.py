"""Quick test to verify services work."""
import subprocess
import time
import requests
import sys
from pathlib import Path

# Start services
print("Starting services...")
venv_python = Path(__file__).parent / "venv" / "bin" / "python"

ticketing = subprocess.Popen(
    [str(venv_python), "-m", "uvicorn", "ticketing_api.main:app", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

time.sleep(3)

npc_manager = subprocess.Popen(
    [str(venv_python), "-m", "uvicorn", "npc_manager.main:app", "--port", "8001"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

time.sleep(3)

# Test health endpoints
try:
    r1 = requests.get("http://localhost:8000/health", timeout=2)
    print(f"Ticketing API: {r1.status_code} - {r1.json()}")
except Exception as e:
    print(f"Ticketing API error: {e}")

try:
    r2 = requests.get("http://localhost:8001/health", timeout=2)
    print(f"NPC Manager: {r2.status_code} - {r2.json()}")
except Exception as e:
    print(f"NPC Manager error: {e}")

# Cleanup
ticketing.terminate()
npc_manager.terminate()
ticketing.wait()
npc_manager.wait()

print("Test complete!")

