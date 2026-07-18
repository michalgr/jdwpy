from __future__ import annotations
import asyncio
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
import pytest
from typing import Any

from jdwpy.constants import JdwpEventKind, JdwpSuspendPolicy, JdwpTag
from jdwpy import commands
from jdwpy.connection import JdwpSession
from jdwpy.proxy import JdwpProxySession
from jdwpy.spec import Location
from jdwpy.testing import compile_java, find_free_port, wait_for_port


@contextmanager
def running_jvm_debuggee():
    """Context manager to compile and run the Java test program in debug mode."""
    # Locate SimpleApp.java in the same directory structure
    source_file = Path(__file__).parent / "testdata" / "SimpleApp.java"

    with tempfile.TemporaryDirectory(prefix="jdwpy_classes_") as tmpdir:
        classpath = Path(tmpdir)
        compile_java(source_file, classpath)
        port = find_free_port()

        # Launch JVM with JDWP suspended and listening on the free port
        cmd = [
            "java",
            f"-agentlib:jdwp=transport=dt_socket,server=y,suspend=y,address=127.0.0.1:{port}",
            "-cp",
            str(classpath),
            "SimpleApp",
        ]
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        try:
            # Wait for the JDWP port to be open and accepting connections
            if not wait_for_port(port, timeout=5.0):
                proc.terminate()
                stdout, stderr = proc.communicate()
                raise RuntimeError(
                    f"JVM JDWP agent failed to bind to port {port} in time.\n"
                    f"STDOUT: {stdout}\nSTDERR: {stderr}"
                )
            yield port, proc
        finally:
            # Gracefully terminate the JVM process
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


async def assert_jdwp_session_flow(session: JdwpSession) -> None:
    """Establishes JDWP connection, sets class prep request, inspects methods,
    sets breakpoint on testMethod, and verifies stack trace and iteration parameter.
    """
    # 0. Read startup VM_START composite event command
    event = await session.receive_command()
    assert isinstance(event, commands.event.CompositeCommand)
    assert len(event.events) == 1
    assert isinstance(event.events[0], commands.event.VMStartEvent)

    # 1. Send IDSizesCommand to configure Spec sizes
    idsizes = await session.send_command(commands.vm.IDSizesCommand())
    assert isinstance(idsizes, commands.vm.IDSizesResponse)

    # 2. Set a CLASS_PREPARE event request to monitor loading of SimpleApp
    set_resp = await session.send_command(
        commands.event_request.SetCommand(
            event_kind=JdwpEventKind.CLASS_PREPARE,
            suspend_policy=JdwpSuspendPolicy.ALL,
            modifiers=[
                commands.event_request.ClassMatchModifier(class_pattern="SimpleApp")
            ],
        )
    )
    class_prep_request_id = set_resp.request_id

    # 3. Resume execution to trigger class preparation
    await session.send_command(commands.vm.ResumeCommand())

    # 4. Read ClassPrepareEvent for SimpleApp
    event_cmd = await session.receive_command()
    assert isinstance(event_cmd, commands.event.CompositeCommand)
    class_prep = event_cmd.events[0]
    assert isinstance(class_prep, commands.event.ClassPrepareEvent)
    assert class_prep.signature == "LSimpleApp;"

    # 5. Retrieve methods of SimpleApp
    methods_resp = await session.send_command(
        commands.reference_type.MethodsCommand(ref_type=class_prep.type_id)
    )
    test_method = next(m for m in methods_resp.methods if m.name == "testMethod")
    method_id = test_method.method_id

    # 6. Retrieve variable table of testMethod to find slot for "iteration"
    var_table_resp = await session.send_command(
        commands.method.VariableTableCommand(
            ref_type=class_prep.type_id, method=method_id
        )
    )
    iteration_var = next(v for v in var_table_resp.slots if v.name == "iteration")
    iteration_slot = iteration_var.slot

    # 7. Set a breakpoint at index 0 of testMethod
    bp_loc = Location(
        type_tag=class_prep.ref_type_tag,
        class_id=class_prep.type_id,
        method_id=method_id,
        index=0,
    )
    bp_set_resp = await session.send_command(
        commands.event_request.SetCommand(
            event_kind=JdwpEventKind.BREAKPOINT,
            suspend_policy=JdwpSuspendPolicy.ALL,
            modifiers=[commands.event_request.LocationOnlyModifier(loc=bp_loc)],
        )
    )
    bp_request_id = bp_set_resp.request_id

    # 8. Loop for the first 3 iterations, verifying iteration value increases
    for expected_iteration in range(1, 4):
        # Resume VM
        await session.send_command(commands.vm.ResumeCommand())

        # Wait for breakpoint hit
        bp_event_cmd = await session.receive_command()
        assert isinstance(bp_event_cmd, commands.event.CompositeCommand)
        bp_event = bp_event_cmd.events[0]
        assert isinstance(bp_event, commands.event.BreakpointEvent)
        assert bp_event.request_id == bp_request_id

        # Get stack trace (frames)
        frames_resp = await session.send_command(
            commands.thread_reference.FramesCommand(
                thread=bp_event.thread,
                start_frame=0,
                length=-1,
            )
        )
        assert len(frames_resp.frames) >= 1
        top_frame = frames_resp.frames[0]
        assert top_frame.location.method_id == method_id

        # Get value of the local variable 'iteration' in the top frame
        val_resp = await session.send_command(
            commands.stack_frame.GetValuesCommand(
                thread=bp_event.thread,
                frame=top_frame.frame_id,
                slots=[
                    commands.stack_frame.GetValuesRequestSlot(
                        slot=iteration_slot,
                        sig_byte=JdwpTag.INT,
                    )
                ],
            )
        )
        assert len(val_resp.values) == 1
        iteration_val = val_resp.values[0]
        assert iteration_val.tag == JdwpTag.INT
        assert iteration_val.value == expected_iteration

    # 9. Clean up event requests
    await session.send_command(
        commands.event_request.ClearCommand(
            event_kind=JdwpEventKind.BREAKPOINT,
            request_id=bp_request_id,
        )
    )
    await session.send_command(
        commands.event_request.ClearCommand(
            event_kind=JdwpEventKind.CLASS_PREPARE,
            request_id=class_prep_request_id,
        )
    )

    # 10. Resume JVM to complete execution
    await session.send_command(commands.vm.ResumeCommand())


@pytest.mark.asyncio
async def test_direct_jdwp_connection() -> None:
    """Verifies that we can connect directly to a JVM JDWP agent, exchange version & id size packets."""
    with running_jvm_debuggee() as (port, proc):
        # 1. Connect directly to JVM JDWP agent
        async with await JdwpSession.connect("127.0.0.1", port) as session:
            await assert_jdwp_session_flow(session)


@pytest.mark.asyncio
async def test_proxied_jdwp_connection() -> None:
    """Verifies that a JdwpProxySession successfully forwards traffic and intercepts IDSizes responses."""
    with running_jvm_debuggee() as (jvm_port, proc):
        proxy_port = find_free_port()

        # 1. Define proxy connection handler
        async def client_connected(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ) -> None:
            session = await JdwpProxySession.create(
                reader, writer, "127.0.0.1", jvm_port
            )
            await session.run()

        # 2. Start the JDWP Logging Proxy server
        server = await asyncio.start_server(client_connected, "127.0.0.1", proxy_port)

        # 3. Use async context managers to manage server and client connections
        async with server:
            async with await JdwpSession.connect("127.0.0.1", proxy_port) as session:
                await assert_jdwp_session_flow(session)
