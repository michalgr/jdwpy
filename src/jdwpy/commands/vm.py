from __future__ import annotations
from jdwpy.constants import JdwpErrorCode
from dataclasses import dataclass
from typing import ClassVar, Self
from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import register_command
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.spec import ObjectID, ReferenceTypeID, ThreadID, ThreadGroupID, StringID
from jdwpy.constants import JdwpTypeTag, JdwpClassStatus


@dataclass
class VersionResponse(JdwpResponse):
    """Represents the response of VirtualMachine.Version command."""

    description: str
    jdwp_major: int
    jdwp_minor: int
    vm_version: str
    vm_name: str

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            description=reader.read_string(),
            jdwp_major=reader.read_int(),
            jdwp_minor=reader.read_int(),
            vm_version=reader.read_string(),
            vm_name=reader.read_string(),
        )

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_string(self.description)
        writer.write_int(self.jdwp_major)
        writer.write_int(self.jdwp_minor)
        writer.write_string(self.vm_version)
        writer.write_string(self.vm_name)


@register_command(VersionResponse)
@dataclass
class VersionCommand(JdwpCommand[VersionResponse]):
    """JDWP Command Set 1, Command 1: VirtualMachine.Version."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 1
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    def serialize(self, writer: JdwpWriter) -> None:
        pass  # Empty payload request

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


@dataclass
class ClassesBySignatureEntry:
    ref_type_tag: JdwpTypeTag
    type_id: ReferenceTypeID
    status: JdwpClassStatus

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_byte(self.ref_type_tag)
        writer.write_reference_type_id(self.type_id)
        writer.write_int(self.status)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            ref_type_tag=JdwpTypeTag(reader.read_byte()),
            type_id=reader.read_reference_type_id(),
            status=JdwpClassStatus(reader.read_int()),
        )


@dataclass
class ClassesBySignatureResponse(JdwpResponse):
    classes: list[ClassesBySignatureEntry]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        entries = []
        for _ in range(num):
            entries.append(ClassesBySignatureEntry.deserialize(reader))
        return cls(classes=entries)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.classes))
        for entry in self.classes:
            entry.serialize(writer)


@register_command(ClassesBySignatureResponse)
@dataclass
class ClassesBySignatureCommand(JdwpCommand[ClassesBySignatureResponse]):
    """JDWP Command Set 1, Command 2: VirtualMachine.ClassesBySignature."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 2
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    signature: str

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_string(self.signature)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(signature=reader.read_string())


@dataclass
class AllClassesEntry:
    ref_type_tag: JdwpTypeTag
    type_id: ReferenceTypeID
    signature: str
    status: JdwpClassStatus

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_byte(self.ref_type_tag)
        writer.write_reference_type_id(self.type_id)
        writer.write_string(self.signature)
        writer.write_int(self.status)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            ref_type_tag=JdwpTypeTag(reader.read_byte()),
            type_id=reader.read_reference_type_id(),
            signature=reader.read_string(),
            status=JdwpClassStatus(reader.read_int()),
        )


@dataclass
class AllClassesResponse(JdwpResponse):
    classes: list[AllClassesEntry]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        entries = []
        for _ in range(num):
            entries.append(AllClassesEntry.deserialize(reader))
        return cls(classes=entries)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.classes))
        for entry in self.classes:
            entry.serialize(writer)


@register_command(AllClassesResponse)
@dataclass
class AllClassesCommand(JdwpCommand[AllClassesResponse]):
    """JDWP Command Set 1, Command 3: VirtualMachine.AllClasses."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 3
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


@dataclass
class AllThreadsResponse(JdwpResponse):
    threads: list[ThreadID]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        threads = [reader.read_thread_id() for _ in range(num)]
        return cls(threads=threads)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.threads))
        for t in self.threads:
            writer.write_thread_id(t)


@register_command(AllThreadsResponse)
@dataclass
class AllThreadsCommand(JdwpCommand[AllThreadsResponse]):
    """JDWP Command Set 1, Command 4: VirtualMachine.AllThreads."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 4
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


@dataclass
class TopLevelThreadGroupsResponse(JdwpResponse):
    groups: list[ThreadGroupID]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        groups = [reader.read_thread_group_id() for _ in range(num)]
        return cls(groups=groups)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.groups))
        for g in self.groups:
            writer.write_thread_group_id(g)


@register_command(TopLevelThreadGroupsResponse)
@dataclass
class TopLevelThreadGroupsCommand(JdwpCommand[TopLevelThreadGroupsResponse]):
    """JDWP Command Set 1, Command 5: VirtualMachine.TopLevelThreadGroups."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 5
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


@dataclass
class DisposeResponse(JdwpResponse):
    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(DisposeResponse)
@dataclass
class DisposeCommand(JdwpCommand[DisposeResponse]):
    """JDWP Command Set 1, Command 6: VirtualMachine.Dispose."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 6
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
        ]
    )

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


@dataclass
class IDSizesResponse(JdwpResponse):
    """Represents the response of VirtualMachine.IDSizes command."""

    field_id_size: int
    method_id_size: int
    object_id_size: int
    reference_type_id_size: int
    frame_id_size: int

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            field_id_size=reader.read_int(),
            method_id_size=reader.read_int(),
            object_id_size=reader.read_int(),
            reference_type_id_size=reader.read_int(),
            frame_id_size=reader.read_int(),
        )

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(self.field_id_size)
        writer.write_int(self.method_id_size)
        writer.write_int(self.object_id_size)
        writer.write_int(self.reference_type_id_size)
        writer.write_int(self.frame_id_size)


@register_command(IDSizesResponse)
@dataclass
class IDSizesCommand(JdwpCommand[IDSizesResponse]):
    """JDWP Command Set 1, Command 7: VirtualMachine.IDSizes."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 7
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    def serialize(self, writer: JdwpWriter) -> None:
        pass  # Empty payload request

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


@dataclass
class SuspendResponse(JdwpResponse):
    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(SuspendResponse)
@dataclass
class SuspendCommand(JdwpCommand[SuspendResponse]):
    """JDWP Command Set 1, Command 8: VirtualMachine.Suspend."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 8
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


@dataclass
class ResumeResponse(JdwpResponse):
    """Represents the response of VirtualMachine.Resume command."""

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(ResumeResponse)
@dataclass
class ResumeCommand(JdwpCommand[ResumeResponse]):
    """JDWP Command Set 1, Command 9: VirtualMachine.Resume."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 9
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
        ]
    )

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


@dataclass
class ExitResponse(JdwpResponse):
    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(ExitResponse)
@dataclass
class ExitCommand(JdwpCommand[ExitResponse]):
    """JDWP Command Set 1, Command 10: VirtualMachine.Exit."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 10
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
        ]
    )

    exit_code: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(self.exit_code)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(exit_code=reader.read_int())


@dataclass
class CreateStringResponse(JdwpResponse):
    string_object: StringID

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(string_object=reader.read_string_id())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_string_id(self.string_object)


@register_command(CreateStringResponse)
@dataclass
class CreateStringCommand(JdwpCommand[CreateStringResponse]):
    """JDWP Command Set 1, Command 11: VirtualMachine.CreateString."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 11
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    utf: str

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_string(self.utf)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(utf=reader.read_string())


@dataclass
class CapabilitiesResponse(JdwpResponse):
    can_watch_field_modification: bool
    can_watch_field_access: bool
    can_get_bytecodes: bool
    can_get_synthetic_attribute: bool
    can_get_owned_monitor_info: bool
    can_get_current_contended_monitor: bool
    can_get_monitor_info: bool

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            can_watch_field_modification=reader.read_boolean(),
            can_watch_field_access=reader.read_boolean(),
            can_get_bytecodes=reader.read_boolean(),
            can_get_synthetic_attribute=reader.read_boolean(),
            can_get_owned_monitor_info=reader.read_boolean(),
            can_get_current_contended_monitor=reader.read_boolean(),
            can_get_monitor_info=reader.read_boolean(),
        )

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_boolean(self.can_watch_field_modification)
        writer.write_boolean(self.can_watch_field_access)
        writer.write_boolean(self.can_get_bytecodes)
        writer.write_boolean(self.can_get_synthetic_attribute)
        writer.write_boolean(self.can_get_owned_monitor_info)
        writer.write_boolean(self.can_get_current_contended_monitor)
        writer.write_boolean(self.can_get_monitor_info)


@register_command(CapabilitiesResponse)
@dataclass
class CapabilitiesCommand(JdwpCommand[CapabilitiesResponse]):
    """JDWP Command Set 1, Command 12: VirtualMachine.Capabilities."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 12
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


@dataclass
class ClassPathsResponse(JdwpResponse):
    base_dir: str
    classpaths: list[str]
    bootclasspaths: list[str]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        base_dir = reader.read_string()
        num_cp = reader.read_int()
        classpaths = [reader.read_string() for _ in range(num_cp)]
        num_bcp = reader.read_int()
        bootclasspaths = [reader.read_string() for _ in range(num_bcp)]
        return cls(
            base_dir=base_dir, classpaths=classpaths, bootclasspaths=bootclasspaths
        )

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_string(self.base_dir)
        writer.write_int(len(self.classpaths))
        for p in self.classpaths:
            writer.write_string(p)
        writer.write_int(len(self.bootclasspaths))
        for p in self.bootclasspaths:
            writer.write_string(p)


@register_command(ClassPathsResponse)
@dataclass
class ClassPathsCommand(JdwpCommand[ClassPathsResponse]):
    """JDWP Command Set 1, Command 13: VirtualMachine.ClassPaths."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 13
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


@dataclass
class DisposeObjectsRequest:
    object_id: ObjectID
    ref_cnt: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.object_id)
        writer.write_int(self.ref_cnt)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            object_id=reader.read_object_id(),
            ref_cnt=reader.read_int(),
        )


@dataclass
class DisposeObjectsResponse(JdwpResponse):
    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(DisposeObjectsResponse)
@dataclass
class DisposeObjectsCommand(JdwpCommand[DisposeObjectsResponse]):
    """JDWP Command Set 1, Command 14: VirtualMachine.DisposeObjects."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 14
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
        ]
    )

    requests: list[DisposeObjectsRequest]

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.requests))
        for req in self.requests:
            req.serialize(writer)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        requests = []
        for _ in range(num):
            requests.append(DisposeObjectsRequest.deserialize(reader))
        return cls(requests=requests)


@dataclass
class HoldEventsResponse(JdwpResponse):
    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(HoldEventsResponse)
@dataclass
class HoldEventsCommand(JdwpCommand[HoldEventsResponse]):
    """JDWP Command Set 1, Command 15: VirtualMachine.HoldEvents."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 15
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
        ]
    )

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


@dataclass
class ReleaseEventsResponse(JdwpResponse):
    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(ReleaseEventsResponse)
@dataclass
class ReleaseEventsCommand(JdwpCommand[ReleaseEventsResponse]):
    """JDWP Command Set 1, Command 16: VirtualMachine.ReleaseEvents."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 16
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
        ]
    )

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


@dataclass
class CapabilitiesNewResponse(JdwpResponse):
    can_watch_field_modification: bool
    can_watch_field_access: bool
    can_get_bytecodes: bool
    can_get_synthetic_attribute: bool
    can_get_owned_monitor_info: bool
    can_get_current_contended_monitor: bool
    can_get_monitor_info: bool
    can_redefine_classes: bool
    can_add_method: bool
    can_unrestrictedly_redefine_classes: bool
    can_pop_frames: bool
    can_use_instance_filters: bool
    can_get_source_debug_extension: bool
    can_request_vm_death_event: bool
    can_set_default_stratum: bool
    can_get_instance_info: bool
    can_request_monitor_events: bool
    can_get_monitor_frame_info: bool
    can_use_source_name_filters: bool
    can_get_constant_pool: bool
    can_force_early_return: bool
    reserved22: bool
    reserved23: bool
    reserved24: bool
    reserved25: bool
    reserved26: bool
    reserved27: bool
    reserved28: bool
    reserved29: bool
    reserved30: bool
    reserved31: bool
    reserved32: bool

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            can_watch_field_modification=reader.read_boolean(),
            can_watch_field_access=reader.read_boolean(),
            can_get_bytecodes=reader.read_boolean(),
            can_get_synthetic_attribute=reader.read_boolean(),
            can_get_owned_monitor_info=reader.read_boolean(),
            can_get_current_contended_monitor=reader.read_boolean(),
            can_get_monitor_info=reader.read_boolean(),
            can_redefine_classes=reader.read_boolean(),
            can_add_method=reader.read_boolean(),
            can_unrestrictedly_redefine_classes=reader.read_boolean(),
            can_pop_frames=reader.read_boolean(),
            can_use_instance_filters=reader.read_boolean(),
            can_get_source_debug_extension=reader.read_boolean(),
            can_request_vm_death_event=reader.read_boolean(),
            can_set_default_stratum=reader.read_boolean(),
            can_get_instance_info=reader.read_boolean(),
            can_request_monitor_events=reader.read_boolean(),
            can_get_monitor_frame_info=reader.read_boolean(),
            can_use_source_name_filters=reader.read_boolean(),
            can_get_constant_pool=reader.read_boolean(),
            can_force_early_return=reader.read_boolean(),
            reserved22=reader.read_boolean(),
            reserved23=reader.read_boolean(),
            reserved24=reader.read_boolean(),
            reserved25=reader.read_boolean(),
            reserved26=reader.read_boolean(),
            reserved27=reader.read_boolean(),
            reserved28=reader.read_boolean(),
            reserved29=reader.read_boolean(),
            reserved30=reader.read_boolean(),
            reserved31=reader.read_boolean(),
            reserved32=reader.read_boolean(),
        )

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_boolean(self.can_watch_field_modification)
        writer.write_boolean(self.can_watch_field_access)
        writer.write_boolean(self.can_get_bytecodes)
        writer.write_boolean(self.can_get_synthetic_attribute)
        writer.write_boolean(self.can_get_owned_monitor_info)
        writer.write_boolean(self.can_get_current_contended_monitor)
        writer.write_boolean(self.can_get_monitor_info)
        writer.write_boolean(self.can_redefine_classes)
        writer.write_boolean(self.can_add_method)
        writer.write_boolean(self.can_unrestrictedly_redefine_classes)
        writer.write_boolean(self.can_pop_frames)
        writer.write_boolean(self.can_use_instance_filters)
        writer.write_boolean(self.can_get_source_debug_extension)
        writer.write_boolean(self.can_request_vm_death_event)
        writer.write_boolean(self.can_set_default_stratum)
        writer.write_boolean(self.can_get_instance_info)
        writer.write_boolean(self.can_request_monitor_events)
        writer.write_boolean(self.can_get_monitor_frame_info)
        writer.write_boolean(self.can_use_source_name_filters)
        writer.write_boolean(self.can_get_constant_pool)
        writer.write_boolean(self.can_force_early_return)
        writer.write_boolean(self.reserved22)
        writer.write_boolean(self.reserved23)
        writer.write_boolean(self.reserved24)
        writer.write_boolean(self.reserved25)
        writer.write_boolean(self.reserved26)
        writer.write_boolean(self.reserved27)
        writer.write_boolean(self.reserved28)
        writer.write_boolean(self.reserved29)
        writer.write_boolean(self.reserved30)
        writer.write_boolean(self.reserved31)
        writer.write_boolean(self.reserved32)


@register_command(CapabilitiesNewResponse)
@dataclass
class CapabilitiesNewCommand(JdwpCommand[CapabilitiesNewResponse]):
    """JDWP Command Set 1, Command 17: VirtualMachine.CapabilitiesNew."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 17
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


@dataclass
class RedefineClassesRequest:
    ref_type: ReferenceTypeID
    class_bytes: bytes

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)
        writer.write_int(len(self.class_bytes))
        for b in self.class_bytes:
            writer.write_byte(b)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        ref_type = reader.read_reference_type_id()
        num_bytes = reader.read_int()
        class_bytes = bytes(reader.read_byte() for _ in range(num_bytes))
        return cls(ref_type=ref_type, class_bytes=class_bytes)


@dataclass
class RedefineClassesResponse(JdwpResponse):
    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(RedefineClassesResponse)
@dataclass
class RedefineClassesCommand(JdwpCommand[RedefineClassesResponse]):
    """JDWP Command Set 1, Command 18: VirtualMachine.RedefineClasses."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 18
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.ADD_METHOD_NOT_IMPLEMENTED,
            JdwpErrorCode.CIRCULAR_CLASS_DEFINITION,
            JdwpErrorCode.CLASS_ATTRIBUTE_CHANGE_NOT_IMPLEMENTED,
            JdwpErrorCode.CLASS_MODIFIERS_CHANGE_NOT_IMPLEMENTED,
            JdwpErrorCode.DELETE_METHOD_NOT_IMPLEMENTED,
            JdwpErrorCode.FAILS_VERIFICATION,
            JdwpErrorCode.HIERARCHY_CHANGE_NOT_IMPLEMENTED,
            JdwpErrorCode.INVALID_CLASS,
            JdwpErrorCode.INVALID_CLASS_FORMAT,
            JdwpErrorCode.INVALID_OBJECT,
            JdwpErrorCode.METHOD_MODIFIERS_CHANGE_NOT_IMPLEMENTED,
            JdwpErrorCode.NAMES_DONT_MATCH,
            JdwpErrorCode.NOT_IMPLEMENTED,
            JdwpErrorCode.SCHEMA_CHANGE_NOT_IMPLEMENTED,
            JdwpErrorCode.UNSUPPORTED_VERSION,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    classes: list[RedefineClassesRequest]

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.classes))
        for item in self.classes:
            item.serialize(writer)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        classes = []
        for _ in range(num):
            classes.append(RedefineClassesRequest.deserialize(reader))
        return cls(classes=classes)


@dataclass
class SetDefaultStratumResponse(JdwpResponse):
    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(SetDefaultStratumResponse)
@dataclass
class SetDefaultStratumCommand(JdwpCommand[SetDefaultStratumResponse]):
    """JDWP Command Set 1, Command 19: VirtualMachine.SetDefaultStratum."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 19
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.NOT_IMPLEMENTED,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    stratum_id: str

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_string(self.stratum_id)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(stratum_id=reader.read_string())


@dataclass
class AllClassesWithGenericEntry:
    ref_type_tag: JdwpTypeTag
    type_id: ReferenceTypeID
    signature: str
    generic_signature: str
    status: JdwpClassStatus

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_byte(self.ref_type_tag)
        writer.write_reference_type_id(self.type_id)
        writer.write_string(self.signature)
        writer.write_string(self.generic_signature)
        writer.write_int(self.status)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            ref_type_tag=JdwpTypeTag(reader.read_byte()),
            type_id=reader.read_reference_type_id(),
            signature=reader.read_string(),
            generic_signature=reader.read_string(),
            status=JdwpClassStatus(reader.read_int()),
        )


@dataclass
class AllClassesWithGenericResponse(JdwpResponse):
    classes: list[AllClassesWithGenericEntry]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        entries = []
        for _ in range(num):
            entries.append(AllClassesWithGenericEntry.deserialize(reader))
        return cls(classes=entries)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.classes))
        for entry in self.classes:
            entry.serialize(writer)


@register_command(AllClassesWithGenericResponse)
@dataclass
class AllClassesWithGenericCommand(JdwpCommand[AllClassesWithGenericResponse]):
    """JDWP Command Set 1, Command 20: VirtualMachine.AllClassesWithGeneric."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 20
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


@dataclass
class InstanceCountsResponse(JdwpResponse):
    counts: list[int]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        counts = [reader.read_long() for _ in range(num)]
        return cls(counts=counts)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.counts))
        for c in self.counts:
            writer.write_long(c)


@register_command(InstanceCountsResponse)
@dataclass
class InstanceCountsCommand(JdwpCommand[InstanceCountsResponse]):
    """JDWP Command Set 1, Command 21: VirtualMachine.InstanceCounts."""

    COMMAND_SET: ClassVar[int] = 1
    COMMAND: ClassVar[int] = 21
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.ILLEGAL_ARGUMENT,
            JdwpErrorCode.NOT_IMPLEMENTED,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    ref_types: list[ReferenceTypeID]

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.ref_types))
        for ref in self.ref_types:
            writer.write_reference_type_id(ref)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        ref_types = [reader.read_reference_type_id() for _ in range(num)]
        return cls(ref_types=ref_types)
