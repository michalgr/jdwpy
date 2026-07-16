from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, Self
import asyncio
import pytest
from jdwpy.constants import (
    JdwpThreadStatus,
    JdwpSuspendStatus,
    JdwpErrorCode,
    JdwpEventKind,
    JdwpSuspendPolicy,
    JdwpTypeTag,
    JdwpTag,
    JdwpClassStatus,
    JdwpInvokeOptions,
)
from jdwpy.spec import (
    Location,
    ArrayTypeID,
    ArrayObjectID,
    ClassID,
    ClassLoaderID,
    ClassObjectID,
    InterfaceID,
    FrameID,
    IdSizesSpec,
    ObjectID,
    ReferenceTypeID,
    FieldID,
    MethodID,
    TaggedObjectID,
    JdwpValue,
    ThreadID,
    ThreadGroupID,
    StringID,
)
from jdwpy.packet import JdwpPacket, JdwpCommandPacket, JdwpReplyPacket
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy import commands, JdwpException

from jdwpy.connection import (
    JdwpConnection,
    JdwpPacketConnection,
    JdwpPacketSender,
    JdwpPacketReceiver,
)


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


def create_mock_connection(
    spec: IdSizesSpec | None = None,
) -> tuple[JdwpConnection, asyncio.StreamReader, MockStreamWriter]:
    """Helper factory that constructs all JDWP connection mock objects and starts the loop."""
    reader = asyncio.StreamReader()
    writer = MockStreamWriter()
    sender = JdwpPacketSender(writer)  # type: ignore
    receiver = JdwpPacketReceiver(reader)
    packet_conn = JdwpPacketConnection(sender, receiver)
    packet_conn.start()
    conn = JdwpConnection(packet_conn, spec=spec)
    return conn, reader, writer


def parse_command_packet(buffer: bytes | bytearray) -> JdwpCommandPacket:
    """Parses a JdwpCommandPacket from a raw bytes buffer."""
    if len(buffer) < 11:
        raise ValueError("Buffer too short for JDWP packet")
    return JdwpCommandPacket.from_bytes(bytes(buffer[:11]), bytes(buffer[11:]))


def feed_reply(reader: asyncio.StreamReader, packet_id: int, payload: bytes) -> None:
    """Serializes a successful JdwpReplyPacket and feeds it to the StreamReader."""
    reply = JdwpReplyPacket(
        id=packet_id,
        flags=0x80,
        error_code=JdwpErrorCode.NONE,
        data=payload,
    )
    reader.feed_data(reply.to_bytes())


async def assert_command_roundtrip[T: commands.JdwpResponse | None](
    command: commands.JdwpCommand[T],
    expected_response: T,
    spec: IdSizesSpec | None = None,
) -> None:
    """Generic helper that sets up a mock connection, runs assertions on serialization,

    and executes a full JDWP command-response roundtrip.
    """
    conn, reader, writer = create_mock_connection(spec)
    async with conn:
        # 1. Launch sending the command
        task = asyncio.create_task(conn.send_command(command))
        await asyncio.sleep(0)  # Yield execution to let command write to mock stream

        # 2. Verify command set, command, and command payload match on the wire
        packet = parse_command_packet(writer.buffer)
        assert packet.command_set == command.COMMAND_SET
        assert packet.command == command.COMMAND

        # Deserialize the bytes written to the writer, verifying they reconstruct the command
        deserialized_command = command.__class__.from_bytes(packet.data, conn.spec)
        assert deserialized_command == command

        # 3. If a response is expected, serialize expected_response to feed mock reply
        response_class = commands.get_response_class(command.__class__)
        assert (response_class is None) == (expected_response is None)

        if response_class is not None:
            assert expected_response is not None
            serialized_response = expected_response.to_bytes(conn.spec)
            feed_reply(reader, packet.id, serialized_response)

        response = await task

        # Verify the returned response equals expected_response
        assert response == expected_response

        # Verify dynamic spec updates when commands.vm.IDSizesResponse is received
        if isinstance(response, commands.vm.IDSizesResponse):
            assert conn.spec.field_id_struct.size == response.field_id_size
            assert conn.spec.object_id_struct.size == response.object_id_size
            assert conn.spec.method_id_struct.size == response.method_id_size
            assert (
                conn.spec.reference_type_id_struct.size
                == response.reference_type_id_size
            )
            assert conn.spec.frame_id_struct.size == response.frame_id_size


def test_id_sizes_spec_struct_compilation() -> None:
    """Verifies that IdSizesSpec pre-compiles correct struct sizes and formats."""
    # Test 8-byte spec (typical 64-bit JVM)
    spec_8 = IdSizesSpec.create(
        field_id_size=8,
        method_id_size=8,
        object_id_size=8,
        reference_type_id_size=8,
        frame_id_size=8,
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
        frame_id_size=4,
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
        id=42, flags=0x00, command_set=1, command=7, data=cmd_payload
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
        id=42, flags=0x80, error_code=JdwpErrorCode.INVALID_OBJECT, data=reply_payload
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
    assert commands.get_command_class(1, 1) is commands.vm.VersionCommand
    assert commands.get_command_class(1, 7) is commands.vm.IDSizesCommand
    assert commands.get_command_class(99, 98) is MockNoResponseCommand
    assert commands.get_command_class(99, 99) is None


@pytest.mark.asyncio
async def test_virtual_machine_command_set() -> None:
    """Verifies flow and serialization for commands in the VirtualMachine Command Set (Set 1)."""
    spec = IdSizesSpec.create()

    # 1. Version Command
    resp_version = commands.vm.VersionResponse(
        description="JVM 14.0",
        jdwp_major=1,
        jdwp_minor=6,
        vm_version="14.0.1",
        vm_name="OpenJDK",
    )
    await assert_command_roundtrip(
        commands.vm.VersionCommand(), resp_version, spec=spec
    )

    # 2. IDSizes Command & spec update verification
    resp_ids = commands.vm.IDSizesResponse(
        field_id_size=4,
        method_id_size=4,
        object_id_size=8,
        reference_type_id_size=8,
        frame_id_size=8,
    )
    await assert_command_roundtrip(commands.vm.IDSizesCommand(), resp_ids, spec=spec)

    # 3. ClassesBySignature Command
    classes_by_sig_resp = commands.vm.ClassesBySignatureResponse(
        classes=[
            commands.vm.ClassesBySignatureEntry(
                ref_type_tag=JdwpTypeTag.CLASS,
                type_id=ReferenceTypeID(42),
                status=JdwpClassStatus.VERIFIED,
            )
        ]
    )
    await assert_command_roundtrip(
        commands.vm.ClassesBySignatureCommand(signature="Ljava/lang/String;"),
        classes_by_sig_resp,
        spec=spec,
    )

    # 4. AllClasses Command
    all_classes_resp = commands.vm.AllClassesResponse(
        classes=[
            commands.vm.AllClassesEntry(
                ref_type_tag=JdwpTypeTag.CLASS,
                type_id=ReferenceTypeID(42),
                signature="Ljava/lang/String;",
                status=JdwpClassStatus.VERIFIED,
            )
        ]
    )
    await assert_command_roundtrip(
        commands.vm.AllClassesCommand(),
        all_classes_resp,
        spec=spec,
    )

    # 5. AllThreads Command
    all_threads_resp = commands.vm.AllThreadsResponse(
        threads=[ThreadID(42), ThreadID(43)]
    )
    await assert_command_roundtrip(
        commands.vm.AllThreadsCommand(),
        all_threads_resp,
        spec=spec,
    )

    # 6. TopLevelThreadGroups Command
    top_level_groups_resp = commands.vm.TopLevelThreadGroupsResponse(
        groups=[ThreadGroupID(44)]
    )
    await assert_command_roundtrip(
        commands.vm.TopLevelThreadGroupsCommand(),
        top_level_groups_resp,
        spec=spec,
    )

    # 7. Dispose Command
    await assert_command_roundtrip(
        commands.vm.DisposeCommand(),
        commands.vm.DisposeResponse(),
        spec=spec,
    )

    # 8. Suspend Command
    await assert_command_roundtrip(
        commands.vm.SuspendCommand(),
        commands.vm.SuspendResponse(),
        spec=spec,
    )

    # 9. Resume Command
    await assert_command_roundtrip(
        commands.vm.ResumeCommand(),
        commands.vm.ResumeResponse(),
        spec=spec,
    )

    # 10. Exit Command
    await assert_command_roundtrip(
        commands.vm.ExitCommand(exit_code=42),
        commands.vm.ExitResponse(),
        spec=spec,
    )

    # 11. CreateString Command
    await assert_command_roundtrip(
        commands.vm.CreateStringCommand(utf="hello"),
        commands.vm.CreateStringResponse(string_object=StringID(45)),
        spec=spec,
    )

    # 12. Capabilities Command
    caps_resp = commands.vm.CapabilitiesResponse(
        can_watch_field_modification=True,
        can_watch_field_access=True,
        can_get_bytecodes=True,
        can_get_synthetic_attribute=True,
        can_get_owned_monitor_info=True,
        can_get_current_contended_monitor=True,
        can_get_monitor_info=True,
    )
    await assert_command_roundtrip(
        commands.vm.CapabilitiesCommand(),
        caps_resp,
        spec=spec,
    )

    # 13. ClassPaths Command
    class_paths_resp = commands.vm.ClassPathsResponse(
        base_dir="/base",
        classpaths=["/cp1"],
        bootclasspaths=["/bcp1"],
    )
    await assert_command_roundtrip(
        commands.vm.ClassPathsCommand(),
        class_paths_resp,
        spec=spec,
    )

    # 14. DisposeObjects Command
    await assert_command_roundtrip(
        commands.vm.DisposeObjectsCommand(
            requests=[
                commands.vm.DisposeObjectsRequest(object_id=ObjectID(46), ref_cnt=2)
            ]
        ),
        commands.vm.DisposeObjectsResponse(),
        spec=spec,
    )

    # 15. HoldEvents Command
    await assert_command_roundtrip(
        commands.vm.HoldEventsCommand(),
        commands.vm.HoldEventsResponse(),
        spec=spec,
    )

    # 16. ReleaseEvents Command
    await assert_command_roundtrip(
        commands.vm.ReleaseEventsCommand(),
        commands.vm.ReleaseEventsResponse(),
        spec=spec,
    )

    # 17. CapabilitiesNew Command
    caps_new_resp = commands.vm.CapabilitiesNewResponse(
        can_watch_field_modification=True,
        can_watch_field_access=True,
        can_get_bytecodes=True,
        can_get_synthetic_attribute=True,
        can_get_owned_monitor_info=True,
        can_get_current_contended_monitor=True,
        can_get_monitor_info=True,
        can_redefine_classes=True,
        can_add_method=True,
        can_unrestrictedly_redefine_classes=True,
        can_pop_frames=True,
        can_use_instance_filters=True,
        can_get_source_debug_extension=True,
        can_request_vm_death_event=True,
        can_set_default_stratum=True,
        can_get_instance_info=True,
        can_request_monitor_events=True,
        can_get_monitor_frame_info=True,
        can_use_source_name_filters=True,
        can_get_constant_pool=True,
        can_force_early_return=True,
        reserved22=False,
        reserved23=False,
        reserved24=False,
        reserved25=False,
        reserved26=False,
        reserved27=False,
        reserved28=False,
        reserved29=False,
        reserved30=False,
        reserved31=False,
        reserved32=False,
    )
    await assert_command_roundtrip(
        commands.vm.CapabilitiesNewCommand(),
        caps_new_resp,
        spec=spec,
    )

    # 18. RedefineClasses Command
    await assert_command_roundtrip(
        commands.vm.RedefineClassesCommand(
            classes=[
                commands.vm.RedefineClassesRequest(
                    ref_type=ReferenceTypeID(47),
                    class_bytes=b"\xca\xfe\xba\xbe",
                )
            ]
        ),
        commands.vm.RedefineClassesResponse(),
        spec=spec,
    )

    # 19. SetDefaultStratum Command
    await assert_command_roundtrip(
        commands.vm.SetDefaultStratumCommand(stratum_id="Java"),
        commands.vm.SetDefaultStratumResponse(),
        spec=spec,
    )

    # 20. AllClassesWithGeneric Command
    all_classes_generic_resp = commands.vm.AllClassesWithGenericResponse(
        classes=[
            commands.vm.AllClassesWithGenericEntry(
                ref_type_tag=JdwpTypeTag.CLASS,
                type_id=ReferenceTypeID(48),
                signature="Ljava/util/List;",
                generic_signature="Ljava/util/List<TE;>;",
                status=JdwpClassStatus.VERIFIED,
            )
        ]
    )
    await assert_command_roundtrip(
        commands.vm.AllClassesWithGenericCommand(),
        all_classes_generic_resp,
        spec=spec,
    )

    # 21. InstanceCounts Command
    await assert_command_roundtrip(
        commands.vm.InstanceCountsCommand(ref_types=[ReferenceTypeID(49)]),
        commands.vm.InstanceCountsResponse(counts=[100]),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_class_object_reference_command_set() -> None:
    """Verifies flow and serialization for commands in the ClassObjectReference Command Set (Set 17)."""
    spec = IdSizesSpec.create()

    # 1. ReflectedType Command
    await assert_command_roundtrip(
        commands.class_object_reference.ReflectedTypeCommand(
            class_object=ObjectID(0x11223344)
        ),
        commands.class_object_reference.ReflectedTypeResponse(
            ref_type_tag=JdwpTypeTag.CLASS, type_id=ReferenceTypeID(0x55667788)
        ),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_stack_frame_command_set() -> None:
    """Verifies flow and serialization for commands in the StackFrame Command Set (Set 16)."""
    spec = IdSizesSpec.create()

    thread_id = ThreadID(0x11223344)
    frame_id = FrameID(0x55667788)

    # 1. GetValues Command
    await assert_command_roundtrip(
        commands.stack_frame.GetValuesCommand(
            thread=thread_id,
            frame=frame_id,
            slots=[
                commands.stack_frame.GetValuesRequestSlot(slot=0, sig_byte=JdwpTag.INT),
                commands.stack_frame.GetValuesRequestSlot(
                    slot=1, sig_byte=JdwpTag.OBJECT
                ),
            ],
        ),
        commands.stack_frame.GetValuesResponse(
            values=[
                JdwpValue(tag=JdwpTag.INT, value=42),
                JdwpValue(tag=JdwpTag.OBJECT, value=ObjectID(0xDEADBEEF)),
            ]
        ),
        spec=spec,
    )

    # 2. SetValues Command
    await assert_command_roundtrip(
        commands.stack_frame.SetValuesCommand(
            thread=thread_id,
            frame=frame_id,
            slots=[
                commands.stack_frame.SetValuesRequestSlot(
                    slot=0, value=JdwpValue(tag=JdwpTag.INT, value=42)
                ),
                commands.stack_frame.SetValuesRequestSlot(
                    slot=1,
                    value=JdwpValue(tag=JdwpTag.OBJECT, value=ObjectID(0xDEADBEEF)),
                ),
            ],
        ),
        commands.stack_frame.SetValuesResponse(),
        spec=spec,
    )

    # 3. ThisObject Command
    await assert_command_roundtrip(
        commands.stack_frame.ThisObjectCommand(thread=thread_id, frame=frame_id),
        commands.stack_frame.ThisObjectResponse(
            this_object=TaggedObjectID(
                tag=JdwpTag.OBJECT, object_id=ObjectID(0xFEEDFACE)
            )
        ),
        spec=spec,
    )

    # 4. PopFrames Command
    await assert_command_roundtrip(
        commands.stack_frame.PopFramesCommand(thread=thread_id, frame=frame_id),
        commands.stack_frame.PopFramesResponse(),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_reference_type_command_set() -> None:
    """Verifies flow and serialization for commands in the ReferenceType Command Set (Set 2)."""
    spec = IdSizesSpec.create()

    ref_type = ReferenceTypeID(0x11223344)

    # 1. Signature Command
    await assert_command_roundtrip(
        commands.reference_type.SignatureCommand(ref_type=ref_type),
        commands.reference_type.SignatureResponse(signature="Ljava/lang/String;"),
        spec=spec,
    )

    # 2. ClassLoader Command
    await assert_command_roundtrip(
        commands.reference_type.ClassLoaderCommand(ref_type=ref_type),
        commands.reference_type.ClassLoaderResponse(
            class_loader=ClassLoaderID(0x55667788)
        ),
        spec=spec,
    )

    # 3. Modifiers Command
    await assert_command_roundtrip(
        commands.reference_type.ModifiersCommand(ref_type=ref_type),
        commands.reference_type.ModifiersResponse(mod_bits=0x21),
        spec=spec,
    )

    # 4. Fields Command
    await assert_command_roundtrip(
        commands.reference_type.FieldsCommand(ref_type=ref_type),
        commands.reference_type.FieldsResponse(
            fields=[
                commands.reference_type.FieldsEntry(
                    field_id=FieldID(0xAAAA),
                    name="value",
                    signature="[C",
                    mod_bits=0x12,
                )
            ]
        ),
        spec=spec,
    )

    # 5. Methods Command
    await assert_command_roundtrip(
        commands.reference_type.MethodsCommand(ref_type=ref_type),
        commands.reference_type.MethodsResponse(
            methods=[
                commands.reference_type.MethodsEntry(
                    method_id=MethodID(0xBBBB),
                    name="indexOf",
                    signature="(I)I",
                    mod_bits=0x1,
                )
            ]
        ),
        spec=spec,
    )

    # 6. RefTypeGetValues Command
    await assert_command_roundtrip(
        commands.reference_type.GetValuesCommand(
            ref_type=ref_type, fields=[FieldID(0xAAAA)]
        ),
        commands.reference_type.GetValuesResponse(
            values=[JdwpValue(tag=JdwpTag.INT, value=42)]
        ),
        spec=spec,
    )

    # 7. SourceFile Command
    await assert_command_roundtrip(
        commands.reference_type.SourceFileCommand(ref_type=ref_type),
        commands.reference_type.SourceFileResponse(source_file="String.java"),
        spec=spec,
    )

    # 8. NestedTypes Command
    await assert_command_roundtrip(
        commands.reference_type.NestedTypesCommand(ref_type=ref_type),
        commands.reference_type.NestedTypesResponse(
            nested_types=[
                commands.reference_type.NestedTypesEntry(
                    ref_type_tag=JdwpTypeTag.CLASS,
                    type_id=ReferenceTypeID(0x22334455),
                )
            ]
        ),
        spec=spec,
    )

    # 9. RefTypeStatus Command
    await assert_command_roundtrip(
        commands.reference_type.StatusCommand(ref_type=ref_type),
        commands.reference_type.StatusResponse(
            status=JdwpClassStatus.VERIFIED | JdwpClassStatus.PREPARED
        ),
        spec=spec,
    )

    # 10. Interfaces Command
    await assert_command_roundtrip(
        commands.reference_type.InterfacesCommand(ref_type=ref_type),
        commands.reference_type.InterfacesResponse(interfaces=[InterfaceID(0x9999)]),
        spec=spec,
    )

    # 11. ClassObject Command
    await assert_command_roundtrip(
        commands.reference_type.ClassObjectCommand(ref_type=ref_type),
        commands.reference_type.ClassObjectResponse(class_object=ClassObjectID(0x8888)),
        spec=spec,
    )

    # 12. SourceDebugExtension Command
    await assert_command_roundtrip(
        commands.reference_type.SourceDebugExtensionCommand(ref_type=ref_type),
        commands.reference_type.SourceDebugExtensionResponse(
            extension="KotlinDebugExtension"
        ),
        spec=spec,
    )

    # 13. SignatureWithGeneric Command
    await assert_command_roundtrip(
        commands.reference_type.SignatureWithGenericCommand(ref_type=ref_type),
        commands.reference_type.SignatureWithGenericResponse(
            signature="Ljava/util/List;",
            generic_signature="Ljava/util/List<TE;>;",
        ),
        spec=spec,
    )

    # 14. FieldsWithGeneric Command
    await assert_command_roundtrip(
        commands.reference_type.FieldsWithGenericCommand(ref_type=ref_type),
        commands.reference_type.FieldsWithGenericResponse(
            fields=[
                commands.reference_type.FieldsWithGenericEntry(
                    field_id=FieldID(0xCCCC),
                    name="list",
                    signature="Ljava/util/List;",
                    generic_signature="Ljava/util/List<Ljava/lang/String;>;",
                    mod_bits=0x2,
                )
            ]
        ),
        spec=spec,
    )

    # 15. MethodsWithGeneric Command
    await assert_command_roundtrip(
        commands.reference_type.MethodsWithGenericCommand(ref_type=ref_type),
        commands.reference_type.MethodsWithGenericResponse(
            methods=[
                commands.reference_type.MethodsWithGenericEntry(
                    method_id=MethodID(0xDDDD),
                    name="getList",
                    signature="()Ljava/util/List;",
                    generic_signature="()Ljava/util/List<Ljava/lang/String;>;",
                    mod_bits=0x1,
                )
            ]
        ),
        spec=spec,
    )

    # 16. Instances Command
    await assert_command_roundtrip(
        commands.reference_type.InstancesCommand(ref_type=ref_type, max_instances=5),
        commands.reference_type.InstancesResponse(
            instances=[
                TaggedObjectID(
                    tag=JdwpTag.OBJECT,
                    object_id=ObjectID(0xEEFF),
                )
            ]
        ),
        spec=spec,
    )

    # 17. ClassFileVersion Command
    await assert_command_roundtrip(
        commands.reference_type.ClassFileVersionCommand(ref_type=ref_type),
        commands.reference_type.ClassFileVersionResponse(
            major_version=52, minor_version=0
        ),
        spec=spec,
    )

    # 18. ConstantPool Command
    await assert_command_roundtrip(
        commands.reference_type.ConstantPoolCommand(ref_type=ref_type),
        commands.reference_type.ConstantPoolResponse(bytes=b"\xca\xfe\xba\xbe"),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_class_type_command_set() -> None:
    """Verifies flow and serialization for commands in the ClassType Command Set (Set 3)."""
    spec = IdSizesSpec.create()

    clazz = ClassID(0x11223344)
    thread = ThreadID(0x55667788)
    method = MethodID(0x99AABBCC)

    # 1. Superclass Command
    await assert_command_roundtrip(
        commands.class_type.SuperclassCommand(clazz=clazz),
        commands.class_type.SuperclassResponse(superclass=ClassID(0x22334455)),
        spec=spec,
    )

    # 2. ClassTypeSetValues Command
    await assert_command_roundtrip(
        commands.class_type.SetValuesCommand(
            clazz=clazz,
            slots=[
                commands.class_type.SetValuesRequestSlot(
                    field_id=FieldID(0xAAAA),
                    value=JdwpValue(tag=JdwpTag.INT, value=42),
                )
            ],
        ),
        commands.class_type.SetValuesResponse(),
        spec=spec,
    )

    # 3. ClassTypeInvokeMethod Command
    await assert_command_roundtrip(
        commands.class_type.InvokeMethodCommand(
            clazz=clazz,
            thread=thread,
            method=method,
            arguments=[JdwpValue(tag=JdwpTag.INT, value=100)],
            options=JdwpInvokeOptions.INVOKE_NONVIRTUAL,
        ),
        commands.class_type.InvokeMethodResponse(
            return_value=JdwpValue(tag=JdwpTag.INT, value=200),
            exception=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0)),
        ),
        spec=spec,
    )

    # 4. NewInstance Command
    await assert_command_roundtrip(
        commands.class_type.NewInstanceCommand(
            clazz=clazz,
            thread=thread,
            method=method,
            arguments=[JdwpValue(tag=JdwpTag.INT, value=100)],
            options=JdwpInvokeOptions.INVOKE_NONVIRTUAL,
        ),
        commands.class_type.NewInstanceResponse(
            new_object=TaggedObjectID(
                tag=JdwpTag.OBJECT, object_id=ObjectID(0xDEADBEEF)
            ),
            exception=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0)),
        ),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_array_type_command_set() -> None:
    """Verifies flow and serialization for commands in the ArrayType Command Set (Set 4)."""
    spec = IdSizesSpec.create()

    # 1. NewInstance Command
    await assert_command_roundtrip(
        commands.array_type.NewInstanceCommand(
            arr_type=ArrayTypeID(0x11223344), length=10
        ),
        commands.array_type.NewInstanceResponse(new_array=ArrayObjectID(0x55667788)),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_interface_type_command_set() -> None:
    """Verifies flow and serialization for commands in the InterfaceType Command Set (Set 5)."""
    spec = IdSizesSpec.create()

    # 1. InvokeMethod Command
    await assert_command_roundtrip(
        commands.interface_type.InvokeMethodCommand(
            clazz=InterfaceID(0x11223344),
            thread=ThreadID(0x55667788),
            method=MethodID(0x99AABBCC),
            arguments=[JdwpValue(tag=JdwpTag.INT, value=100)],
            options=JdwpInvokeOptions.INVOKE_NONVIRTUAL,
        ),
        commands.interface_type.InvokeMethodResponse(
            return_value=JdwpValue(tag=JdwpTag.INT, value=200),
            exception=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0)),
        ),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_method_command_set() -> None:
    """Verifies flow and serialization for commands in the Method Command Set (Set 6)."""
    spec = IdSizesSpec.create()

    ref_type = ReferenceTypeID(0x11223344)
    method = MethodID(0x55667788)

    # 1. LineTable Command
    await assert_command_roundtrip(
        commands.method.LineTableCommand(ref_type=ref_type, method=method),
        commands.method.LineTableResponse(
            start_code_index=10,
            end_code_index=100,
            lines=[commands.method.LineTableEntry(code_index=20, line_number=5)],
        ),
        spec=spec,
    )

    # 2. VariableTable Command
    await assert_command_roundtrip(
        commands.method.VariableTableCommand(ref_type=ref_type, method=method),
        commands.method.VariableTableResponse(
            arg_cnt=1,
            slots=[
                commands.method.VariableTableEntry(
                    code_index=10,
                    name="arg0",
                    signature="I",
                    length=90,
                    slot=0,
                )
            ],
        ),
        spec=spec,
    )

    # 3. Bytecodes Command
    await assert_command_roundtrip(
        commands.method.BytecodesCommand(ref_type=ref_type, method=method),
        commands.method.BytecodesResponse(bytecodes=b"\x1b\x3c\x1c\x3d"),
        spec=spec,
    )

    # 4. IsObsolete Command
    await assert_command_roundtrip(
        commands.method.IsObsoleteCommand(ref_type=ref_type, method=method),
        commands.method.IsObsoleteResponse(is_obsolete=False),
        spec=spec,
    )

    # 5. VariableTableWithGeneric Command
    await assert_command_roundtrip(
        commands.method.VariableTableWithGenericCommand(
            ref_type=ref_type, method=method
        ),
        commands.method.VariableTableWithGenericResponse(
            arg_cnt=1,
            slots=[
                commands.method.VariableTableWithGenericEntry(
                    code_index=10,
                    name="listArg",
                    signature="Ljava/util/List;",
                    generic_signature="Ljava/util/List<Ljava/lang/String;>;",
                    length=90,
                    slot=0,
                )
            ],
        ),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_object_reference_command_set() -> None:
    """Verifies flow and serialization for commands in the ObjectReference Command Set (Set 9)."""
    spec = IdSizesSpec.create()

    obj = ObjectID(0x11223344)
    thread = ThreadID(0x55667788)
    clazz = ClassID(0x99AABBCC)
    method = MethodID(0xDDDEEEFF)

    # 1. ReferenceType Command
    await assert_command_roundtrip(
        commands.object_reference.ReferenceTypeCommand(object=obj),
        commands.object_reference.ReferenceTypeResponse(
            ref_type_tag=JdwpTypeTag.CLASS, type_id=ReferenceTypeID(0x7777)
        ),
        spec=spec,
    )

    # 2. GetValues Command
    await assert_command_roundtrip(
        commands.object_reference.GetValuesCommand(
            object=obj, fields=[FieldID(0xAAAA)]
        ),
        commands.object_reference.GetValuesResponse(
            values=[JdwpValue(tag=JdwpTag.INT, value=42)]
        ),
        spec=spec,
    )

    # 3. SetValues Command
    await assert_command_roundtrip(
        commands.object_reference.SetValuesCommand(
            object=obj,
            slots=[
                commands.object_reference.SetValuesRequestSlot(
                    field_id=FieldID(0xAAAA),
                    value=JdwpValue(tag=JdwpTag.INT, value=42),
                )
            ],
        ),
        commands.object_reference.SetValuesResponse(),
        spec=spec,
    )

    # 5. MonitorInfo Command
    await assert_command_roundtrip(
        commands.object_reference.MonitorInfoCommand(object=obj),
        commands.object_reference.MonitorInfoResponse(
            owner=ThreadID(0x8888),
            entry_count=1,
            waiters=[ThreadID(0x9999)],
        ),
        spec=spec,
    )

    # 6. InvokeMethod Command
    await assert_command_roundtrip(
        commands.object_reference.InvokeMethodCommand(
            object=obj,
            thread=thread,
            clazz=clazz,
            method=method,
            arguments=[JdwpValue(tag=JdwpTag.INT, value=100)],
            options=JdwpInvokeOptions.INVOKE_NONVIRTUAL,
        ),
        commands.object_reference.InvokeMethodResponse(
            return_value=JdwpValue(tag=JdwpTag.INT, value=200),
            exception=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0)),
        ),
        spec=spec,
    )

    # 7. DisableCollection Command
    await assert_command_roundtrip(
        commands.object_reference.DisableCollectionCommand(object=obj),
        commands.object_reference.DisableCollectionResponse(),
        spec=spec,
    )

    # 8. EnableCollection Command
    await assert_command_roundtrip(
        commands.object_reference.EnableCollectionCommand(object=obj),
        commands.object_reference.EnableCollectionResponse(),
        spec=spec,
    )

    # 9. IsCollected Command
    await assert_command_roundtrip(
        commands.object_reference.IsCollectedCommand(object=obj),
        commands.object_reference.IsCollectedResponse(is_collected=False),
        spec=spec,
    )

    # 10. ReferringObjects Command
    await assert_command_roundtrip(
        commands.object_reference.ReferringObjectsCommand(object=obj, max_referrers=5),
        commands.object_reference.ReferringObjectsResponse(
            referring_objects=[
                TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0xFEED))
            ]
        ),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_string_reference_command_set() -> None:
    """Verifies flow and serialization for commands in the StringReference Command Set (Set 10)."""
    spec = IdSizesSpec.create()

    # 1. Value Command
    await assert_command_roundtrip(
        commands.string_reference.ValueCommand(string_object=StringID(0x11223344)),
        commands.string_reference.ValueResponse(string_value="Hello World"),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_thread_reference_command_set() -> None:
    """Verifies flow and serialization for commands in the ThreadReference Command Set (Set 11)."""
    spec = IdSizesSpec.create()

    thread = ThreadID(0x11223344)
    ref_type = ReferenceTypeID(0x55667788)
    method = MethodID(0x99AABBCC)
    location = Location(
        type_tag=JdwpTypeTag.CLASS, class_id=ref_type, method_id=method, index=42
    )

    # 1. Name Command
    await assert_command_roundtrip(
        commands.thread_reference.NameCommand(thread=thread),
        commands.thread_reference.NameResponse(thread_name="main"),
        spec=spec,
    )

    # 2. Suspend Command
    await assert_command_roundtrip(
        commands.thread_reference.SuspendCommand(thread=thread),
        commands.thread_reference.SuspendResponse(),
        spec=spec,
    )

    # 3. Resume Command
    await assert_command_roundtrip(
        commands.thread_reference.ResumeCommand(thread=thread),
        commands.thread_reference.ResumeResponse(),
        spec=spec,
    )

    # 4. Status Command
    await assert_command_roundtrip(
        commands.thread_reference.StatusCommand(thread=thread),
        commands.thread_reference.StatusResponse(
            thread_status=JdwpThreadStatus.RUNNING,
            suspend_status=JdwpSuspendStatus.SUSPENDED,
        ),
        spec=spec,
    )

    # 5. ThreadGroup Command
    await assert_command_roundtrip(
        commands.thread_reference.ThreadGroupCommand(thread=thread),
        commands.thread_reference.ThreadGroupResponse(
            thread_group=ThreadGroupID(0x9999)
        ),
        spec=spec,
    )

    # 6. Frames Command
    await assert_command_roundtrip(
        commands.thread_reference.FramesCommand(thread=thread, start_frame=0, length=5),
        commands.thread_reference.FramesResponse(
            frames=[
                commands.thread_reference.FramesEntry(
                    frame_id=FrameID(0xAAAA),
                    location=location,
                )
            ]
        ),
        spec=spec,
    )

    # 7. FrameCount Command
    await assert_command_roundtrip(
        commands.thread_reference.FrameCountCommand(thread=thread),
        commands.thread_reference.FrameCountResponse(frame_count=1),
        spec=spec,
    )

    # 8. OwnedMonitors Command
    await assert_command_roundtrip(
        commands.thread_reference.OwnedMonitorsCommand(thread=thread),
        commands.thread_reference.OwnedMonitorsResponse(
            monitors=[TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0xBBBB))]
        ),
        spec=spec,
    )

    # 9. CurrentContendedMonitor Command
    await assert_command_roundtrip(
        commands.thread_reference.CurrentContendedMonitorCommand(thread=thread),
        commands.thread_reference.CurrentContendedMonitorResponse(
            monitor=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0xCCCC))
        ),
        spec=spec,
    )

    # 10. Stop Command
    await assert_command_roundtrip(
        commands.thread_reference.StopCommand(
            thread=thread, throwable=ObjectID(0xDDDD)
        ),
        commands.thread_reference.StopResponse(),
        spec=spec,
    )

    # 11. Interrupt Command
    await assert_command_roundtrip(
        commands.thread_reference.InterruptCommand(thread=thread),
        commands.thread_reference.InterruptResponse(),
        spec=spec,
    )

    # 12. SuspendCount Command
    await assert_command_roundtrip(
        commands.thread_reference.SuspendCountCommand(thread=thread),
        commands.thread_reference.SuspendCountResponse(suspend_count=1),
        spec=spec,
    )

    # 13. OwnedMonitorsStackDepthInfo Command
    await assert_command_roundtrip(
        commands.thread_reference.OwnedMonitorsStackDepthInfoCommand(thread=thread),
        commands.thread_reference.OwnedMonitorsStackDepthInfoResponse(
            monitors=[
                commands.thread_reference.MonitorStackDepthInfoEntry(
                    monitor=TaggedObjectID(
                        tag=JdwpTag.OBJECT, object_id=ObjectID(0xEEEE)
                    ),
                    stack_depth=2,
                )
            ]
        ),
        spec=spec,
    )

    # 14. ForceEarlyReturn Command
    await assert_command_roundtrip(
        commands.thread_reference.ForceEarlyReturnCommand(
            thread=thread, value=JdwpValue(tag=JdwpTag.INT, value=42)
        ),
        commands.thread_reference.ForceEarlyReturnResponse(),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_thread_group_reference_command_set() -> None:
    """Verifies flow and serialization for commands in the ThreadGroupReference Command Set (Set 12)."""
    spec = IdSizesSpec.create()

    group = ThreadGroupID(0x11223344)

    # 1. Name Command
    await assert_command_roundtrip(
        commands.thread_group_reference.NameCommand(group=group),
        commands.thread_group_reference.NameResponse(group_name="system"),
        spec=spec,
    )

    # 2. Parent Command
    await assert_command_roundtrip(
        commands.thread_group_reference.ParentCommand(group=group),
        commands.thread_group_reference.ParentResponse(
            parent_group=ThreadGroupID(0x55667788)
        ),
        spec=spec,
    )

    # 3. Children Command
    await assert_command_roundtrip(
        commands.thread_group_reference.ChildrenCommand(group=group),
        commands.thread_group_reference.ChildrenResponse(
            child_threads=[ThreadID(0xAAAA)],
            child_groups=[ThreadGroupID(0xBBBB)],
        ),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_array_reference_command_set() -> None:
    """Verifies flow and serialization for commands in the ArrayReference Command Set (Set 13)."""
    spec = IdSizesSpec.create()

    arr = ArrayObjectID(0x11223344)

    # 1. Length Command
    await assert_command_roundtrip(
        commands.array_reference.LengthCommand(array_object=arr),
        commands.array_reference.LengthResponse(array_length=5),
        spec=spec,
    )

    # 2. GetValues Command
    await assert_command_roundtrip(
        commands.array_reference.GetValuesCommand(
            array_object=arr, first_index=0, length=2
        ),
        commands.array_reference.GetValuesResponse(
            values=commands.array_reference.JdwpArrayRegion(
                tag=JdwpTag.INT,
                values=[
                    JdwpValue(tag=JdwpTag.INT, value=100),
                    JdwpValue(tag=JdwpTag.INT, value=200),
                ],
            )
        ),
        spec=spec,
    )

    # 3. SetValues Command
    await assert_command_roundtrip(
        commands.array_reference.SetValuesCommand(
            array_object=arr,
            first_index=0,
            tag=JdwpTag.INT,
            values=[
                JdwpValue(tag=JdwpTag.INT, value=300),
                JdwpValue(tag=JdwpTag.INT, value=400),
            ],
        ),
        commands.array_reference.SetValuesResponse(),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_class_loader_reference_command_set() -> None:
    """Verifies flow and serialization for commands in the ClassLoaderReference Command Set (Set 14)."""
    spec = IdSizesSpec.create()

    # 1. VisibleClasses Command
    await assert_command_roundtrip(
        commands.class_loader_reference.VisibleClassesCommand(
            class_loader=ClassLoaderID(0x11223344)
        ),
        commands.class_loader_reference.VisibleClassesResponse(
            classes=[
                commands.class_loader_reference.VisibleClassesEntry(
                    ref_type_tag=JdwpTypeTag.CLASS,
                    type_id=ReferenceTypeID(0x55667788),
                )
            ]
        ),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_event_request_command_set() -> None:
    """Verifies flow and serialization for commands in the EventRequest Command Set (Set 15)."""
    # 4-byte JDWP spec configuration
    spec = IdSizesSpec.create(
        field_id_size=4,
        method_id_size=4,
        object_id_size=4,
        reference_type_id_size=4,
        frame_id_size=4,
    )

    # 1. ClearAllBreakpoints Command
    await assert_command_roundtrip(
        commands.event_request.ClearAllBreakpointsCommand(),
        commands.event_request.ClearAllBreakpointsResponse(),
        spec=spec,
    )

    # 2. Clear Command
    cmd_clear = commands.event_request.ClearCommand(
        event_kind=JdwpEventKind.BREAKPOINT, request_id=42
    )
    await assert_command_roundtrip(
        cmd_clear, commands.event_request.ClearResponse(), spec=spec
    )

    # 3. Set Command with no modifiers
    cmd_set_simple = commands.event_request.SetCommand(
        event_kind=JdwpEventKind.BREAKPOINT,
        suspend_policy=JdwpSuspendPolicy.NONE,
        modifiers=[],
    )
    await assert_command_roundtrip(
        cmd_set_simple, commands.event_request.SetResponse(request_id=100)
    )

    # 4. Set Command with various modifiers
    modifiers = [
        commands.event_request.CountModifier(count=5),
        commands.event_request.ConditionalModifier(expr_id=123),
        commands.event_request.ThreadOnlyModifier(thread=ObjectID(0x11223344)),
        commands.event_request.ClassOnlyModifier(clazz=ReferenceTypeID(0x55667788)),
        commands.event_request.ClassMatchModifier(class_pattern="java.lang.*"),
        commands.event_request.ClassExcludeModifier(class_pattern="sun.*"),
        commands.event_request.LocationOnlyModifier(
            loc=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x99AABBCC),
                method_id=MethodID(0xDDEEFF00),
                index=0x1122334455667788,
            )
        ),
        commands.event_request.ExceptionOnlyModifier(
            exception_or_null=ReferenceTypeID(0x77889900), caught=True, uncaught=False
        ),
        commands.event_request.FieldOnlyModifier(
            declaring=ReferenceTypeID(0x66554433), field=FieldID(0x221100AA)
        ),
        commands.event_request.StepModifier(
            thread=ObjectID(0xDEADBEEF), size=1, depth=2
        ),
        commands.event_request.InstanceOnlyModifier(instance=ObjectID(0xFEEDFACE)),
        commands.event_request.PlatformThreadsOnlyModifier(),
    ]
    cmd_set_complex = commands.event_request.SetCommand(
        event_kind=JdwpEventKind.BREAKPOINT,
        suspend_policy=JdwpSuspendPolicy.ALL,
        modifiers=modifiers,
    )
    await assert_command_roundtrip(
        cmd_set_complex, commands.event_request.SetResponse(request_id=42), spec=spec
    )


@commands.register_command()
@dataclass
class MockNoResponseCommand(commands.JdwpCommand[None]):
    COMMAND_SET: ClassVar[int] = 99
    COMMAND: ClassVar[int] = 98

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


@pytest.mark.asyncio
async def test_mock_command_set() -> None:
    """Verifies flow for mock commands without response types."""
    await assert_command_roundtrip(
        MockNoResponseCommand(),
        None,
    )


@pytest.mark.asyncio
async def test_composite_events_roundtrip() -> None:
    spec = IdSizesSpec.create(
        field_id_size=4,
        method_id_size=4,
        object_id_size=4,
        reference_type_id_size=4,
        frame_id_size=4,
    )

    events = [
        commands.event.VMStartEvent(request_id=0, thread=ObjectID(0x1111)),
        commands.event.SingleStepEvent(
            request_id=1,
            thread=ObjectID(0x1111),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
        ),
        commands.event.BreakpointEvent(
            request_id=42,
            thread=ObjectID(0x2222),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x3333),
                method_id=MethodID(0x4444),
                index=0x5555666677778888,
            ),
        ),
        commands.event.MethodEntryEvent(
            request_id=2,
            thread=ObjectID(0x1111),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
        ),
        commands.event.MethodExitEvent(
            request_id=3,
            thread=ObjectID(0x1111),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
        ),
        commands.event.MethodExitWithReturnValueEvent(
            request_id=4,
            thread=ObjectID(0x1111),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
            value=JdwpValue(tag=JdwpTag.STRING, value=ObjectID(0x5555)),
        ),
        commands.event.MonitorContendedEnterEvent(
            request_id=5,
            thread=ObjectID(0x1111),
            object=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0x5555)),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
        ),
        commands.event.MonitorContendedEnteredEvent(
            request_id=6,
            thread=ObjectID(0x1111),
            object=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0x5555)),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
        ),
        commands.event.MonitorWaitEvent(
            request_id=7,
            thread=ObjectID(0x1111),
            object=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0x5555)),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
            timeout=1000,
        ),
        commands.event.MonitorWaitedEvent(
            request_id=8,
            thread=ObjectID(0x1111),
            object=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0x5555)),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
            timed_out=True,
        ),
        commands.event.ExceptionEvent(
            request_id=9,
            thread=ObjectID(0x1111),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
            exception=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0x6666)),
            catch_location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x5555,
            ),
        ),
        commands.event.ThreadStartEvent(
            request_id=0,
            thread=ObjectID(0x1111),
        ),
        commands.event.ThreadDeathEvent(
            request_id=10,
            thread=ObjectID(0x1111),
        ),
        commands.event.ClassPrepareEvent(
            request_id=0,
            thread=ObjectID(0x1111),
            ref_type_tag=JdwpTypeTag.CLASS,
            type_id=ReferenceTypeID(0x3333),
            signature="Ljava/lang/String;",
            status=1,
        ),
        commands.event.ClassUnloadEvent(
            request_id=11,
            signature="Ljava/lang/Object;",
        ),
        commands.event.FieldAccessEvent(
            request_id=12,
            thread=ObjectID(0x1111),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
            ref_type_tag=JdwpTypeTag.CLASS,
            type_id=ReferenceTypeID(0x2222),
            field_id=FieldID(0x7777),
            object=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0x5555)),
        ),
        commands.event.FieldModificationEvent(
            request_id=77,
            thread=ObjectID(0x2222),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x3333),
                method_id=MethodID(0x4444),
                index=0x5555666677778888,
            ),
            ref_type_tag=JdwpTypeTag.CLASS,
            type_id=ReferenceTypeID(0x3333),
            field_id=FieldID(0x9999),
            object=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0xAAAA)),
            value_to_be=JdwpValue(tag=JdwpTag.INT, value=42),
        ),
        commands.event.VMDeathEvent(
            request_id=13,
        ),
    ]

    composite = commands.event.CompositeCommand(
        suspend_policy=JdwpSuspendPolicy.ALL,
        events=events,
    )

    await assert_command_roundtrip(composite, None, spec=spec)


@pytest.mark.asyncio
async def test_unexpected_error_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Verifies that receiving a JDWP error not listed in the command's ALLOWED_ERRORS logs a warning."""
    import logging

    spec = IdSizesSpec.create()
    conn, reader, writer = create_mock_connection(spec)

    async with conn:
        # Launch VersionCommand which only allows VM_DEAD and NONE
        task = asyncio.create_task(conn.send_command(commands.vm.VersionCommand()))
        await asyncio.sleep(0)

        # Parse command packet to get ID
        packet = parse_command_packet(writer.buffer)

        # Feed an invalid reply with an unexpected error: INVALID_THREAD (10)
        reply = JdwpReplyPacket(
            id=packet.id,
            flags=0x80,
            error_code=JdwpErrorCode.INVALID_THREAD,
            data=b"",
        )
        reader.feed_data(reply.to_bytes())

        # Assert that executing the task raises JdwpException
        with pytest.raises(JdwpException) as exc_info:
            await task

        assert exc_info.value.error_code == JdwpErrorCode.INVALID_THREAD
        assert exc_info.value.raw_error_code == JdwpErrorCode.INVALID_THREAD.value
        assert isinstance(exc_info.value.command, commands.vm.VersionCommand)
        assert "failed with error: INVALID_THREAD" in str(exc_info.value)

        # Assert that a warning was captured in log
        warnings = [
            rec
            for rec in caplog.records
            if rec.levelno == logging.WARNING
            and "Received unexpected JDWP error code INVALID_THREAD" in rec.message
        ]
        assert len(warnings) == 1
