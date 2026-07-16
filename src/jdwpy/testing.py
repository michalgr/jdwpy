from __future__ import annotations
import socket
import subprocess
import time
from pathlib import Path


def compile_java(source_path: Path, output_dir: Path) -> None:
    """Compiles a Java source file using javac.

    Writes the compiled .class files to the specified output_dir.
    """
    if not source_path.exists():
        raise FileNotFoundError(f"Java source file not found: {source_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["javac", "-g", "-d", str(output_dir), str(source_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to compile Java file {source_path}:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )


def find_free_port() -> int:
    """Finds and returns an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_port(port: int, host: str = "127.0.0.1", timeout: float = 5.0) -> bool:
    """Polls a port using lsof to check if a process is listening on it, without connecting.

    Returns True if the port is open and listening before the timeout, False otherwise.
    """
    start_time = time.time()
    cmd = ["lsof", f"-iTCP:{port}", "-sTCP:LISTEN"]
    while time.time() - start_time < timeout:
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0:
            return True
        time.sleep(0.1)
    return False
