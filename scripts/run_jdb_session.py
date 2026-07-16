#!/usr/bin/env python3
from __future__ import annotations
import os
import sys
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

# Clean import from the package now that testing is inside src/jdwpy/
from jdwpy.testing import compile_java, find_free_port, wait_for_port


def compile_debuggee(source_file: Path, output_dir: Path) -> None:
    """Compiles the Java target debuggee file, exiting on failure."""
    print("[*] Compiling SimpleApp.java...")
    try:
        compile_java(source_file, output_dir)
    except Exception as e:
        print(f"[-] Compilation failed: {e}", file=sys.stderr)
        sys.exit(1)


def terminate_process(proc: subprocess.Popen) -> None:
    """Gracefully terminates a subprocess, killing it if it hangs."""
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


@contextmanager
def running_jvm_debuggee(classpath: Path, port: int, log_file: any) -> subprocess.Popen:
    """Context manager that starts the JVM debuggee and ensures it is terminated on exit."""
    print(f"[*] Starting JVM on port {port} (suspended)...")
    jvm_cmd = [
        "java",
        f"-agentlib:jdwp=transport=dt_socket,server=y,suspend=y,address=127.0.0.1:{port}",
        "-cp",
        str(classpath),
        "SimpleApp",
    ]
    proc = subprocess.Popen(jvm_cmd, stdout=log_file, stderr=log_file, text=True)
    try:
        yield proc
    finally:
        terminate_process(proc)


@contextmanager
def running_jdwp_proxy(
    root_dir: Path, listen_port: int, target_port: int, log_file: any
) -> subprocess.Popen:
    """Context manager that starts the JDWP proxy and ensures it is terminated on exit."""
    print(
        f"[*] Starting JDWP Logging Proxy on port {listen_port} (forwarding to {target_port})..."
    )
    proxy_cmd = [
        sys.executable,
        "-u",
        "-m",
        "jdwpy.proxy",
        "--listen-port",
        str(listen_port),
        "--target-port",
        str(target_port),
    ]

    # Add src/ to PYTHONPATH so python can resolve jdwpy
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root_dir / "src")

    proc = subprocess.Popen(
        proxy_cmd, stdout=log_file, stderr=log_file, env=env, text=True
    )
    try:
        yield proc
    finally:
        terminate_process(proc)


def launch_tmux_session(
    session_name: str, proxy_port: int, proxy_log: Path, jvm_log: Path
) -> None:
    """Configures and attaches a 3-pane tmux workspace for interactive debugging."""
    print("[*] tmux detected. Launching 3-pane debugging workspace...")

    # Clear TMUX variable to avoid nesting errors
    tmux_env = os.environ.copy()
    if "TMUX" in tmux_env:
        del tmux_env["TMUX"]

    # Kill any existing session with the same name to prevent collisions
    subprocess.run(["tmux", "kill-session", "-t", session_name], capture_output=True)

    # Pane 1 (Left): Run jdb and automatically kill tmux session on exit
    jdb_cmd = f"jdb -attach 127.0.0.1:{proxy_port}; tmux kill-session -t {session_name}"
    subprocess.run(
        ["tmux", "new-session", "-d", "-s", session_name, "-n", "Debugging", jdb_cmd],
        env=tmux_env,
    )

    # Pane 2 (Right): Split active pane (left) horizontally to show JDWP proxy traces
    subprocess.run(
        [
            "tmux",
            "split-window",
            "-h",
            "-t",
            f"{session_name}:Debugging",
            f"tail -f '{proxy_log}'",
        ],
        env=tmux_env,
    )

    # Pane 3 (Bottom Left): Split the top-left pane (jdb) vertically to show JVM output
    subprocess.run(
        [
            "tmux",
            "split-window",
            "-v",
            "-t",
            f"{session_name}:Debugging.top-left",
            f"tail -f '{jvm_log}'",
        ],
        env=tmux_env,
    )

    # Focus the top-left pane so the cursor is in jdb (base-index independent)
    subprocess.run(
        ["tmux", "select-pane", "-t", f"{session_name}:Debugging.top-left"],
        env=tmux_env,
    )

    # Attach user to the tmux session
    subprocess.run(["tmux", "attach-session", "-t", session_name], env=tmux_env)


def launch_fallback_session(proxy_port: int, proxy_log: Path, jvm_log: Path) -> None:
    """Launches jdb directly in the foreground, showing instructions to tail log files."""
    print("[-] tmux not detected. Falling back to single-pane mode.")
    print(f"[*] Proxy logs: {proxy_log}")
    print(f"[*] JVM output logs: {jvm_log}")
    print("[*] Launching jdb. Press Ctrl+D or type 'exit' to quit.")
    print("-" * 60)

    try:
        subprocess.run(["jdb", "-attach", f"127.0.0.1:{proxy_port}"])
    except KeyboardInterrupt:
        pass


def main() -> None:
    root_dir = Path(__file__).parent.parent.resolve()
    source_file = root_dir / "tests" / "testdata" / "SimpleApp.java"

    # Use a single temporary directory for all compilation and logging files
    with tempfile.TemporaryDirectory(prefix="jdwpy_session_") as session_dir_str:
        session_dir = Path(session_dir_str)
        classpath = session_dir / "classes"
        proxy_log = session_dir / "proxy.log"
        jvm_log = session_dir / "jvm.log"

        # 1. Compile Java Target
        compile_debuggee(source_file, classpath)

        # 2. Ports Selection
        jvm_port = find_free_port()
        proxy_port = find_free_port()

        # 3. Start Processes and run session within context managers
        with open(jvm_log, "w") as jvm_file, open(proxy_log, "w") as proxy_file:
            with (
                running_jvm_debuggee(classpath, jvm_port, jvm_file),
                running_jdwp_proxy(root_dir, proxy_port, jvm_port, proxy_file),
            ):
                # 4. Wait for TCP services to bind
                if not wait_for_port(jvm_port) or not wait_for_port(proxy_port):
                    print("[-] Port binding failed or timed out.", file=sys.stderr)
                    sys.exit(1)

                # 5. Run Session
                tmux_available = shutil.which("tmux") is not None
                if tmux_available:
                    launch_tmux_session("jdwp_debug", proxy_port, proxy_log, jvm_log)
                else:
                    launch_fallback_session(proxy_port, proxy_log, jvm_log)

                # 6. Session teardown logs (processes terminated automatically on context exit)
                print("-" * 60)
                print("[*] Debugging session ended. Cleaning up processes...")

        print("[*] Done!")


if __name__ == "__main__":
    main()
