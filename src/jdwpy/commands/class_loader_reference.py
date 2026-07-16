from __future__ import annotations
from jdwpy.constants import JdwpErrorCode
from dataclasses import dataclass
from typing import ClassVar, Self
from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import register_command
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.spec import ClassLoaderID, ReferenceTypeID
from jdwpy.constants import JdwpTypeTag


@dataclass
class VisibleClassesEntry:
    ref_type_tag: JdwpTypeTag
    type_id: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_byte(self.ref_type_tag)
        writer.write_reference_type_id(self.type_id)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            ref_type_tag=JdwpTypeTag(reader.read_byte()),
            type_id=reader.read_reference_type_id(),
        )


@dataclass
class VisibleClassesResponse(JdwpResponse):
    """Represents the response of ClassLoaderReference.VisibleClasses command."""

    classes: list[VisibleClassesEntry]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        classes = [VisibleClassesEntry.deserialize(reader) for _ in range(num)]
        return cls(classes=classes)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.classes))
        for c in self.classes:
            c.serialize(writer)


@register_command(VisibleClassesResponse)
@dataclass
class VisibleClassesCommand(JdwpCommand[VisibleClassesResponse]):
    """JDWP Command Set 14, Command 1: ClassLoaderReference.VisibleClasses."""

    COMMAND_SET: ClassVar[int] = 14
    COMMAND: ClassVar[int] = 1
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.INVALID_CLASS_LOADER,
            JdwpErrorCode.INVALID_OBJECT,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    class_loader: ClassLoaderID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_class_loader_id(self.class_loader)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(class_loader=reader.read_class_loader_id())
