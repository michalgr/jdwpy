from __future__ import annotations
from typing import ClassVar
import asyncio
import struct
import pytest
from jdwpy.constants import JdwpTag, JdwpErrorCode, HANDSHAKE
from jdwpy.spec import IdSizesSpec, ObjectID, ReferenceTypeID, FieldID, MethodID, FrameID
from jdwpy.packet import JdwpPacket, JdwpCommandPacket, JdwpReplyPacket
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.commands import (
    get_command_class,
    register_command,
    VersionCommand,
    VersionResponse,
    IDSizesCommand,
    IDSizesResponse,
    JdwpCommand,
)
from jdwpy.connection import JdwpConnection, JdwpPacketConnection, JdwpPacketSender, JdwpPacketReceiver


class MockStreamWriter:
    """Mock StreamWriter for testing connections completely in-memory."""
    def __init__(self) -> None:
        self.buffer = bytearray()
        self.closed = False

    def write(self, data: bytes) -> None:
        self.buffer.extend(data)

    async def drain(self) -> None:
        await asyncio.sleep(0)  # Yield execution

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        await asyncio.sleep(0)


def create_mock_connection() -> tuple[JdwpConnection, asyncio.StreamReader, MockStreamWriter]:
    """Helper factory that constructs all JDWP connection mock objects and starts the loop."""
    reader = asyncio.StreamReader()
    writer = MockStreamWriter()
    sender = JdwpPacketSender(writer)  # type: ignore
    receiver = JdwpPacketReceiver(reader)
    packet_conn = JdwpPacketConnection(sender, receiver)
    packet_conn.start()
    conn = JdwpConnection(packet_conn)
    return conn, reader, writer


def test_id_sizes_spec_struct_compilation() -> None:
    """Verifies that IdSizesSpec pre-compiles correct struct sizes and formats."""
    # Test 8-byte spec (typical 64-bit JVM)
    spec_8 = IdSizesSpec.create(
        field_id_size=8,
        method_id_size=8,
        object_id_size=8,
        reference_type_id_size=8,
        frame_id_size=8
    )
    assert spec_8.field_id_struct.format == ">Q"
    assert spec_8.object_id_struct.format == ">Q"
    assert spec_8.field_id_struct.size == 8

    # Test 4-byte spec (typical 32-bit JVM)
    spec_4 = IdSizesSpec.create(
        field_id_size=4,
        method_id_size=4,
        object_id_size=4,
        reference_type_id_size=4,
        frame_id_size=4
    )
    assert spec_4.field_id_struct.format == ">I"
    assert spec_4.object_id_struct.format == ">I"
    assert spec_4.field_id_struct.size == 4


def test_jdwp_writer_and_reader_primitives() -> None:
    """Tests big-endian serialization and parsing of primitives."""
    spec = IdSizesSpec.create()
    writer = JdwpWriter(spec)
    
    writer.write_byte(0xAB)
    writer.write_boolean(True)
    writer.write_boolean(False)
    writer.write_int(0x12345678)
    writer.write_long(0x1122334455667788)
    writer.write_string("Hello JDWP!")
    
    serialized = writer.get_bytes()
    reader = JdwpReader(serialized, spec)
    
    assert reader.read_byte() == 0xAB
    assert reader.read_boolean() is True
    assert reader.read_boolean() is False
    assert reader.read_int() == 0x12345678
    assert reader.read_long() == 0x1122334455667788
    assert reader.read_string() == "Hello JDWP!"
    assert reader.remaining == 0


def test_jdwp_writer_and_reader_ids() -> None:
    """Verifies variable length JDWP ID writing and reading."""
    # Test 8-byte mode
    spec_8 = IdSizesSpec.create(object_id_size=8)
    writer_8 = JdwpWriter(spec_8)
    writer_8.write_object_id(ObjectID(0xABCDEF1234567890))
    
    reader_8 = JdwpReader(writer_8.get_bytes(), spec_8)
    assert reader_8.read_object_id() == 0xABCDEF1234567890

    # Test 4-byte mode
    spec_4 = IdSizesSpec.create(object_id_size=4)
    writer_4 = JdwpWriter(spec_4)
    writer_4.write_object_id(ObjectID(0x76543210))
    
    reader_4 = JdwpReader(writer_4.get_bytes(), spec_4)
    assert reader_4.read_object_id() == 0x76543210


@pytest.mark.asyncio
async def test_packet_stream_serialization() -> None:
    """Verifies async stream-based serialization and deserialization of JdwpPackets."""
    # 1. Test Command Packet
    cmd_payload = b"\x00\x00\x00\x05Hello"
    cmd_packet = JdwpCommandPacket(
        id=42,
        flags=0x00,
        command_set=1,
        command=7,
        data=cmd_payload
    )
    
    writer = MockStreamWriter()
    cmd_packet.serialize(writer)  # type: ignore
    
    # Read back from stream reader
    reader = asyncio.StreamReader()
    reader.feed_data(writer.buffer)
    reader.feed_eof()
    
    deserialized = await JdwpPacket.deserialize(reader)
    assert isinstance(deserialized, JdwpCommandPacket)
    assert deserialized.id == 42
    assert deserialized.flags == 0x00
    assert deserialized.command_set == 1
    assert deserialized.command == 7
    assert deserialized.data == cmd_payload
    assert deserialized.is_reply is False

    # 2. Test Reply Packet
    reply_payload = b"World!"
    reply_packet = JdwpReplyPacket(
        id=42,
        flags=0x80,
        error_code=JdwpErrorCode.INVALID_OBJECT,
        data=reply_payload
    )
    
    writer_reply = MockStreamWriter()
    reply_packet.serialize(writer_reply)  # type: ignore
    
    reader_reply = asyncio.StreamReader()
    reader_reply.feed_data(writer_reply.buffer)
    reader_reply.feed_eof()
    
    deserialized_reply = await JdwpPacket.deserialize(reader_reply)
    assert isinstance(deserialized_reply, JdwpReplyPacket)
    assert deserialized_reply.id == 42
    assert deserialized_reply.flags == 0x80
    assert deserialized_reply.error_code == JdwpErrorCode.INVALID_OBJECT
    assert deserialized_reply.data == reply_payload
    assert deserialized_reply.is_reply is True


def test_command_registry_indexing() -> None:
    """Verifies that concrete commands are successfully indexed in the registry."""
    assert get_command_class(1, 1) is VersionCommand
    assert get_command_class(1, 7) is IDSizesCommand
    assert get_command_class(99, 98) is MockNoResponseCommand
    assert get_command_class(99, 99) is None


def test_concrete_commands_payloads() -> None:
    """Verifies serialization and deserialization of command and reply payloads."""
    spec = IdSizesSpec.create()

    # 1. Version Command Set
    cmd = VersionCommand()
    assert cmd.to_bytes(spec) == b""  # Empty payload request

    resp = VersionResponse(
        description="JVM 14.0",
        jdwp_major=1,
        jdwp_minor=6,
        vm_version="14.0.1",
        vm_name="OpenJDK"
    )
    deserialized_resp = VersionResponse.from_bytes(resp.to_bytes(spec), spec)
    assert deserialized_resp.description == "JVM 14.0"
    assert deserialized_resp.jdwp_major == 1
    assert deserialized_resp.jdwp_minor == 6
    assert deserialized_resp.vm_version == "14.0.1"
    assert deserialized_resp.vm_name == "OpenJDK"

    # 2. IDSizes Command Set
    resp_ids = IDSizesResponse(
        field_id_size=4,
        method_id_size=4,
        object_id_size=8,
        reference_type_id_size=8,
        frame_id_size=8
    )
    deserialized_ids = IDSizesResponse.from_bytes(resp_ids.to_bytes(spec), spec)
    assert deserialized_ids.field_id_size == 4
    assert deserialized_ids.method_id_size == 4
    assert deserialized_ids.object_id_size == 8
    assert deserialized_ids.reference_type_id_size == 8
    assert deserialized_ids.frame_id_size == 8


@pytest.mark.asyncio
async def test_jdwp_connection_full_flow() -> None:
    """Tests the JDWP handshake, background loop, futures routing, and dynamic spec replacement."""
    conn, reader, writer = create_mock_connection()

    # 2. Send IDSizesCommand and intercept raw writer bytes to feed mock response
    task = asyncio.create_task(conn.send_command(IDSizesCommand()))
    
    # Let the event loop run to send command
    await asyncio.sleep(0)
    
    # Verify command was sent
    assert len(writer.buffer) >= 11
    packet = JdwpCommandPacket.parse(writer.buffer[:11], writer.buffer[11:])
    assert packet.id == 1
    assert packet.command_set == 1
    assert packet.command == 7
    writer.buffer.clear()

    # Construct and feed the mock IDSizes response packet using library components
    resp_ids = IDSizesResponse(
        field_id_size=4,
        method_id_size=4,
        object_id_size=8,
        reference_type_id_size=8,
        frame_id_size=8,
    )
    payload = resp_ids.to_bytes(conn.spec)

    reply_packet = JdwpReplyPacket(
        id=packet.id,
        flags=0x80,
        error_code=JdwpErrorCode.NONE,
        data=payload,
    )
    temp_writer = MockStreamWriter()
    reply_packet.serialize(temp_writer)  # type: ignore
    reader.feed_data(temp_writer.buffer)
    
    # Wait for command response
    response = await task
    assert isinstance(response, IDSizesResponse)
    assert response.field_id_size == 4
    assert response.method_id_size == 4
    assert response.object_id_size == 8
    
    # Verify Dynamic IDSizes Spec Replacement!
    assert conn.spec.field_id_struct.size == 4
    assert conn.spec.object_id_struct.size == 8

    await conn.close()


@register_command()
class MockNoResponseCommand(JdwpCommand[None]):
    COMMAND_SET: ClassVar[int] = 99
    COMMAND: ClassVar[int] = 98

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> MockNoResponseCommand:
        return cls()


@pytest.mark.asyncio
async def test_jdwp_command_no_response() -> None:
    conn, reader, writer = create_mock_connection()
    
    res = await conn.send_command(MockNoResponseCommand())
    assert res is None
    
    assert len(writer.buffer) == 11
    packet = JdwpCommandPacket.parse(writer.buffer, b"")
    assert packet.command_set == 99
    assert packet.command == 98
    
    await conn.close()

