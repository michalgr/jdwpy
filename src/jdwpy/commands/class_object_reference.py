from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, Self
from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import register_command
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.spec import ObjectID, ReferenceTypeID
from jdwpy.constants import JdwpTypeTag


@dataclass
class ReflectedTypeResponse(JdwpResponse):
    """Represents the response of ClassObjectReference.ReflectedType command."""

    ref_type_tag: JdwpTypeTag
    type_id: ReferenceTypeID

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            ref_type_tag=JdwpTypeTag(reader.read_byte()),
            type_id=reader.read_reference_type_id(),
        )

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_byte(self.ref_type_tag)
        writer.write_reference_type_id(self.type_id)


@register_command(ReflectedTypeResponse)
@dataclass
class ReflectedTypeCommand(JdwpCommand[ReflectedTypeResponse]):
    """JDWP Command Set 17, Command 1: ClassObjectReference.ReflectedType."""

    COMMAND_SET: ClassVar[int] = 17
    COMMAND: ClassVar[int] = 1

    class_object: ObjectID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.class_object)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(class_object=reader.read_object_id())
