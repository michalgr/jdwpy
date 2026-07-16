# jdwpy

An asynchronous, strongly typed implementation of the **Java Debug Wire Protocol (JDWP)** in Python, built on top of `asyncio`.

`jdwpy` provides low-level abstractions for JDWP network packets, big-endian serialization for composite types, dynamic JDWP ID size configuration, and a high-level asynchronous client connection. It also includes a bi-directional logging proxy that intercepts JVM-debugger traffic to inspect and debug JDWP communications.

---

## Features

- **Asynchronous I/O**: Designed from the ground up using `asyncio` for packet transport, background reading loops, and connection management.
- **Strongly Typed Spec**: Command and reply payloads are fully mapped to Python dataclasses, preserving typing rules and static verification via `pyrefly`.
- **Dynamic ID Sizes**: Automatically parses and adjusts type serializers (`IdSizesSpec`) based on the JVM's `IDSizes` parameters (essential for debugging across 32-bit and 64-bit platforms).
- **JDWP Logging Proxy**: A built-in command-line proxy to capture, parse, and hexdump debug traffic in both directions.
- **tmx Interactive Session**: Includes a utility script to launch a 3-pane `tmux` debug session running `jdb` attached to the proxy, alongside live packet logs and JVM stdout.

---

## Project Structure

```
jdwpy/
├── pyproject.toml         # Modern project metadata (uv build backend, pyrefly)
├── README.md              # Documentation
├── shell.nix              # Nix environment configuration for dependencies
├── src/
│   └── jdwpy/
│       ├── __init__.py    # Public exports
│       ├── connection.py  # Asynchronous connection, packet sender/receiver
│       ├── constants.py   # JDWP protocol error codes, tags, flags, and policies
│       ├── exceptions.py  # Custom exceptions for JDWP error codes
│       ├── io.py          # Big-endian stream reader/writer with variable size ID serialization
│       ├── packet.py      # Abstract JdwpPacket, JdwpCommandPacket, JdwpReplyPacket
│       ├── proxy.py       # JDWP bi-directional logging proxy CLI
│       ├── spec.py        # Strong types (ObjectID, FrameID, etc.) and IdSizesSpec
│       ├── testing.py     # Test utilities (Java compiling, port detection)
│       └── commands/      # Registry and individual command set modules (VM, StackFrame, etc.)
└── tests/
    ├── test_protocol.py   # Low-level protocol serialization/deserialization tests
    └── test_integration.py# Integration tests running a real target JVM
```

---

## Getting Started

### Prerequisites

You need **Python 3.14+** and **Java (JDK 21+)** installed on your system. If you use Nix, you can load the environment via:

```bash
nix-shell
```

### Installation

This project uses `uv` for package management. To install the dependencies and configure the virtual environment:

```bash
uv sync
```

---

## Usage Examples

### 1. Connecting Asynchronously to a JVM Debug Target

```python
import asyncio
from jdwpy import JdwpConnection, establish_jdwp_connection
from jdwpy.commands.vm import VersionCommand, ResumeCommand

async def main():
    # Connect directly to the suspended JVM's JDWP port
    async with await JdwpConnection.connect("127.0.0.1", 8000) as conn:
        # Request VM Version information
        version = await conn.send_command(VersionCommand())
        print(f"Connected to: {version.vm_name} (JVM Version: {version.vm_version})")

        # Resume the VM
        await conn.send_command(ResumeCommand())

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Starting the Logging Proxy

The proxy captures traffic between your debugger (e.g., `jdb` or IDE) and the target JVM:

```bash
uv run python -m jdwpy.proxy --listen-port 5005 --target-host 127.0.0.1 --target-port 8000 --verbose
```

Once running, point your debugger to attach to `127.0.0.1:5005`. All traffic will be printed to stdout as structured hexdumps and parsed command payloads.

### 3. Launching the Interactive TMUX Workspace

To test the proxy interactively with a test app:

```bash
uv run scripts/run_jdb_session.py
```

If `tmux` is available, this opens a 3-pane window:
1. **Pane 1**: Live interactive `jdb` session.
2. **Pane 2**: Live tail of the JDWP Logging Proxy traces.
3. **Pane 3**: Output logs of the target JVM debuggee.

---

## Development and Validation

Quality control steps are defined in the workspace settings. Always run these checks before submitting pull requests:

### 1. Code Formatting
Format files using Ruff:
```bash
uv run ruff format
uv run ruff check
```

### 2. Type Checking
Perform type verification with `pyrefly`:
```bash
uv run pyrefly check
```

### 3. Testing
Run the unit and integration tests (which compile a test class and launch a local subprocess JVM):
```bash
nix-shell --run "uv run pytest"
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
