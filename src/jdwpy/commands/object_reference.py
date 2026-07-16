from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, Self
from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import register_command
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.spec import (
    ObjectID,
    ReferenceTypeID,
    FieldID,
    ThreadID,
    ClassID,
    MethodID,
    TaggedObjectID,
    JdwpValue,
)
from jdwpy.constants import JdwpTypeTag, JdwpInvokeOptions


@dataclass
class ReferenceTypeResponse(JdwpResponse):
    """Represents the response of ObjectReference.ReferenceType command."""

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


@register_command(ReferenceTypeResponse)
@dataclass
class ReferenceTypeCommand(JdwpCommand[ReferenceTypeResponse]):
    """JDWP Command Set 9, Command 1: ObjectReference.ReferenceType."""

    COMMAND_SET: ClassVar[int] = 9
    COMMAND: ClassVar[int] = 1

    object: ObjectID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.object)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(object=reader.read_object_id())


@dataclass
class GetValuesResponse(JdwpResponse):
    """Represents the response of ObjectReference.GetValues command."""

    values: list[JdwpValue]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        values = [reader.read_value() for _ in range(num)]
        return cls(values=values)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.values))
        for v in self.values:
            writer.write_value(v)


@register_command(GetValuesResponse)
@dataclass
class GetValuesCommand(JdwpCommand[GetValuesResponse]):
    """JDWP Command Set 9, Command 2: ObjectReference.GetValues."""

    COMMAND_SET: ClassVar[int] = 9
    COMMAND: ClassVar[int] = 2

    object: ObjectID
    fields: list[FieldID]

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.object)
        writer.write_int(len(self.fields))
        for f in self.fields:
            writer.write_field_id(f)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        object = reader.read_object_id()
        num = reader.read_int()
        fields = [reader.read_field_id() for _ in range(num)]
        return cls(object=object, fields=fields)


@dataclass
class SetValuesRequestSlot:
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
class SetValuesResponse(JdwpResponse):
    """Represents the response of ObjectReference.SetValues command."""

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(SetValuesResponse)
@dataclass
class SetValuesCommand(JdwpCommand[SetValuesResponse]):
    """JDWP Command Set 9, Command 3: ObjectReference.SetValues."""

    COMMAND_SET: ClassVar[int] = 9
    COMMAND: ClassVar[int] = 3

    object: ObjectID
    slots: list[SetValuesRequestSlot]

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.object)
        writer.write_int(len(self.slots))
        for s in self.slots:
            s.serialize(writer)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        object = reader.read_object_id()
        num = reader.read_int()
        slots = [SetValuesRequestSlot.deserialize(reader) for _ in range(num)]
        return cls(object=object, slots=slots)


@dataclass
class MonitorInfoResponse(JdwpResponse):
    """Represents the response of ObjectReference.MonitorInfo command."""

    owner: ThreadID
    entry_count: int
    waiters: list[ThreadID]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        owner = reader.read_thread_id()
        entry_count = reader.read_int()
        num = reader.read_int()
        waiters = [reader.read_thread_id() for _ in range(num)]
        return cls(owner=owner, entry_count=entry_count, waiters=waiters)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.owner)
        writer.write_int(self.entry_count)
        writer.write_int(len(self.waiters))
        for w in self.waiters:
            writer.write_thread_id(w)


@register_command(MonitorInfoResponse)
@dataclass
class MonitorInfoCommand(JdwpCommand[MonitorInfoResponse]):
    """JDWP Command Set 9, Command 5: ObjectReference.MonitorInfo."""

    COMMAND_SET: ClassVar[int] = 9
    COMMAND: ClassVar[int] = 5

    object: ObjectID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.object)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(object=reader.read_object_id())


@dataclass
class InvokeMethodResponse(JdwpResponse):
    """Represents the response of ObjectReference.InvokeMethod command."""

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
    """JDWP Command Set 9, Command 6: ObjectReference.InvokeMethod."""

    COMMAND_SET: ClassVar[int] = 9
    COMMAND: ClassVar[int] = 6

    object: ObjectID
    thread: ThreadID
    clazz: ClassID
    method: MethodID
    arguments: list[JdwpValue]
    options: JdwpInvokeOptions

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.object)
        writer.write_thread_id(self.thread)
        writer.write_class_id(self.clazz)
        writer.write_method_id(self.method)
        writer.write_int(len(self.arguments))
        for arg in self.arguments:
            writer.write_value(arg)
        writer.write_int(self.options)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        object = reader.read_object_id()
        thread = reader.read_thread_id()
        clazz = reader.read_class_id()
        method = reader.read_method_id()
        num = reader.read_int()
        arguments = [reader.read_value() for _ in range(num)]
        options = JdwpInvokeOptions(reader.read_int())
        return cls(
            object=object,
            thread=thread,
            clazz=clazz,
            method=method,
            arguments=arguments,
            options=options,
        )


@dataclass
class DisableCollectionResponse(JdwpResponse):
    """Represents the response of ObjectReference.DisableCollection command."""

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(DisableCollectionResponse)
@dataclass
class DisableCollectionCommand(JdwpCommand[DisableCollectionResponse]):
    """JDWP Command Set 9, Command 7: ObjectReference.DisableCollection."""

    COMMAND_SET: ClassVar[int] = 9
    COMMAND: ClassVar[int] = 7

    object: ObjectID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.object)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(object=reader.read_object_id())


@dataclass
class EnableCollectionResponse(JdwpResponse):
    """Represents the response of ObjectReference.EnableCollection command."""

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(EnableCollectionResponse)
@dataclass
class EnableCollectionCommand(JdwpCommand[EnableCollectionResponse]):
    """JDWP Command Set 9, Command 8: ObjectReference.EnableCollection."""

    COMMAND_SET: ClassVar[int] = 9
    COMMAND: ClassVar[int] = 8

    object: ObjectID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.object)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(object=reader.read_object_id())


@dataclass
class IsCollectedResponse(JdwpResponse):
    """Represents the response of ObjectReference.IsCollected command."""

    is_collected: bool

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(is_collected=reader.read_boolean())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_boolean(self.is_collected)


@register_command(IsCollectedResponse)
@dataclass
class IsCollectedCommand(JdwpCommand[IsCollectedResponse]):
    """JDWP Command Set 9, Command 9: ObjectReference.IsCollected."""

    COMMAND_SET: ClassVar[int] = 9
    COMMAND: ClassVar[int] = 9

    object: ObjectID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.object)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(object=reader.read_object_id())


@dataclass
class ReferringObjectsResponse(JdwpResponse):
    """Represents the response of ObjectReference.ReferringObjects command."""

    referring_objects: list[TaggedObjectID]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        referring_objects = [reader.read_tagged_object() for _ in range(num)]
        return cls(referring_objects=referring_objects)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.referring_objects))
        for r in self.referring_objects:
            writer.write_tagged_object(r)


@register_command(ReferringObjectsResponse)
@dataclass
class ReferringObjectsCommand(JdwpCommand[ReferringObjectsResponse]):
    """JDWP Command Set 9, Command 10: ObjectReference.ReferringObjects."""

    COMMAND_SET: ClassVar[int] = 9
    COMMAND: ClassVar[int] = 10

    object: ObjectID
    max_referrers: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.object)
        writer.write_int(self.max_referrers)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            object=reader.read_object_id(),
            max_referrers=reader.read_int(),
        )
