from __future__ import annotations
from jdwpy.constants import JdwpErrorCode
from dataclasses import dataclass
from typing import ClassVar, Self
from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import register_command
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.spec import ArrayObjectID, JdwpValue
from jdwpy.constants import JdwpTag


@dataclass
class JdwpArrayRegion:
    """Represents a JDWP arrayregion structure (used in GetValues reply)."""

    tag: JdwpTag
    values: list[JdwpValue]

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_byte(self.tag)
        writer.write_int(len(self.values))
        for val in self.values:
            if self.tag.is_object:
                writer.write_byte(val.tag)
            writer.write_untagged_value(val.tag, val.value)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        tag = JdwpTag(reader.read_byte())
        num = reader.read_int()
        values = []
        for _ in range(num):
            elem_tag = JdwpTag(reader.read_byte()) if tag.is_object else tag
            val = reader.read_untagged_value(elem_tag)
            values.append(JdwpValue(tag=elem_tag, value=val))
        return cls(tag=tag, values=values)


@dataclass
class LengthResponse(JdwpResponse):
    """Represents the response of ArrayReference.Length command."""

    array_length: int

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(array_length=reader.read_int())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(self.array_length)


@register_command(LengthResponse)
@dataclass
class LengthCommand(JdwpCommand[LengthResponse]):
    """JDWP Command Set 13, Command 1: ArrayReference.Length."""

    COMMAND_SET: ClassVar[int] = 13
    COMMAND: ClassVar[int] = 1
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.INVALID_ARRAY,
            JdwpErrorCode.INVALID_OBJECT,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    array_object: ArrayObjectID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_array_object_id(self.array_object)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(array_object=reader.read_array_object_id())


@dataclass
class GetValuesResponse(JdwpResponse):
    """Represents the response of ArrayReference.GetValues command."""

    values: JdwpArrayRegion

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(values=JdwpArrayRegion.deserialize(reader))

    def serialize(self, writer: JdwpWriter) -> None:
        self.values.serialize(writer)


@register_command(GetValuesResponse)
@dataclass
class GetValuesCommand(JdwpCommand[GetValuesResponse]):
    """JDWP Command Set 13, Command 2: ArrayReference.GetValues."""

    COMMAND_SET: ClassVar[int] = 13
    COMMAND: ClassVar[int] = 2
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.INVALID_ARRAY,
            JdwpErrorCode.INVALID_LENGTH,
            JdwpErrorCode.INVALID_OBJECT,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    array_object: ArrayObjectID
    first_index: int
    length: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_array_object_id(self.array_object)
        writer.write_int(self.first_index)
        writer.write_int(self.length)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            array_object=reader.read_array_object_id(),
            first_index=reader.read_int(),
            length=reader.read_int(),
        )


@dataclass
class SetValuesResponse(JdwpResponse):
    """Represents the response of ArrayReference.SetValues command."""

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(SetValuesResponse)
@dataclass
class SetValuesCommand(JdwpCommand[SetValuesResponse]):
    """JDWP Command Set 13, Command 3: ArrayReference.SetValues.

    Note that JDWP SetValues request does not include the signature tag byte or tagged-values.
    Instead, it contains a raw sequence of untagged-values matching the array's component type.
    """

    COMMAND_SET: ClassVar[int] = 13
    COMMAND: ClassVar[int] = 3
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.INVALID_ARRAY,
            JdwpErrorCode.INVALID_LENGTH,
            JdwpErrorCode.INVALID_OBJECT,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    array_object: ArrayObjectID
    first_index: int
    tag: JdwpTag
    values: list[JdwpValue]

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_array_object_id(self.array_object)
        writer.write_int(self.first_index)
        writer.write_int(len(self.values))
        for val in self.values:
            writer.write_untagged_value(self.tag, val.value)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        array_object = reader.read_array_object_id()
        first_index = reader.read_int()
        num = reader.read_int()
        # Since the tag is not on the wire, we fetch/default it from reader context
        tag = getattr(reader, "array_element_tag", JdwpTag.INT)
        values = []
        for _ in range(num):
            val = reader.read_untagged_value(tag)
            values.append(JdwpValue(tag=tag, value=val))
        return cls(
            array_object=array_object,
            first_index=first_index,
            tag=tag,
            values=values,
        )
