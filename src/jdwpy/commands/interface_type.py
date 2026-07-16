from __future__ import annotations
from jdwpy.constants import JdwpErrorCode
from dataclasses import dataclass
from typing import ClassVar, Self
from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import register_command
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.spec import (
    InterfaceID,
    MethodID,
    ThreadID,
    TaggedObjectID,
    JdwpValue,
)
from jdwpy.constants import JdwpInvokeOptions


@dataclass
class InvokeMethodResponse(JdwpResponse):
    """Represents the response of InterfaceType.InvokeMethod command."""

    return_value: JdwpValue
    exception: TaggedObjectID

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            return_value=reader.read_value(),
            exception=reader.read_tagged_object(),
        )

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_value(self.return_value)
        writer.write_tagged_object(self.exception)


@register_command(InvokeMethodResponse)
@dataclass
class InvokeMethodCommand(JdwpCommand[InvokeMethodResponse]):
    """JDWP Command Set 5, Command 1: InterfaceType.InvokeMethod."""

    COMMAND_SET: ClassVar[int] = 5
    COMMAND: ClassVar[int] = 1
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
            JdwpErrorCode.INVALID_CLASS,
            JdwpErrorCode.INVALID_METHODID,
            JdwpErrorCode.INVALID_OBJECT,
            JdwpErrorCode.INVALID_THREAD,
            JdwpErrorCode.THREAD_NOT_SUSPENDED,
            JdwpErrorCode.VM_DEAD,
        ]
    )

    clazz: InterfaceID
    thread: ThreadID
    method: MethodID
    arguments: list[JdwpValue]
    options: JdwpInvokeOptions

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_interface_id(self.clazz)
        writer.write_thread_id(self.thread)
        writer.write_method_id(self.method)
        writer.write_int(len(self.arguments))
        for arg in self.arguments:
            writer.write_value(arg)
        writer.write_int(self.options)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        clazz = reader.read_interface_id()
        thread = reader.read_thread_id()
        method = reader.read_method_id()
        num = reader.read_int()
        arguments = [reader.read_value() for _ in range(num)]
        options = JdwpInvokeOptions(reader.read_int())
        return cls(
            clazz=clazz,
            thread=thread,
            method=method,
            arguments=arguments,
            options=options,
        )
