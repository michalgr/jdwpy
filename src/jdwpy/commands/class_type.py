from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, Self
from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import register_command
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.spec import (
    ClassID,
    FieldID,
    MethodID,
    ThreadID,
    TaggedObjectID,
    JdwpValue,
)
from jdwpy.constants import JdwpInvokeOptions


@dataclass
class SuperclassResponse(JdwpResponse):
    """Represents the response of ClassType.Superclass command."""

    superclass: ClassID

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(superclass=reader.read_class_id())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_class_id(self.superclass)


@register_command(SuperclassResponse)
@dataclass
class SuperclassCommand(JdwpCommand[SuperclassResponse]):
    """JDWP Command Set 3, Command 1: ClassType.Superclass."""

    COMMAND_SET: ClassVar[int] = 3
    COMMAND: ClassVar[int] = 1

    clazz: ClassID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_class_id(self.clazz)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(clazz=reader.read_class_id())


@dataclass
class ClassTypeSetValuesRequestSlot:
    field_id: FieldID
    value: JdwpValue

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_field_id(self.field_id)
        writer.write_value(self.value)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            field_id=reader.read_field_id(),
            value=reader.read_value(),
        )


@dataclass
class ClassTypeSetValuesResponse(JdwpResponse):
    """Represents the response of ClassType.SetValues command."""

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(ClassTypeSetValuesResponse)
@dataclass
class ClassTypeSetValuesCommand(JdwpCommand[ClassTypeSetValuesResponse]):
    """JDWP Command Set 3, Command 2: ClassType.SetValues."""

    COMMAND_SET: ClassVar[int] = 3
    COMMAND: ClassVar[int] = 2

    clazz: ClassID
    slots: list[ClassTypeSetValuesRequestSlot]

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_class_id(self.clazz)
        writer.write_int(len(self.slots))
        for s in self.slots:
            s.serialize(writer)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        clazz = reader.read_class_id()
        num = reader.read_int()
        slots = [ClassTypeSetValuesRequestSlot.deserialize(reader) for _ in range(num)]
        return cls(clazz=clazz, slots=slots)


@dataclass
class ClassTypeInvokeMethodResponse(JdwpResponse):
    """Represents the response of ClassType.InvokeMethod command."""

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


@register_command(ClassTypeInvokeMethodResponse)
@dataclass
class ClassTypeInvokeMethodCommand(JdwpCommand[ClassTypeInvokeMethodResponse]):
    """JDWP Command Set 3, Command 3: ClassType.InvokeMethod."""

    COMMAND_SET: ClassVar[int] = 3
    COMMAND: ClassVar[int] = 3

    clazz: ClassID
    thread: ThreadID
    method: MethodID
    arguments: list[JdwpValue]
    options: JdwpInvokeOptions

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_class_id(self.clazz)
        writer.write_thread_id(self.thread)
        writer.write_method_id(self.method)
        writer.write_int(len(self.arguments))
        for arg in self.arguments:
            writer.write_value(arg)
        writer.write_int(self.options)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        clazz = reader.read_class_id()
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


@dataclass
class NewInstanceResponse(JdwpResponse):
    """Represents the response of ClassType.NewInstance command."""

    new_object: TaggedObjectID
    exception: TaggedObjectID

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            new_object=reader.read_tagged_object(),
            exception=reader.read_tagged_object(),
        )

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_tagged_object(self.new_object)
        writer.write_tagged_object(self.exception)


@register_command(NewInstanceResponse)
@dataclass
class NewInstanceCommand(JdwpCommand[NewInstanceResponse]):
    """JDWP Command Set 3, Command 4: ClassType.NewInstance."""

    COMMAND_SET: ClassVar[int] = 3
    COMMAND: ClassVar[int] = 4

    clazz: ClassID
    thread: ThreadID
    method: MethodID
    arguments: list[JdwpValue]
    options: JdwpInvokeOptions

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_class_id(self.clazz)
        writer.write_thread_id(self.thread)
        writer.write_method_id(self.method)
        writer.write_int(len(self.arguments))
        for arg in self.arguments:
            writer.write_value(arg)
        writer.write_int(self.options)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        clazz = reader.read_class_id()
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
