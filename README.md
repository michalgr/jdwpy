# jdwpy

An asynchronous, strongly typed implementation of the **Java Debug Wire Protocol (JDWP)** in Python, built on top of `asyncio`.

`jdwpy` provides abstractions for JDWP network packets, big-endian serialization for composite types, dynamic JDWP ID size configuration, and a high-level asynchronous client connection. It also includes a bi-directional logging proxy that intercepts JVM-debugger traffic to inspect and debug JDWP communications.

---

## Features

- **Asynchronous I/O**: Designed from the ground up using `asyncio` for packet transport, background reading loops, and connection management.
- **Strongly Typed Spec**: Command and reply payloads are fully mapped to Python dataclasses, preserving typing rules and static verification via [pyrefly](https://pyrefly.org/).
- **Dynamic ID Sizes**: Automatically parses and adjusts type serializers (`IdSizesSpec`) based on the JVM's `IDSizes` parameters (essential for debugging across 32-bit and 64-bit platforms).
- **JDWP Logging Proxy**: A built-in command-line proxy to capture, parse, and hexdump debug traffic in both directions.
- **tmux Interactive Session**: Includes a utility script to launch a 3-pane `tmux` debug session running `jdb` attached to the proxy, alongside live packet logs and JVM stdout.

---

## Project Structure

```
jdwpy/
├── pyproject.toml         # Project metadata and configuration (uv, pyrefly)
├── README.md              # Documentation
├── flake.nix              # Nix Flake environment configuration
├── shell.nix              # Nix shell (compat/fallback) environment configuration
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
    ├── test_protocol_core.py # Core protocol and connection tests
    ├── test_io.py            # Low-level serialization/deserialization tests
    ├── test_integration.py   # Integration tests running a real target JVM
    └── commands/             # Individual command serialization tests
```

---

## Supported JDWP Command Sets

The library implements the complete set of standard JDWP specification command sets, located under `src/jdwpy/commands/`:

| Module | Description | Supported Commands |
|---|---|---|
| `vm.py` | Virtual Machine commands | Version, Classes, IDSizes, Resume, Suspend, Exit, Dispose, etc. |
| `reference_type.py` | ReferenceType metadata | Fields, Methods, Signature, SourceFile, ClassLoader, etc. |
| `class_type.py` | ClassType inspection | Superclass, NewInstance, InvokeMethod |
| `method.py` | Method information | LineTable, VariableTable |
| `stack_frame.py` | Thread stack frame control | GetValues, SetValues, ThisObject |
| `thread_reference.py` | Thread state and control | Name, Suspend, Resume, Status, Frames |
| `event_request.py` | Event request management | Set, Clear, ClearAllBreakpoints |
| `event.py` | Event definitions | VMStart, ClassPrepare, Breakpoint, VMDeath, Composite events |
| `object_reference.py` | Object inspection | ReferenceType, GetValues, SetValues |

---

## Getting Started

### Prerequisites

You need **Java (JDK 21+)** and **uv** installed on your system. `uv` will automatically download and manage the required Python 3.14+ version if it is not available.

If you use Nix, you can load the environment via:

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

When connecting to a suspended-on-start JVM (`suspend=y`), the debugger must consume the initial `VMStartEvent` and configure the connection's ID sizes before sending other commands.

```python
import asyncio
from jdwpy import JdwpConnection
from jdwpy.commands import vm, event

async def main():
    # Connect directly to the suspended JVM's JDWP port
    async with await JdwpConnection.connect("127.0.0.1", 8000) as conn:
        # 1. Read the initial VM_START event command
        start_event = await conn.receive_command()
        assert isinstance(start_event, event.CompositeCommand)
        print("Received VMStartEvent")

        # 2. Negotiate dynamic JDWP ID sizes
        idsizes = await conn.send_command(vm.IDSizesCommand())
        print(f"Configured ID sizes: Object={conn.spec.object_id_size}B, Method={conn.spec.method_id_size}B")

        # 3. Request VM Version information
        version = await conn.send_command(vm.VersionCommand())
        print(f"Connected to: {version.vm_name} (JVM Version: {version.vm_version})")

        # 4. Resume the VM
        await conn.send_command(vm.ResumeCommand())

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Setting a Breakpoint and Reading Local Variables

A more advanced flow involving class preparation, setting a breakpoint, and inspecting local variables:

```python
import asyncio
from jdwpy import JdwpConnection, JdwpEventKind, JdwpSuspendPolicy, JdwpTag, Location
from jdwpy.commands import vm, event_request, event, reference_type, method, stack_frame, thread_reference

async def debug_session(conn: JdwpConnection):
    # Consume VMStartEvent and configure ID sizes
    await conn.receive_command()
    await conn.send_command(vm.IDSizesCommand())

    # Request notifications when the "SimpleApp" class is prepared (loaded)
    set_resp = await conn.send_command(
        event_request.SetCommand(
            event_kind=JdwpEventKind.CLASS_PREPARE,
            suspend_policy=JdwpSuspendPolicy.ALL,
            modifiers=[event_request.ClassMatchModifier(class_pattern="SimpleApp")],
        )
    )

    # Resume VM to allow class load
    await conn.send_command(vm.ResumeCommand())

    # Wait for the ClassPrepare event
    composite = await conn.receive_command()
    prep_event = composite.events[0]
    class_id = prep_event.type_id

    # Find the method ID of "testMethod"
    methods_resp = await conn.send_command(reference_type.MethodsCommand(ref_type=class_id))
    test_method = next(m for m in methods_resp.methods if m.name == "testMethod")

    # Find the slot for local variable "iteration" in the method's variable table
    var_table_resp = await conn.send_command(
        method.VariableTableCommand(ref_type=class_id, method=test_method.method_id)
    )
    iteration_var = next(v for v in var_table_resp.slots if v.name == "iteration")

    # Set breakpoint at index 0 of the method
    bp_loc = Location(
        type_tag=prep_event.ref_type_tag,
        class_id=class_id,
        method_id=test_method.method_id,
        index=0
    )
    bp_resp = await conn.send_command(
        event_request.SetCommand(
            event_kind=JdwpEventKind.BREAKPOINT,
            suspend_policy=JdwpSuspendPolicy.ALL,
            modifiers=[event_request.LocationOnlyModifier(loc=bp_loc)],
        )
    )

    # Resume to run until breakpoint is hit
    await conn.send_command(vm.ResumeCommand())

    # Wait for Breakpoint Event
    bp_composite = await conn.receive_command()
    bp_event = bp_composite.events[0]

    # Get thread call stack
    frames_resp = await conn.send_command(
        thread_reference.FramesCommand(thread=bp_event.thread, start_frame=0, length=1)
    )
    top_frame = frames_resp.frames[0]

    # Read the value of local variable "iteration" in the top stack frame
    val_resp = await conn.send_command(
        stack_frame.GetValuesCommand(
            thread=bp_event.thread,
            frame=top_frame.frame_id,
            slots=[
                stack_frame.GetValuesRequestSlot(
                    slot=iteration_var.slot,
                    sig_byte=JdwpTag.INT,
                )
            ],
        )
    )
    iteration_value = val_resp.values[0].value

    print(f"Breakpoint hit at method: {test_method.name}, Frame ID: {top_frame.frame_id}")
    print(f"Local variable 'iteration' value: {iteration_value}")
```

### 3. Starting the Logging Proxy

The proxy captures, parses, and formats traffic between your debugger (e.g., `jdb` or IDE) and the target JVM:

```bash
uv run python -m jdwpy.proxy --listen-port 5005 --target-host 127.0.0.1 --target-port 8000
```

Point your debugger to attach to `127.0.0.1:5005` instead of `8000`. The proxy intercepts the dynamic ID sizes response to configure its internal decoders, logs command sets/commands with human-readable class names, and outputs hexdumps of both directions.

### 4. Launching the Interactive TMUX Workspace

To run an automated interactive workspace containing the target app, the proxy, and `jdb`:

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
