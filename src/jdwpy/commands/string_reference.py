from __future__ import annotations
from jdwpy.constants import JdwpErrorCode
from dataclasses import dataclass
from typing import ClassVar, Self
from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import register_command
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.spec import StringID


@dataclass
class ValueResponse(JdwpResponse):
    """Represents the response of StringReference.Value command."""

    string_value: str

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(string_value=reader.read_string())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_string(self.string_value)


@register_command(ValueResponse)
@dataclass
class ValueCommand(JdwpCommand[ValueResponse]):
    """JDWP Command Set 10, Command 1: StringReference.Value."""

    COMMAND_SET: ClassVar[int] = 10
    COMMAND: ClassVar[int] = 1
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.INVALID_OBJECT,
            JdwpErrorCode.INVALID_STRING,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    string_object: StringID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_string_id(self.string_object)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(string_object=reader.read_string_id())
