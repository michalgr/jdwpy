from __future__ import annotations
import asyncio
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
import pytest

from jdwpy.constants import JdwpEventKind, JdwpSuspendPolicy
from jdwpy import commands
from jdwpy.connection import JdwpConnection
from jdwpy.proxy import JdwpProxySession
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


async def assert_jdwp_session_flow(conn: JdwpConnection) -> None:
    """Sends JDWP version and IDSizes commands, verifying the responses and spec updates."""
    # 0. Read startup VM_START composite event command
    event = await conn.read_command()
    assert isinstance(event, commands.event.CompositeCommand)
    assert len(event.events) == 1
    assert isinstance(event.events[0], commands.event.VMStartEvent)
    assert event.events[0].thread > 0

    # 1. Send commands.vm.VersionCommand and verify response
    version = await conn.send_command(commands.vm.VersionCommand())
    assert isinstance(version, commands.vm.VersionResponse)
    assert version.jdwp_major >= 1
    assert any(
        vendor in version.vm_name
        for vendor in ["OpenJDK", "HotSpot", "Java", "Temurin"]
    )

    # 2. Check and send commands.vm.IDSizesCommand
    initial_field_size = conn.spec.field_id_struct.size
    assert initial_field_size == 8  # Default standard size

    idsizes = await conn.send_command(commands.vm.IDSizesCommand())
    assert isinstance(idsizes, commands.vm.IDSizesResponse)

    # 3. Check that connection spec was dynamically updated
    assert conn.spec.field_id_struct.size == idsizes.field_id_size
    assert conn.spec.object_id_struct.size == idsizes.object_id_size
    assert conn.spec.method_id_struct.size == idsizes.method_id_size

    # 4. Set a CLASS_PREPARE event request to monitor loading/preparation of SimpleApp
    set_resp = await conn.send_command(
        commands.event_request.SetCommand(
            event_kind=JdwpEventKind.CLASS_PREPARE,
            suspend_policy=JdwpSuspendPolicy.ALL,
            modifiers=[
                commands.event_request.ClassMatchModifier(class_pattern="SimpleApp")
            ],
        )
    )
    assert isinstance(set_resp, commands.event_request.SetResponse)
    request_id = set_resp.request_id

    # 5. Resume execution to trigger class preparation
    await conn.send_command(commands.vm.ResumeCommand())

    # 6. Read the Composite event and verify it is indeed commands.event.ClassPrepareEvent for SimpleApp
    event_cmd = await conn.read_command()
    assert isinstance(event_cmd, commands.event.CompositeCommand)
    assert len(event_cmd.events) == 1

    class_prep = event_cmd.events[0]
    assert isinstance(class_prep, commands.event.ClassPrepareEvent)
    assert class_prep.request_id == request_id
    assert class_prep.signature == "LSimpleApp;"

    # 7. Resume again so the target VM can finish execution
    await conn.send_command(commands.vm.ResumeCommand())


@pytest.mark.asyncio
async def test_direct_jdwp_connection() -> None:
    """Verifies that we can connect directly to a JVM JDWP agent, exchange version & id size packets."""
    with running_jvm_debuggee() as (port, proc):
        # 1. Connect directly to JVM JDWP agent
        async with await JdwpConnection.connect("127.0.0.1", port) as conn:
            await assert_jdwp_session_flow(conn)


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
            async with await JdwpConnection.connect("127.0.0.1", proxy_port) as conn:
                await assert_jdwp_session_flow(conn)
