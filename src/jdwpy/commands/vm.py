from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, Self
from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import register_command
from jdwpy.io import JdwpReader, JdwpWriter


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
            vm_name=reader.read_string()
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

    def serialize(self, writer: JdwpWriter) -> None:
        pass  # Empty payload request

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
            frame_id_size=reader.read_int()
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

    def serialize(self, writer: JdwpWriter) -> None:
        pass  # Empty payload request

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()
