from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, Self
from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import register_command
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.spec import FrameID, ThreadID, TaggedObjectID, JdwpValue
from jdwpy.constants import JdwpTag


@dataclass
class GetValuesRequestSlot:
    slot: int
    sig_byte: JdwpTag

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(self.slot)
        writer.write_byte(self.sig_byte)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            slot=reader.read_int(),
            sig_byte=JdwpTag(reader.read_byte()),
        )


@dataclass
class GetValuesResponse(JdwpResponse):
    """Represents the response of StackFrame.GetValues command."""

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
    """JDWP Command Set 16, Command 1: StackFrame.GetValues."""

    COMMAND_SET: ClassVar[int] = 16
    COMMAND: ClassVar[int] = 1

    thread: ThreadID
    frame: FrameID
    slots: list[GetValuesRequestSlot]

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)
        writer.write_frame_id(self.frame)
        writer.write_int(len(self.slots))
        for s in self.slots:
            s.serialize(writer)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        thread = reader.read_thread_id()
        frame = reader.read_frame_id()
        num = reader.read_int()
        slots = [GetValuesRequestSlot.deserialize(reader) for _ in range(num)]
        return cls(thread=thread, frame=frame, slots=slots)


@dataclass
class SetValuesRequestSlot:
    slot: int
    value: JdwpValue

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(self.slot)
        writer.write_value(self.value)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            slot=reader.read_int(),
            value=reader.read_value(),
        )


@dataclass
class SetValuesResponse(JdwpResponse):
    """Represents the response of StackFrame.SetValues command."""

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(SetValuesResponse)
@dataclass
class SetValuesCommand(JdwpCommand[SetValuesResponse]):
    """JDWP Command Set 16, Command 2: StackFrame.SetValues."""

    COMMAND_SET: ClassVar[int] = 16
    COMMAND: ClassVar[int] = 2

    thread: ThreadID
    frame: FrameID
    slots: list[SetValuesRequestSlot]

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)
        writer.write_frame_id(self.frame)
        writer.write_int(len(self.slots))
        for s in self.slots:
            s.serialize(writer)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        thread = reader.read_thread_id()
        frame = reader.read_frame_id()
        num = reader.read_int()
        slots = [SetValuesRequestSlot.deserialize(reader) for _ in range(num)]
        return cls(thread=thread, frame=frame, slots=slots)


@dataclass
class ThisObjectResponse(JdwpResponse):
    """Represents the response of StackFrame.ThisObject command."""

    this_object: TaggedObjectID

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(this_object=reader.read_tagged_object())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_tagged_object(self.this_object)


@register_command(ThisObjectResponse)
@dataclass
class ThisObjectCommand(JdwpCommand[ThisObjectResponse]):
    """JDWP Command Set 16, Command 3: StackFrame.ThisObject."""

    COMMAND_SET: ClassVar[int] = 16
    COMMAND: ClassVar[int] = 3

    thread: ThreadID
    frame: FrameID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)
        writer.write_frame_id(self.frame)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            thread=reader.read_thread_id(),
            frame=reader.read_frame_id(),
        )


@dataclass
class PopFramesResponse(JdwpResponse):
    """Represents the response of StackFrame.PopFrames command."""

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(PopFramesResponse)
@dataclass
class PopFramesCommand(JdwpCommand[PopFramesResponse]):
    """JDWP Command Set 16, Command 4: StackFrame.PopFrames."""

    COMMAND_SET: ClassVar[int] = 16
    COMMAND: ClassVar[int] = 4

    thread: ThreadID
    frame: FrameID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)
        writer.write_frame_id(self.frame)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            thread=reader.read_thread_id(),
            frame=reader.read_frame_id(),
        )
