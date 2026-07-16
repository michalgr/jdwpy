from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Self

from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import register_command
from jdwpy.constants import JdwpEventKind, JdwpSuspendPolicy
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.spec import (
    Location,
    ObjectID,
    ReferenceTypeID,
    FieldID,
)


class EventModifier(ABC):
    """Abstract Base Class representing an event filter modifier."""

    MOD_KIND: ClassVar[int]

    @abstractmethod
    def serialize(self, writer: JdwpWriter) -> None:
        """Serializes modifier fields into big-endian bytes."""
        pass

    @classmethod
    @abstractmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        """Parses modifier bytes into a typed modifier object."""
        pass


@dataclass
class CountModifier(EventModifier):
    """Limits the report of an event to occur at most once after a specific number of occurrences."""

    MOD_KIND: ClassVar[int] = 1
    count: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(self.count)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(count=reader.read_int())


@dataclass
class ConditionalModifier(EventModifier):
    """Filters events based on an expression evaluation (Reserved/unused in standard VM)."""

    MOD_KIND: ClassVar[int] = 2
    expr_id: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(self.expr_id)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(expr_id=reader.read_int())


@dataclass
class ThreadOnlyModifier(EventModifier):
    """Restricts reported events to those that occur in a specific thread."""

    MOD_KIND: ClassVar[int] = 3
    thread: ObjectID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(thread=reader.read_object_id())


@dataclass
class ClassOnlyModifier(EventModifier):
    """Restricts reported events to those in a specific class and its subtypes."""

    MOD_KIND: ClassVar[int] = 4
    clazz: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.clazz)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(clazz=reader.read_reference_type_id())


@dataclass
class ClassMatchModifier(EventModifier):
    """Restricts reported events to classes whose name matches a pattern (Regex string)."""

    MOD_KIND: ClassVar[int] = 5
    class_pattern: str

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_string(self.class_pattern)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(class_pattern=reader.read_string())


@dataclass
class ClassExcludeModifier(EventModifier):
    """Restricts reported events to classes whose name does NOT match a pattern (Regex string)."""

    MOD_KIND: ClassVar[int] = 6
    class_pattern: str

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_string(self.class_pattern)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(class_pattern=reader.read_string())


@dataclass
class LocationOnlyModifier(EventModifier):
    """Restricts reported events to those that occur at a specific Location."""

    MOD_KIND: ClassVar[int] = 7
    loc: Location

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_location(self.loc)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(loc=reader.read_location())


@dataclass
class ExceptionOnlyModifier(EventModifier):
    """Restricts reported exception events by exception type and catch status."""

    MOD_KIND: ClassVar[int] = 8
    exception_or_null: ReferenceTypeID
    caught: bool
    uncaught: bool

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.exception_or_null)
        writer.write_boolean(self.caught)
        writer.write_boolean(self.uncaught)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            exception_or_null=reader.read_reference_type_id(),
            caught=reader.read_boolean(),
            uncaught=reader.read_boolean(),
        )


@dataclass
class FieldOnlyModifier(EventModifier):
    """Restricts reported events to access or modification of a specific field."""

    MOD_KIND: ClassVar[int] = 9
    declaring: ReferenceTypeID
    field: FieldID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.declaring)
        writer.write_field_id(self.field)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            declaring=reader.read_reference_type_id(),
            field=reader.read_field_id(),
        )


@dataclass
class StepModifier(EventModifier):
    """Restricts reported step events to specific size and depth constraints."""

    MOD_KIND: ClassVar[int] = 10
    thread: ObjectID
    size: int
    depth: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.thread)
        writer.write_int(self.size)
        writer.write_int(self.depth)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            thread=reader.read_object_id(),
            size=reader.read_int(),
            depth=reader.read_int(),
        )


@dataclass
class InstanceOnlyModifier(EventModifier):
    """Restricts reported events to those occurring within a specific object instance."""

    MOD_KIND: ClassVar[int] = 11
    instance: ObjectID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_object_id(self.instance)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(instance=reader.read_object_id())


@dataclass
class PlatformThreadsOnlyModifier(EventModifier):
    """Excludes virtual threads from THREAD_START and THREAD_END events."""

    MOD_KIND: ClassVar[int] = 14

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()


_MODIFIER_CLASSES: dict[int, type[EventModifier]] = {
    1: CountModifier,
    2: ConditionalModifier,
    3: ThreadOnlyModifier,
    4: ClassOnlyModifier,
    5: ClassMatchModifier,
    6: ClassExcludeModifier,
    7: LocationOnlyModifier,
    8: ExceptionOnlyModifier,
    9: FieldOnlyModifier,
    10: StepModifier,
    11: InstanceOnlyModifier,
    14: PlatformThreadsOnlyModifier,
}


def deserialize_modifier(reader: JdwpReader) -> EventModifier:
    """Helper to parse a single EventModifier dynamically based on its modKind byte."""
    mod_kind = reader.read_byte()
    cls = _MODIFIER_CLASSES.get(mod_kind)
    if cls is None:
        raise ValueError(f"Unknown modifier kind: {mod_kind}")
    return cls.deserialize(reader)


def serialize_modifier(writer: JdwpWriter, modifier: EventModifier) -> None:
    """Helper to serialize a single EventModifier by prefixing its MOD_KIND tag."""
    writer.write_byte(modifier.MOD_KIND)
    modifier.serialize(writer)


@dataclass
class SetResponse(JdwpResponse):
    """Represents the response of EventRequest.Set command containing the requestID."""

    request_id: int

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(request_id=reader.read_int())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(self.request_id)


@register_command(SetResponse)
@dataclass
class SetCommand(JdwpCommand[SetResponse]):
    """JDWP Command Set 15, Command 1: EventRequest.Set."""

    COMMAND_SET: ClassVar[int] = 15
    COMMAND: ClassVar[int] = 1

    event_kind: JdwpEventKind
    suspend_policy: JdwpSuspendPolicy
    modifiers: list[EventModifier]

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_byte(self.event_kind)
        writer.write_byte(self.suspend_policy)
        writer.write_int(len(self.modifiers))
        for mod in self.modifiers:
            serialize_modifier(writer, mod)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        event_kind = JdwpEventKind(reader.read_byte())
        suspend_policy = JdwpSuspendPolicy(reader.read_byte())
        num_modifiers = reader.read_int()
        modifiers = []
        for _ in range(num_modifiers):
            modifiers.append(deserialize_modifier(reader))
        return cls(
            event_kind=event_kind,
            suspend_policy=suspend_policy,
            modifiers=modifiers,
        )


@dataclass
class ClearResponse(JdwpResponse):
    """Represents the response of EventRequest.Clear command."""

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(ClearResponse)
@dataclass
class ClearCommand(JdwpCommand[ClearResponse]):
    """JDWP Command Set 15, Command 2: EventRequest.Clear."""

    COMMAND_SET: ClassVar[int] = 15
    COMMAND: ClassVar[int] = 2

    event_kind: JdwpEventKind
    request_id: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_byte(self.event_kind)
        writer.write_int(self.request_id)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            event_kind=JdwpEventKind(reader.read_byte()),
            request_id=reader.read_int(),
        )


@dataclass
class ClearAllBreakpointsResponse(JdwpResponse):
    """Represents the response of EventRequest.ClearAllBreakpoints command."""

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(ClearAllBreakpointsResponse)
@dataclass
class ClearAllBreakpointsCommand(JdwpCommand[ClearAllBreakpointsResponse]):
    """JDWP Command Set 15, Command 3: EventRequest.ClearAllBreakpoints."""

    COMMAND_SET: ClassVar[int] = 15
    COMMAND: ClassVar[int] = 3

    def serialize(self, writer: JdwpWriter) -> None:
        pass

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()
