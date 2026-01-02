"""Service management context manager for demo scripts."""
import subprocess
import time
import sys
import os
import requests
from pathlib import Path
from typing import Optional, List, Tuple


def kill_processes_on_port(port: int) -> bool:
    """Kill any processes using the specified port using lsof."""
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
                        killed_any = True
                    except (ValueError, ProcessLookupError, PermissionError):
                        pass
            if killed_any:
                time.sleep(1)  # Give processes time to terminate
            return killed_any
        return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    except Exception:
        return False


def wait_for_service(url: str, service_name: str, timeout: int = 30) -> bool:
    """Wait for a service to be available."""
    start_time = time.time()
    attempt = 0
    while time.time() - start_time < timeout:
        attempt += 1
        try:
            response = requests.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


class ServiceManager:
    """Context manager for managing demo services."""
    
    def __init__(self, services: List[Tuple[str, List[str], int, str]]):
        """
        Initialize service manager.
        
        Args:
            services: List of (name, command, port, url) tuples
        """
        self.services = services
        self.processes: List[Optional[subprocess.Popen]] = []
        self.started_services: List[str] = []
    
    def __enter__(self):
        """Start all services."""
        # Clean up ports first
        for _, _, port, _ in self.services:
            kill_processes_on_port(port)
        
        # Start all services
        for name, command, port, url in self.services:
            print(f"Starting {name} on port {port}...")
            
            # Use current Python executable
            if command[0] == "python":
                command = [sys.executable] + command[1:]
            
            # Don't capture stdout/stderr for NPC Manager so approval prompts are visible
            # For Ticketing API, we can still capture since it doesn't need user interaction
            if "npc_manager" in name.lower():
                # Use unbuffered Python and pass through stdin/stdout/stderr
                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"  # Force unbuffered output
                
                # If command uses "python", add -u flag for unbuffered
                if command[0] == sys.executable or "python" in command[0]:
                    # Insert -u flag after python executable
                    python_cmd = command[0]
                    if python_cmd == sys.executable:
                        command = [sys.executable, "-u"] + command[1:]
                    elif "python" in python_cmd:
                        command = [python_cmd, "-u"] + command[1:]
                
                # Add uvicorn flags to reduce log noise and ensure sequential request handling
                # Find uvicorn in the command and add flags
                if "uvicorn" in command:
                    uvicorn_idx = next((i for i, arg in enumerate(command) if "uvicorn" in arg), -1)
                    if uvicorn_idx >= 0:
                        # Find where to insert flags (after module name, before other args)
                        insert_idx = uvicorn_idx + 1
                        while insert_idx < len(command) and not command[insert_idx].startswith("--"):
                            insert_idx += 1
                        # Add --no-access-log to reduce noise
                        command.insert(insert_idx, "--no-access-log")
                
                process = subprocess.Popen(
                    command,
                    stdout=None,  # Let stdout go to terminal
                    stderr=None,  # Let stderr go to terminal
                    stdin=None,   # Let stdin come from terminal
                    cwd=Path(__file__).parent.parent,
                    env=env
                )
            else:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=Path(__file__).parent.parent,
                    env=os.environ.copy()
                )
            
            # Check if process started successfully
            time.sleep(1.0)
            if process.poll() is not None:
                # Process exited immediately
                if "npc_manager" in name.lower():
                    # Can't read stdout/stderr if they're None
                    print(f"✗ {name} process exited immediately (check terminal for errors)")
                else:
                    try:
                        stdout, stderr = process.communicate(timeout=2)
                        stdout_str = stdout.decode('utf-8', errors='ignore')[:500] if stdout else ""
                        stderr_str = stderr.decode('utf-8', errors='ignore')[:500] if stderr else ""
                        print(f"✗ {name} process exited immediately")
                        if stderr_str:
                            print(f"  Error: {stderr_str}")
                    except subprocess.TimeoutExpired:
                        pass
                self.processes.append(None)
                continue
            
            self.processes.append(process)
            
            # Wait for service to be ready
            if wait_for_service(url, name, timeout=30):
                print(f"✓ {name} is ready")
                self.started_services.append(name)
            else:
                print(f"✗ {name} failed to start within timeout")
                self.processes[-1] = None
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop all services and clean up ports."""
        print("\nStopping services...")
        for i, process in enumerate(self.processes):
            if process:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass
        
        # Clean up ports
        for _, _, port, _ in self.services:
            kill_processes_on_port(port)
        
        time.sleep(1)  # Give OS time to release ports
        return False  # Don't suppress exceptions
    
    def is_ready(self, service_name: str) -> bool:
        """Check if a specific service is ready."""
        return service_name in self.started_services
    
    def get_process(self, service_name: str) -> Optional[subprocess.Popen]:
        """Get the process for a specific service."""
        for i, (name, _, _, _) in enumerate(self.services):
            if name == service_name:
                return self.processes[i] if i < len(self.processes) else None
        return None

