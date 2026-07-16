from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, Self
from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import register_command
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.spec import ArrayTypeID, ArrayObjectID


@dataclass
class ArrayTypeNewInstanceResponse(JdwpResponse):
    """Represents the response of ArrayType.NewInstance command."""

    new_array: ArrayObjectID

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(new_array=reader.read_array_object_id())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_array_object_id(self.new_array)


@register_command(ArrayTypeNewInstanceResponse)
@dataclass
class ArrayTypeNewInstanceCommand(JdwpCommand[ArrayTypeNewInstanceResponse]):
    """JDWP Command Set 4, Command 1: ArrayType.NewInstance."""

    COMMAND_SET: ClassVar[int] = 4
    COMMAND: ClassVar[int] = 1

    arr_type: ArrayTypeID
    length: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_array_type_id(self.arr_type)
        writer.write_int(self.length)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            arr_type=reader.read_array_type_id(),
            length=reader.read_int(),
        )
