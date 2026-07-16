from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, Self
import asyncio
import pytest
from jdwpy.constants import (
    JdwpErrorCode,
    JdwpEventKind,
    JdwpSuspendPolicy,
    JdwpTypeTag,
    JdwpTag,
    JdwpClassStatus,
    JdwpInvokeOptions,
)
from jdwpy.spec import (
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
    Location,
    TaggedObjectID,
    JdwpValue,
    ThreadID,
    ThreadGroupID,
    StringID,
)
from jdwpy.packet import JdwpPacket, JdwpCommandPacket, JdwpReplyPacket
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.commands import (
    StringReferenceValueCommand,
    StringReferenceValueResponse,
    ObjectRefReferenceTypeCommand,
    ObjectRefReferenceTypeResponse,
    ObjectRefGetValuesCommand,
    ObjectRefGetValuesResponse,
    ObjectRefSetValuesCommand,
    ObjectRefSetValuesResponse,
    ObjectRefSetValuesRequestSlot,
    MonitorInfoCommand,
    MonitorInfoResponse,
    ObjectRefInvokeMethodCommand,
    ObjectRefInvokeMethodResponse,
    DisableCollectionCommand,
    DisableCollectionResponse,
    EnableCollectionCommand,
    EnableCollectionResponse,
    IsCollectedCommand,
    IsCollectedResponse,
    ReferringObjectsCommand,
    ReferringObjectsResponse,
    LineTableCommand,
    LineTableResponse,
    LineTableEntry,
    VariableTableCommand,
    VariableTableResponse,
    VariableTableEntry,
    BytecodesCommand,
    BytecodesResponse,
    IsObsoleteCommand,
    IsObsoleteResponse,
    VariableTableWithGenericCommand,
    VariableTableWithGenericResponse,
    VariableTableWithGenericEntry,
    InterfaceTypeInvokeMethodCommand,
    InterfaceTypeInvokeMethodResponse,
    ArrayTypeNewInstanceCommand,
    ArrayTypeNewInstanceResponse,
    SuperclassCommand,
    SuperclassResponse,
    ClassTypeSetValuesCommand,
    ClassTypeSetValuesResponse,
    ClassTypeSetValuesRequestSlot,
    ClassTypeInvokeMethodCommand,
    ClassTypeInvokeMethodResponse,
    NewInstanceCommand,
    NewInstanceResponse,
    SignatureCommand,
    SignatureResponse,
    ClassLoaderCommand,
    ClassLoaderResponse,
    ModifiersCommand,
    ModifiersResponse,
    FieldsCommand,
    FieldsResponse,
    FieldsEntry,
    MethodsCommand,
    MethodsResponse,
    MethodsEntry,
    RefTypeGetValuesCommand,
    RefTypeGetValuesResponse,
    SourceFileCommand,
    SourceFileResponse,
    NestedTypesCommand,
    NestedTypesResponse,
    NestedTypesEntry,
    RefTypeStatusCommand,
    RefTypeStatusResponse,
    InterfacesCommand,
    InterfacesResponse,
    ClassObjectCommand,
    ClassObjectResponse,
    SourceDebugExtensionCommand,
    SourceDebugExtensionResponse,
    SignatureWithGenericCommand,
    SignatureWithGenericResponse,
    FieldsWithGenericCommand,
    FieldsWithGenericResponse,
    FieldsWithGenericEntry,
    MethodsWithGenericCommand,
    MethodsWithGenericResponse,
    MethodsWithGenericEntry,
    InstancesCommand,
    InstancesResponse,
    ClassFileVersionCommand,
    ClassFileVersionResponse,
    ConstantPoolCommand,
    ConstantPoolResponse,
    GetValuesCommand,
    GetValuesResponse,
    GetValuesRequestSlot,
    SetValuesCommand,
    SetValuesResponse,
    SetValuesRequestSlot,
    ThisObjectCommand,
    ThisObjectResponse,
    PopFramesCommand,
    PopFramesResponse,
    ReflectedTypeCommand,
    ReflectedTypeResponse,
    get_command_class,
    get_response_class,
    register_command,
    VersionCommand,
    VersionResponse,
    IDSizesCommand,
    IDSizesResponse,
    JdwpCommand,
    JdwpResponse,
    SetCommand,
    SetResponse,
    ClearCommand,
    ClearResponse,
    ClearAllBreakpointsCommand,
    ClearAllBreakpointsResponse,
    CountModifier,
    ConditionalModifier,
    ThreadOnlyModifier,
    ClassOnlyModifier,
    ClassMatchModifier,
    ClassExcludeModifier,
    LocationOnlyModifier,
    ExceptionOnlyModifier,
    FieldOnlyModifier,
    StepModifier,
    InstanceOnlyModifier,
    PlatformThreadsOnlyModifier,
    CompositeCommand,
    VMStartEvent,
    SingleStepEvent,
    BreakpointEvent,
    MethodEntryEvent,
    MethodExitEvent,
    MethodExitWithReturnValueEvent,
    MonitorContendedEnterEvent,
    ClassesBySignatureCommand,
    ClassesBySignatureResponse,
    ClassesBySignatureEntry,
    AllClassesCommand,
    AllClassesResponse,
    AllClassesEntry,
    AllThreadsCommand,
    AllThreadsResponse,
    TopLevelThreadGroupsCommand,
    TopLevelThreadGroupsResponse,
    DisposeCommand,
    DisposeResponse,
    SuspendCommand,
    SuspendResponse,
    ResumeCommand,
    ResumeResponse,
    ExitCommand,
    ExitResponse,
    CreateStringCommand,
    CreateStringResponse,
    CapabilitiesCommand,
    CapabilitiesResponse,
    ClassPathsCommand,
    ClassPathsResponse,
    DisposeObjectsCommand,
    DisposeObjectsResponse,
    DisposeObjectsRequest,
    HoldEventsCommand,
    HoldEventsResponse,
    ReleaseEventsCommand,
    ReleaseEventsResponse,
    CapabilitiesNewCommand,
    CapabilitiesNewResponse,
    RedefineClassesCommand,
    RedefineClassesResponse,
    RedefineClassesRequest,
    SetDefaultStratumCommand,
    SetDefaultStratumResponse,
    AllClassesWithGenericCommand,
    AllClassesWithGenericResponse,
    AllClassesWithGenericEntry,
    InstanceCountsCommand,
    InstanceCountsResponse,
    MonitorContendedEnteredEvent,
    MonitorWaitEvent,
    MonitorWaitedEvent,
    ExceptionEvent,
    ThreadStartEvent,
    ThreadDeathEvent,
    ClassPrepareEvent,
    ClassUnloadEvent,
    FieldAccessEvent,
    FieldModificationEvent,
    VMDeathEvent,
)

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


async def assert_command_roundtrip[T: JdwpResponse | None](
    command: JdwpCommand[T],
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
        response_class = get_response_class(command.__class__)
        assert (response_class is None) == (expected_response is None)

        if response_class is not None:
            assert expected_response is not None
            serialized_response = expected_response.to_bytes(conn.spec)
            feed_reply(reader, packet.id, serialized_response)

        response = await task

        # Verify the returned response equals expected_response
        assert response == expected_response

        # Verify dynamic spec updates when IDSizesResponse is received
        if isinstance(response, IDSizesResponse):
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
    assert get_command_class(1, 1) is VersionCommand
    assert get_command_class(1, 7) is IDSizesCommand
    assert get_command_class(99, 98) is MockNoResponseCommand
    assert get_command_class(99, 99) is None


@pytest.mark.asyncio
async def test_virtual_machine_command_set() -> None:
    """Verifies flow and serialization for commands in the VirtualMachine Command Set (Set 1)."""
    spec = IdSizesSpec.create()

    # 1. Version Command
    resp_version = VersionResponse(
        description="JVM 14.0",
        jdwp_major=1,
        jdwp_minor=6,
        vm_version="14.0.1",
        vm_name="OpenJDK",
    )
    await assert_command_roundtrip(VersionCommand(), resp_version, spec=spec)

    # 2. IDSizes Command & spec update verification
    resp_ids = IDSizesResponse(
        field_id_size=4,
        method_id_size=4,
        object_id_size=8,
        reference_type_id_size=8,
        frame_id_size=8,
    )
    await assert_command_roundtrip(IDSizesCommand(), resp_ids, spec=spec)

    # 3. ClassesBySignature Command
    classes_by_sig_resp = ClassesBySignatureResponse(
        classes=[
            ClassesBySignatureEntry(
                ref_type_tag=JdwpTypeTag.CLASS,
                type_id=ReferenceTypeID(42),
                status=JdwpClassStatus.VERIFIED,
            )
        ]
    )
    await assert_command_roundtrip(
        ClassesBySignatureCommand(signature="Ljava/lang/String;"),
        classes_by_sig_resp,
        spec=spec,
    )

    # 4. AllClasses Command
    all_classes_resp = AllClassesResponse(
        classes=[
            AllClassesEntry(
                ref_type_tag=JdwpTypeTag.CLASS,
                type_id=ReferenceTypeID(42),
                signature="Ljava/lang/String;",
                status=JdwpClassStatus.VERIFIED,
            )
        ]
    )
    await assert_command_roundtrip(
        AllClassesCommand(),
        all_classes_resp,
        spec=spec,
    )

    # 5. AllThreads Command
    all_threads_resp = AllThreadsResponse(threads=[ThreadID(42), ThreadID(43)])
    await assert_command_roundtrip(
        AllThreadsCommand(),
        all_threads_resp,
        spec=spec,
    )

    # 6. TopLevelThreadGroups Command
    top_level_groups_resp = TopLevelThreadGroupsResponse(groups=[ThreadGroupID(44)])
    await assert_command_roundtrip(
        TopLevelThreadGroupsCommand(),
        top_level_groups_resp,
        spec=spec,
    )

    # 7. Dispose Command
    await assert_command_roundtrip(
        DisposeCommand(),
        DisposeResponse(),
        spec=spec,
    )

    # 8. Suspend Command
    await assert_command_roundtrip(
        SuspendCommand(),
        SuspendResponse(),
        spec=spec,
    )

    # 9. Resume Command
    await assert_command_roundtrip(
        ResumeCommand(),
        ResumeResponse(),
        spec=spec,
    )

    # 10. Exit Command
    await assert_command_roundtrip(
        ExitCommand(exit_code=42),
        ExitResponse(),
        spec=spec,
    )

    # 11. CreateString Command
    await assert_command_roundtrip(
        CreateStringCommand(utf="hello"),
        CreateStringResponse(string_object=StringID(45)),
        spec=spec,
    )

    # 12. Capabilities Command
    caps_resp = CapabilitiesResponse(
        can_watch_field_modification=True,
        can_watch_field_access=True,
        can_get_bytecodes=True,
        can_get_synthetic_attribute=True,
        can_get_owned_monitor_info=True,
        can_get_current_contended_monitor=True,
        can_get_monitor_info=True,
    )
    await assert_command_roundtrip(
        CapabilitiesCommand(),
        caps_resp,
        spec=spec,
    )

    # 13. ClassPaths Command
    class_paths_resp = ClassPathsResponse(
        base_dir="/base",
        classpaths=["/cp1"],
        bootclasspaths=["/bcp1"],
    )
    await assert_command_roundtrip(
        ClassPathsCommand(),
        class_paths_resp,
        spec=spec,
    )

    # 14. DisposeObjects Command
    await assert_command_roundtrip(
        DisposeObjectsCommand(
            requests=[DisposeObjectsRequest(object_id=ObjectID(46), ref_cnt=2)]
        ),
        DisposeObjectsResponse(),
        spec=spec,
    )

    # 15. HoldEvents Command
    await assert_command_roundtrip(
        HoldEventsCommand(),
        HoldEventsResponse(),
        spec=spec,
    )

    # 16. ReleaseEvents Command
    await assert_command_roundtrip(
        ReleaseEventsCommand(),
        ReleaseEventsResponse(),
        spec=spec,
    )

    # 17. CapabilitiesNew Command
    caps_new_resp = CapabilitiesNewResponse(
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
        CapabilitiesNewCommand(),
        caps_new_resp,
        spec=spec,
    )

    # 18. RedefineClasses Command
    await assert_command_roundtrip(
        RedefineClassesCommand(
            classes=[
                RedefineClassesRequest(
                    ref_type=ReferenceTypeID(47),
                    class_bytes=b"\xca\xfe\xba\xbe",
                )
            ]
        ),
        RedefineClassesResponse(),
        spec=spec,
    )

    # 19. SetDefaultStratum Command
    await assert_command_roundtrip(
        SetDefaultStratumCommand(stratum_id="Java"),
        SetDefaultStratumResponse(),
        spec=spec,
    )

    # 20. AllClassesWithGeneric Command
    all_classes_generic_resp = AllClassesWithGenericResponse(
        classes=[
            AllClassesWithGenericEntry(
                ref_type_tag=JdwpTypeTag.CLASS,
                type_id=ReferenceTypeID(48),
                signature="Ljava/util/List;",
                generic_signature="Ljava/util/List<TE;>;",
                status=JdwpClassStatus.VERIFIED,
            )
        ]
    )
    await assert_command_roundtrip(
        AllClassesWithGenericCommand(),
        all_classes_generic_resp,
        spec=spec,
    )

    # 21. InstanceCounts Command
    await assert_command_roundtrip(
        InstanceCountsCommand(ref_types=[ReferenceTypeID(49)]),
        InstanceCountsResponse(counts=[100]),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_class_object_reference_command_set() -> None:
    """Verifies flow and serialization for commands in the ClassObjectReference Command Set (Set 17)."""
    spec = IdSizesSpec.create()

    # 1. ReflectedType Command
    await assert_command_roundtrip(
        ReflectedTypeCommand(class_object=ObjectID(0x11223344)),
        ReflectedTypeResponse(
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
        GetValuesCommand(
            thread=thread_id,
            frame=frame_id,
            slots=[
                GetValuesRequestSlot(slot=0, sig_byte=JdwpTag.INT),
                GetValuesRequestSlot(slot=1, sig_byte=JdwpTag.OBJECT),
            ],
        ),
        GetValuesResponse(
            values=[
                JdwpValue(tag=JdwpTag.INT, value=42),
                JdwpValue(tag=JdwpTag.OBJECT, value=ObjectID(0xDEADBEEF)),
            ]
        ),
        spec=spec,
    )

    # 2. SetValues Command
    await assert_command_roundtrip(
        SetValuesCommand(
            thread=thread_id,
            frame=frame_id,
            slots=[
                SetValuesRequestSlot(
                    slot=0, value=JdwpValue(tag=JdwpTag.INT, value=42)
                ),
                SetValuesRequestSlot(
                    slot=1,
                    value=JdwpValue(tag=JdwpTag.OBJECT, value=ObjectID(0xDEADBEEF)),
                ),
            ],
        ),
        SetValuesResponse(),
        spec=spec,
    )

    # 3. ThisObject Command
    await assert_command_roundtrip(
        ThisObjectCommand(thread=thread_id, frame=frame_id),
        ThisObjectResponse(
            this_object=TaggedObjectID(
                tag=JdwpTag.OBJECT, object_id=ObjectID(0xFEEDFACE)
            )
        ),
        spec=spec,
    )

    # 4. PopFrames Command
    await assert_command_roundtrip(
        PopFramesCommand(thread=thread_id, frame=frame_id),
        PopFramesResponse(),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_reference_type_command_set() -> None:
    """Verifies flow and serialization for commands in the ReferenceType Command Set (Set 2)."""
    spec = IdSizesSpec.create()

    ref_type = ReferenceTypeID(0x11223344)

    # 1. Signature Command
    await assert_command_roundtrip(
        SignatureCommand(ref_type=ref_type),
        SignatureResponse(signature="Ljava/lang/String;"),
        spec=spec,
    )

    # 2. ClassLoader Command
    await assert_command_roundtrip(
        ClassLoaderCommand(ref_type=ref_type),
        ClassLoaderResponse(class_loader=ClassLoaderID(0x55667788)),
        spec=spec,
    )

    # 3. Modifiers Command
    await assert_command_roundtrip(
        ModifiersCommand(ref_type=ref_type),
        ModifiersResponse(mod_bits=0x21),
        spec=spec,
    )

    # 4. Fields Command
    await assert_command_roundtrip(
        FieldsCommand(ref_type=ref_type),
        FieldsResponse(
            fields=[
                FieldsEntry(
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
        MethodsCommand(ref_type=ref_type),
        MethodsResponse(
            methods=[
                MethodsEntry(
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
        RefTypeGetValuesCommand(ref_type=ref_type, fields=[FieldID(0xAAAA)]),
        RefTypeGetValuesResponse(values=[JdwpValue(tag=JdwpTag.INT, value=42)]),
        spec=spec,
    )

    # 7. SourceFile Command
    await assert_command_roundtrip(
        SourceFileCommand(ref_type=ref_type),
        SourceFileResponse(source_file="String.java"),
        spec=spec,
    )

    # 8. NestedTypes Command
    await assert_command_roundtrip(
        NestedTypesCommand(ref_type=ref_type),
        NestedTypesResponse(
            nested_types=[
                NestedTypesEntry(
                    ref_type_tag=JdwpTypeTag.CLASS,
                    type_id=ReferenceTypeID(0x22334455),
                )
            ]
        ),
        spec=spec,
    )

    # 9. RefTypeStatus Command
    await assert_command_roundtrip(
        RefTypeStatusCommand(ref_type=ref_type),
        RefTypeStatusResponse(
            status=JdwpClassStatus.VERIFIED | JdwpClassStatus.PREPARED
        ),
        spec=spec,
    )

    # 10. Interfaces Command
    await assert_command_roundtrip(
        InterfacesCommand(ref_type=ref_type),
        InterfacesResponse(interfaces=[InterfaceID(0x9999)]),
        spec=spec,
    )

    # 11. ClassObject Command
    await assert_command_roundtrip(
        ClassObjectCommand(ref_type=ref_type),
        ClassObjectResponse(class_object=ClassObjectID(0x8888)),
        spec=spec,
    )

    # 12. SourceDebugExtension Command
    await assert_command_roundtrip(
        SourceDebugExtensionCommand(ref_type=ref_type),
        SourceDebugExtensionResponse(extension="KotlinDebugExtension"),
        spec=spec,
    )

    # 13. SignatureWithGeneric Command
    await assert_command_roundtrip(
        SignatureWithGenericCommand(ref_type=ref_type),
        SignatureWithGenericResponse(
            signature="Ljava/util/List;",
            generic_signature="Ljava/util/List<TE;>;",
        ),
        spec=spec,
    )

    # 14. FieldsWithGeneric Command
    await assert_command_roundtrip(
        FieldsWithGenericCommand(ref_type=ref_type),
        FieldsWithGenericResponse(
            fields=[
                FieldsWithGenericEntry(
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
        MethodsWithGenericCommand(ref_type=ref_type),
        MethodsWithGenericResponse(
            methods=[
                MethodsWithGenericEntry(
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
        InstancesCommand(ref_type=ref_type, max_instances=5),
        InstancesResponse(
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
        ClassFileVersionCommand(ref_type=ref_type),
        ClassFileVersionResponse(major_version=52, minor_version=0),
        spec=spec,
    )

    # 18. ConstantPool Command
    await assert_command_roundtrip(
        ConstantPoolCommand(ref_type=ref_type),
        ConstantPoolResponse(bytes=b"\xca\xfe\xba\xbe"),
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
        SuperclassCommand(clazz=clazz),
        SuperclassResponse(superclass=ClassID(0x22334455)),
        spec=spec,
    )

    # 2. ClassTypeSetValues Command
    await assert_command_roundtrip(
        ClassTypeSetValuesCommand(
            clazz=clazz,
            slots=[
                ClassTypeSetValuesRequestSlot(
                    field_id=FieldID(0xAAAA),
                    value=JdwpValue(tag=JdwpTag.INT, value=42),
                )
            ],
        ),
        ClassTypeSetValuesResponse(),
        spec=spec,
    )

    # 3. ClassTypeInvokeMethod Command
    await assert_command_roundtrip(
        ClassTypeInvokeMethodCommand(
            clazz=clazz,
            thread=thread,
            method=method,
            arguments=[JdwpValue(tag=JdwpTag.INT, value=100)],
            options=JdwpInvokeOptions.INVOKE_NONVIRTUAL,
        ),
        ClassTypeInvokeMethodResponse(
            return_value=JdwpValue(tag=JdwpTag.INT, value=200),
            exception=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0)),
        ),
        spec=spec,
    )

    # 4. NewInstance Command
    await assert_command_roundtrip(
        NewInstanceCommand(
            clazz=clazz,
            thread=thread,
            method=method,
            arguments=[JdwpValue(tag=JdwpTag.INT, value=100)],
            options=JdwpInvokeOptions.INVOKE_NONVIRTUAL,
        ),
        NewInstanceResponse(
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
        ArrayTypeNewInstanceCommand(arr_type=ArrayTypeID(0x11223344), length=10),
        ArrayTypeNewInstanceResponse(new_array=ArrayObjectID(0x55667788)),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_interface_type_command_set() -> None:
    """Verifies flow and serialization for commands in the InterfaceType Command Set (Set 5)."""
    spec = IdSizesSpec.create()

    # 1. InvokeMethod Command
    await assert_command_roundtrip(
        InterfaceTypeInvokeMethodCommand(
            clazz=InterfaceID(0x11223344),
            thread=ThreadID(0x55667788),
            method=MethodID(0x99AABBCC),
            arguments=[JdwpValue(tag=JdwpTag.INT, value=100)],
            options=JdwpInvokeOptions.INVOKE_NONVIRTUAL,
        ),
        InterfaceTypeInvokeMethodResponse(
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
        LineTableCommand(ref_type=ref_type, method=method),
        LineTableResponse(
            start_code_index=10,
            end_code_index=100,
            lines=[LineTableEntry(code_index=20, line_number=5)],
        ),
        spec=spec,
    )

    # 2. VariableTable Command
    await assert_command_roundtrip(
        VariableTableCommand(ref_type=ref_type, method=method),
        VariableTableResponse(
            arg_cnt=1,
            slots=[
                VariableTableEntry(
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
        BytecodesCommand(ref_type=ref_type, method=method),
        BytecodesResponse(bytecodes=b"\x1b\x3c\x1c\x3d"),
        spec=spec,
    )

    # 4. IsObsolete Command
    await assert_command_roundtrip(
        IsObsoleteCommand(ref_type=ref_type, method=method),
        IsObsoleteResponse(is_obsolete=False),
        spec=spec,
    )

    # 5. VariableTableWithGeneric Command
    await assert_command_roundtrip(
        VariableTableWithGenericCommand(ref_type=ref_type, method=method),
        VariableTableWithGenericResponse(
            arg_cnt=1,
            slots=[
                VariableTableWithGenericEntry(
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
        ObjectRefReferenceTypeCommand(object=obj),
        ObjectRefReferenceTypeResponse(
            ref_type_tag=JdwpTypeTag.CLASS, type_id=ReferenceTypeID(0x7777)
        ),
        spec=spec,
    )

    # 2. GetValues Command
    await assert_command_roundtrip(
        ObjectRefGetValuesCommand(object=obj, fields=[FieldID(0xAAAA)]),
        ObjectRefGetValuesResponse(values=[JdwpValue(tag=JdwpTag.INT, value=42)]),
        spec=spec,
    )

    # 3. SetValues Command
    await assert_command_roundtrip(
        ObjectRefSetValuesCommand(
            object=obj,
            slots=[
                ObjectRefSetValuesRequestSlot(
                    field_id=FieldID(0xAAAA),
                    value=JdwpValue(tag=JdwpTag.INT, value=42),
                )
            ],
        ),
        ObjectRefSetValuesResponse(),
        spec=spec,
    )

    # 5. MonitorInfo Command
    await assert_command_roundtrip(
        MonitorInfoCommand(object=obj),
        MonitorInfoResponse(
            owner=ThreadID(0x8888),
            entry_count=1,
            waiters=[ThreadID(0x9999)],
        ),
        spec=spec,
    )

    # 6. InvokeMethod Command
    await assert_command_roundtrip(
        ObjectRefInvokeMethodCommand(
            object=obj,
            thread=thread,
            clazz=clazz,
            method=method,
            arguments=[JdwpValue(tag=JdwpTag.INT, value=100)],
            options=JdwpInvokeOptions.INVOKE_NONVIRTUAL,
        ),
        ObjectRefInvokeMethodResponse(
            return_value=JdwpValue(tag=JdwpTag.INT, value=200),
            exception=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0)),
        ),
        spec=spec,
    )

    # 7. DisableCollection Command
    await assert_command_roundtrip(
        DisableCollectionCommand(object=obj),
        DisableCollectionResponse(),
        spec=spec,
    )

    # 8. EnableCollection Command
    await assert_command_roundtrip(
        EnableCollectionCommand(object=obj),
        EnableCollectionResponse(),
        spec=spec,
    )

    # 9. IsCollected Command
    await assert_command_roundtrip(
        IsCollectedCommand(object=obj),
        IsCollectedResponse(is_collected=False),
        spec=spec,
    )

    # 10. ReferringObjects Command
    await assert_command_roundtrip(
        ReferringObjectsCommand(object=obj, max_referrers=5),
        ReferringObjectsResponse(
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
        StringReferenceValueCommand(string_object=StringID(0x11223344)),
        StringReferenceValueResponse(string_value="Hello World"),
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
        ClearAllBreakpointsCommand(),
        ClearAllBreakpointsResponse(),
        spec=spec,
    )

    # 2. Clear Command
    cmd_clear = ClearCommand(event_kind=JdwpEventKind.BREAKPOINT, request_id=42)
    await assert_command_roundtrip(cmd_clear, ClearResponse(), spec=spec)

    # 3. Set Command with no modifiers
    cmd_set_simple = SetCommand(
        event_kind=JdwpEventKind.BREAKPOINT,
        suspend_policy=JdwpSuspendPolicy.NONE,
        modifiers=[],
    )
    await assert_command_roundtrip(cmd_set_simple, SetResponse(request_id=100))

    # 4. Set Command with various modifiers
    modifiers = [
        CountModifier(count=5),
        ConditionalModifier(expr_id=123),
        ThreadOnlyModifier(thread=ObjectID(0x11223344)),
        ClassOnlyModifier(clazz=ReferenceTypeID(0x55667788)),
        ClassMatchModifier(class_pattern="java.lang.*"),
        ClassExcludeModifier(class_pattern="sun.*"),
        LocationOnlyModifier(
            loc=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x99AABBCC),
                method_id=MethodID(0xDDEEFF00),
                index=0x1122334455667788,
            )
        ),
        ExceptionOnlyModifier(
            exception_or_null=ReferenceTypeID(0x77889900), caught=True, uncaught=False
        ),
        FieldOnlyModifier(
            declaring=ReferenceTypeID(0x66554433), field=FieldID(0x221100AA)
        ),
        StepModifier(thread=ObjectID(0xDEADBEEF), size=1, depth=2),
        InstanceOnlyModifier(instance=ObjectID(0xFEEDFACE)),
        PlatformThreadsOnlyModifier(),
    ]
    cmd_set_complex = SetCommand(
        event_kind=JdwpEventKind.BREAKPOINT,
        suspend_policy=JdwpSuspendPolicy.ALL,
        modifiers=modifiers,
    )
    await assert_command_roundtrip(
        cmd_set_complex, SetResponse(request_id=42), spec=spec
    )


@register_command()
@dataclass
class MockNoResponseCommand(JdwpCommand[None]):
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
        VMStartEvent(request_id=0, thread=ObjectID(0x1111)),
        SingleStepEvent(
            request_id=1,
            thread=ObjectID(0x1111),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
        ),
        BreakpointEvent(
            request_id=42,
            thread=ObjectID(0x2222),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x3333),
                method_id=MethodID(0x4444),
                index=0x5555666677778888,
            ),
        ),
        MethodEntryEvent(
            request_id=2,
            thread=ObjectID(0x1111),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
        ),
        MethodExitEvent(
            request_id=3,
            thread=ObjectID(0x1111),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
        ),
        MethodExitWithReturnValueEvent(
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
        MonitorContendedEnterEvent(
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
        MonitorContendedEnteredEvent(
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
        MonitorWaitEvent(
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
        MonitorWaitedEvent(
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
        ExceptionEvent(
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
        ThreadStartEvent(
            request_id=0,
            thread=ObjectID(0x1111),
        ),
        ThreadDeathEvent(
            request_id=10,
            thread=ObjectID(0x1111),
        ),
        ClassPrepareEvent(
            request_id=0,
            thread=ObjectID(0x1111),
            ref_type_tag=JdwpTypeTag.CLASS,
            type_id=ReferenceTypeID(0x3333),
            signature="Ljava/lang/String;",
            status=1,
        ),
        ClassUnloadEvent(
            request_id=11,
            signature="Ljava/lang/Object;",
        ),
        FieldAccessEvent(
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
        FieldModificationEvent(
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
        VMDeathEvent(
            request_id=13,
        ),
    ]

    composite = CompositeCommand(
        suspend_policy=JdwpSuspendPolicy.ALL,
        events=events,
    )

    await assert_command_roundtrip(composite, None, spec=spec)
