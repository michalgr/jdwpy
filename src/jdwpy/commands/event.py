from __future__ import annotations
from jdwpy.constants import JdwpErrorCode
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Self

from jdwpy.commands.base import JdwpCommand
from jdwpy.commands.registry import register_command
from jdwpy.constants import (
    JdwpEventKind,
    JdwpSuspendPolicy,
    JdwpTypeTag,
    JdwpClassStatus,
)
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.spec import (
    Location,
    ObjectID,
    ReferenceTypeID,
    FieldID,
    TaggedObjectID,
    JdwpValue,
)


class JdwpEvent(ABC):
    """Abstract Base Class representing a single JDWP event notification."""

    event_kind: ClassVar[JdwpEventKind]
    request_id: int

    @abstractmethod
    def serialize(self, writer: JdwpWriter) -> None:
        """Serializes event fields into big-endian bytes."""
        pass

    @classmethod
    @abstractmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        """Parses event bytes into a concrete JdwpEvent object."""
        pass


@dataclass
class VMStartEvent(JdwpEvent):
    """Notification of initialization of a target VM."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.VM_START
    request_id: int
    thread: ObjectID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(request_id=request_id, thread=reader.read_object_id())


@dataclass
class SingleStepEvent(JdwpEvent):
    """Notification of step completion in the target VM."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.SINGLE_STEP
    request_id: int
    thread: ObjectID
    location: Location

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)
        writer.write_location(self.location)

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(
            request_id=request_id,
            thread=reader.read_object_id(),
            location=reader.read_location(),
        )


@dataclass
class BreakpointEvent(JdwpEvent):
    """Notification of a breakpoint in the target VM."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.BREAKPOINT
    request_id: int
    thread: ObjectID
    location: Location

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)
        writer.write_location(self.location)

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(
            request_id=request_id,
            thread=reader.read_object_id(),
            location=reader.read_location(),
        )


@dataclass
class MethodEntryEvent(JdwpEvent):
    """Notification of a method invocation in the target VM."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.METHOD_ENTRY
    request_id: int
    thread: ObjectID
    location: Location

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)
        writer.write_location(self.location)

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(
            request_id=request_id,
            thread=reader.read_object_id(),
            location=reader.read_location(),
        )


@dataclass
class MethodExitEvent(JdwpEvent):
    """Notification of a method return in the target VM."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.METHOD_EXIT
    request_id: int
    thread: ObjectID
    location: Location

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)
        writer.write_location(self.location)

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(
            request_id=request_id,
            thread=reader.read_object_id(),
            location=reader.read_location(),
        )


@dataclass
class MethodExitWithReturnValueEvent(JdwpEvent):
    """Notification of a method return in the target VM with the return value."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.METHOD_EXIT_WITH_RETURN_VALUE
    request_id: int
    thread: ObjectID
    location: Location
    value: JdwpValue

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)
        writer.write_location(self.location)
        writer.write_value(self.value)

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(
            request_id=request_id,
            thread=reader.read_object_id(),
            location=reader.read_location(),
            value=reader.read_value(),
        )


@dataclass
class MonitorContendedEnterEvent(JdwpEvent):
    """Notification that a thread is attempting to enter a monitor already acquired by another thread."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.MONITOR_CONTENDED_ENTER
    request_id: int
    thread: ObjectID
    object: TaggedObjectID
    location: Location

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)
        writer.write_tagged_object(self.object)
        writer.write_location(self.location)

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(
            request_id=request_id,
            thread=reader.read_object_id(),
            object=reader.read_tagged_object(),
            location=reader.read_location(),
        )


@dataclass
class MonitorContendedEnteredEvent(JdwpEvent):
    """Notification of a thread entering a monitor after waiting for it to be released."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.MONITOR_CONTENDED_ENTERED
    request_id: int
    thread: ObjectID
    object: TaggedObjectID
    location: Location

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)
        writer.write_tagged_object(self.object)
        writer.write_location(self.location)

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(
            request_id=request_id,
            thread=reader.read_object_id(),
            object=reader.read_tagged_object(),
            location=reader.read_location(),
        )


@dataclass
class MonitorWaitEvent(JdwpEvent):
    """Notification of a thread about to wait on a monitor object."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.MONITOR_WAIT
    request_id: int
    thread: ObjectID
    object: TaggedObjectID
    location: Location
    timeout: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)
        writer.write_tagged_object(self.object)
        writer.write_location(self.location)
        writer.write_long(self.timeout)

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(
            request_id=request_id,
            thread=reader.read_object_id(),
            object=reader.read_tagged_object(),
            location=reader.read_location(),
            timeout=reader.read_long(),
        )


@dataclass
class MonitorWaitedEvent(JdwpEvent):
    """Notification that a thread has finished waiting on a monitor object."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.MONITOR_WAITED
    request_id: int
    thread: ObjectID
    object: TaggedObjectID
    location: Location
    timed_out: bool

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)
        writer.write_tagged_object(self.object)
        writer.write_location(self.location)
        writer.write_boolean(self.timed_out)

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(
            request_id=request_id,
            thread=reader.read_object_id(),
            object=reader.read_tagged_object(),
            location=reader.read_location(),
            timed_out=reader.read_boolean(),
        )


@dataclass
class ExceptionEvent(JdwpEvent):
    """Notification of an exception in the target VM."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.EXCEPTION
    request_id: int
    thread: ObjectID
    location: Location
    exception: TaggedObjectID
    catch_location: Location

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)
        writer.write_location(self.location)
        writer.write_tagged_object(self.exception)
        writer.write_location(self.catch_location)

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(
            request_id=request_id,
            thread=reader.read_object_id(),
            location=reader.read_location(),
            exception=reader.read_tagged_object(),
            catch_location=reader.read_location(),
        )


@dataclass
class ThreadStartEvent(JdwpEvent):
    """Notification of a new running thread in the target VM."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.THREAD_START
    request_id: int
    thread: ObjectID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(request_id=request_id, thread=reader.read_object_id())


@dataclass
class ThreadDeathEvent(JdwpEvent):
    """Notification of a completed thread in the target VM."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.THREAD_DEATH
    request_id: int
    thread: ObjectID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(request_id=request_id, thread=reader.read_object_id())


@dataclass
class ClassPrepareEvent(JdwpEvent):
    """Notification of a class prepare in the target VM."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.CLASS_PREPARE
    request_id: int
    thread: ObjectID
    ref_type_tag: JdwpTypeTag
    type_id: ReferenceTypeID
    signature: str
    status: JdwpClassStatus

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)
        writer.write_byte(self.ref_type_tag)
        writer.write_reference_type_id(self.type_id)
        writer.write_string(self.signature)
        writer.write_int(self.status)

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(
            request_id=request_id,
            thread=reader.read_object_id(),
            ref_type_tag=JdwpTypeTag(reader.read_byte()),
            type_id=reader.read_reference_type_id(),
            signature=reader.read_string(),
            status=JdwpClassStatus(reader.read_int()),
        )


@dataclass
class ClassUnloadEvent(JdwpEvent):
    """Notification of a class unload in the target VM."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.CLASS_UNLOAD
    request_id: int
    signature: str

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_string(self.signature)

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(
            request_id=request_id,
            signature=reader.read_string(),
        )


@dataclass
class FieldAccessEvent(JdwpEvent):
    """Notification of a field access in the target VM."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.FIELD_ACCESS
    request_id: int
    thread: ObjectID
    location: Location
    ref_type_tag: JdwpTypeTag
    type_id: ReferenceTypeID
    field_id: FieldID
    object: TaggedObjectID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)
        writer.write_location(self.location)
        writer.write_byte(self.ref_type_tag)
        writer.write_reference_type_id(self.type_id)
        writer.write_field_id(self.field_id)
        writer.write_tagged_object(self.object)

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(
            request_id=request_id,
            thread=reader.read_object_id(),
            location=reader.read_location(),
            ref_type_tag=JdwpTypeTag(reader.read_byte()),
            type_id=reader.read_reference_type_id(),
            field_id=reader.read_field_id(),
            object=reader.read_tagged_object(),
        )


@dataclass
class FieldModificationEvent(JdwpEvent):
    """Notification of a field modification in the target VM."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.FIELD_MODIFICATION
    request_id: int
    thread: ObjectID
    location: Location
    ref_type_tag: JdwpTypeTag
    type_id: ReferenceTypeID
    field_id: FieldID
    object: TaggedObjectID
    value_to_be: JdwpValue

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)
        writer.write_location(self.location)
        writer.write_byte(self.ref_type_tag)
        writer.write_reference_type_id(self.type_id)
        writer.write_field_id(self.field_id)
        writer.write_tagged_object(self.object)
        writer.write_value(self.value_to_be)

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(
            request_id=request_id,
            thread=reader.read_object_id(),
            location=reader.read_location(),
            ref_type_tag=JdwpTypeTag(reader.read_byte()),
            type_id=reader.read_reference_type_id(),
            field_id=reader.read_field_id(),
            object=reader.read_tagged_object(),
            value_to_be=reader.read_value(),
        )


@dataclass
class VMDeathEvent(JdwpEvent):
    """Notification of termination of a target VM."""

    event_kind: ClassVar[JdwpEventKind] = JdwpEventKind.VM_DEATH
    request_id: int

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader, request_id: int) -> Self:
        return cls(request_id=request_id)


_EVENT_CLASSES: dict[JdwpEventKind, type[JdwpEvent]] = {
    JdwpEventKind.VM_START: VMStartEvent,
    JdwpEventKind.SINGLE_STEP: SingleStepEvent,
    JdwpEventKind.BREAKPOINT: BreakpointEvent,
    JdwpEventKind.METHOD_ENTRY: MethodEntryEvent,
    JdwpEventKind.METHOD_EXIT: MethodExitEvent,
    JdwpEventKind.METHOD_EXIT_WITH_RETURN_VALUE: MethodExitWithReturnValueEvent,
    JdwpEventKind.MONITOR_CONTENDED_ENTER: MonitorContendedEnterEvent,
    JdwpEventKind.MONITOR_CONTENDED_ENTERED: MonitorContendedEnteredEvent,
    JdwpEventKind.MONITOR_WAIT: MonitorWaitEvent,
    JdwpEventKind.MONITOR_WAITED: MonitorWaitedEvent,
    JdwpEventKind.EXCEPTION: ExceptionEvent,
    JdwpEventKind.THREAD_START: ThreadStartEvent,
    JdwpEventKind.THREAD_DEATH: ThreadDeathEvent,
    JdwpEventKind.CLASS_PREPARE: ClassPrepareEvent,
    JdwpEventKind.CLASS_UNLOAD: ClassUnloadEvent,
    JdwpEventKind.FIELD_ACCESS: FieldAccessEvent,
    JdwpEventKind.FIELD_MODIFICATION: FieldModificationEvent,
    JdwpEventKind.VM_DEATH: VMDeathEvent,
}


def deserialize_event(reader: JdwpReader) -> JdwpEvent:
    """Helper to parse a single JdwpEvent dynamically based on its eventKind byte."""
    event_kind = JdwpEventKind(reader.read_byte())
    request_id = reader.read_int()
    cls = _EVENT_CLASSES.get(event_kind)
    if cls is None:
        raise ValueError(f"Unknown event kind: {event_kind}")
    return cls.deserialize(reader, request_id)


def serialize_event(writer: JdwpWriter, event: JdwpEvent) -> None:
    """Helper to serialize a single JdwpEvent by prefixing its eventKind byte and request_id."""
    writer.write_byte(event.event_kind)
    writer.write_int(event.request_id)
    event.serialize(writer)


@register_command()
@dataclass
class CompositeCommand(JdwpCommand[None]):
    """JDWP Command Set 64, Command 100: Event.Composite."""

    COMMAND_SET: ClassVar[int] = 64
    COMMAND: ClassVar[int] = 100
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset(
        [
            JdwpErrorCode.NONE,
        ]
    )

    suspend_policy: JdwpSuspendPolicy
    events: list[JdwpEvent]

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_byte(self.suspend_policy)
        writer.write_int(len(self.events))
        for event in self.events:
            serialize_event(writer, event)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        suspend_policy = JdwpSuspendPolicy(reader.read_byte())
        num_events = reader.read_int()
        events = []
        for _ in range(num_events):
            events.append(deserialize_event(reader))
        return cls(suspend_policy=suspend_policy, events=events)
