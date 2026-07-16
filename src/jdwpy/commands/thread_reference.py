from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, Self
from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import register_command
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.spec import (
    ThreadID,
    ThreadGroupID,
    FrameID,
    ObjectID,
    TaggedObjectID,
    Location,
    JdwpValue,
)
from jdwpy.constants import JdwpThreadStatus, JdwpSuspendStatus


@dataclass
class ThreadRefNameResponse(JdwpResponse):
    """Represents the response of ThreadReference.Name command."""

    thread_name: str

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(thread_name=reader.read_string())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_string(self.thread_name)


@register_command(ThreadRefNameResponse)
@dataclass
class ThreadRefNameCommand(JdwpCommand[ThreadRefNameResponse]):
    """JDWP Command Set 11, Command 1: ThreadReference.Name."""

    COMMAND_SET: ClassVar[int] = 11
    COMMAND: ClassVar[int] = 1

    thread: ThreadID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(thread=reader.read_thread_id())


@dataclass
class ThreadRefSuspendResponse(JdwpResponse):
    """Represents the response of ThreadReference.Suspend command."""

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(ThreadRefSuspendResponse)
@dataclass
class ThreadRefSuspendCommand(JdwpCommand[ThreadRefSuspendResponse]):
    """JDWP Command Set 11, Command 2: ThreadReference.Suspend."""

    COMMAND_SET: ClassVar[int] = 11
    COMMAND: ClassVar[int] = 2

    thread: ThreadID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(thread=reader.read_thread_id())


@dataclass
class ThreadRefResumeResponse(JdwpResponse):
    """Represents the response of ThreadReference.Resume command."""

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(ThreadRefResumeResponse)
@dataclass
class ThreadRefResumeCommand(JdwpCommand[ThreadRefResumeResponse]):
    """JDWP Command Set 11, Command 3: ThreadReference.Resume."""

    COMMAND_SET: ClassVar[int] = 11
    COMMAND: ClassVar[int] = 3

    thread: ThreadID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(thread=reader.read_thread_id())


@dataclass
class ThreadRefStatusResponse(JdwpResponse):
    """Represents the response of ThreadReference.Status command."""

    thread_status: JdwpThreadStatus
    suspend_status: JdwpSuspendStatus

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            thread_status=JdwpThreadStatus(reader.read_int()),
            suspend_status=JdwpSuspendStatus(reader.read_int()),
        )

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(self.thread_status)
        writer.write_int(self.suspend_status)


@register_command(ThreadRefStatusResponse)
@dataclass
class ThreadRefStatusCommand(JdwpCommand[ThreadRefStatusResponse]):
    """JDWP Command Set 11, Command 4: ThreadReference.Status."""

    COMMAND_SET: ClassVar[int] = 11
    COMMAND: ClassVar[int] = 4

    thread: ThreadID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(thread=reader.read_thread_id())


@dataclass
class ThreadGroupResponse(JdwpResponse):
    """Represents the response of ThreadReference.ThreadGroup command."""

    thread_group: ThreadGroupID

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(thread_group=reader.read_thread_group_id())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_group_id(self.thread_group)


@register_command(ThreadGroupResponse)
@dataclass
class ThreadGroupCommand(JdwpCommand[ThreadGroupResponse]):
    """JDWP Command Set 11, Command 5: ThreadReference.ThreadGroup."""

    COMMAND_SET: ClassVar[int] = 11
    COMMAND: ClassVar[int] = 5

    thread: ThreadID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(thread=reader.read_thread_id())


@dataclass
class FramesEntry:
    frame_id: FrameID
    location: Location

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_frame_id(self.frame_id)
        writer.write_location(self.location)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            frame_id=reader.read_frame_id(),
            location=reader.read_location(),
        )


@dataclass
class FramesResponse(JdwpResponse):
    """Represents the response of ThreadReference.Frames command."""

    frames: list[FramesEntry]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        frames = [FramesEntry.deserialize(reader) for _ in range(num)]
        return cls(frames=frames)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.frames))
        for f in self.frames:
            f.serialize(writer)


@register_command(FramesResponse)
@dataclass
class FramesCommand(JdwpCommand[FramesResponse]):
    """JDWP Command Set 11, Command 6: ThreadReference.Frames."""

    COMMAND_SET: ClassVar[int] = 11
    COMMAND: ClassVar[int] = 6

    thread: ThreadID
    start_frame: int
    length: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)
        writer.write_int(self.start_frame)
        writer.write_int(self.length)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            thread=reader.read_thread_id(),
            start_frame=reader.read_int(),
            length=reader.read_int(),
        )


@dataclass
class FrameCountResponse(JdwpResponse):
    """Represents the response of ThreadReference.FrameCount command."""

    frame_count: int

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(frame_count=reader.read_int())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(self.frame_count)


@register_command(FrameCountResponse)
@dataclass
class FrameCountCommand(JdwpCommand[FrameCountResponse]):
    """JDWP Command Set 11, Command 7: ThreadReference.FrameCount."""

    COMMAND_SET: ClassVar[int] = 11
    COMMAND: ClassVar[int] = 7

    thread: ThreadID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(thread=reader.read_thread_id())


@dataclass
class OwnedMonitorsResponse(JdwpResponse):
    """Represents the response of ThreadReference.OwnedMonitors command."""

    monitors: list[TaggedObjectID]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        monitors = [reader.read_tagged_object() for _ in range(num)]
        return cls(monitors=monitors)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.monitors))
        for m in self.monitors:
            writer.write_tagged_object(m)


@register_command(OwnedMonitorsResponse)
@dataclass
class OwnedMonitorsCommand(JdwpCommand[OwnedMonitorsResponse]):
    """JDWP Command Set 11, Command 8: ThreadReference.OwnedMonitors."""

    COMMAND_SET: ClassVar[int] = 11
    COMMAND: ClassVar[int] = 8

    thread: ThreadID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(thread=reader.read_thread_id())


@dataclass
class CurrentContendedMonitorResponse(JdwpResponse):
    """Represents the response of ThreadReference.CurrentContendedMonitor command."""

    monitor: TaggedObjectID

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(monitor=reader.read_tagged_object())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_tagged_object(self.monitor)


@register_command(CurrentContendedMonitorResponse)
@dataclass
class CurrentContendedMonitorCommand(JdwpCommand[CurrentContendedMonitorResponse]):
    """JDWP Command Set 11, Command 9: ThreadReference.CurrentContendedMonitor."""

    COMMAND_SET: ClassVar[int] = 11
    COMMAND: ClassVar[int] = 9

    thread: ThreadID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(thread=reader.read_thread_id())


@dataclass
class StopResponse(JdwpResponse):
    """Represents the response of ThreadReference.Stop command."""

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(StopResponse)
@dataclass
class StopCommand(JdwpCommand[StopResponse]):
    """JDWP Command Set 11, Command 10: ThreadReference.Stop."""

    COMMAND_SET: ClassVar[int] = 11
    COMMAND: ClassVar[int] = 10

    thread: ThreadID
    throwable: ObjectID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)
        writer.write_object_id(self.throwable)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            thread=reader.read_thread_id(),
            throwable=reader.read_object_id(),
        )


@dataclass
class InterruptResponse(JdwpResponse):
    """Represents the response of ThreadReference.Interrupt command."""

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(InterruptResponse)
@dataclass
class InterruptCommand(JdwpCommand[InterruptResponse]):
    """JDWP Command Set 11, Command 11: ThreadReference.Interrupt."""

    COMMAND_SET: ClassVar[int] = 11
    COMMAND: ClassVar[int] = 11

    thread: ThreadID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(thread=reader.read_thread_id())


@dataclass
class SuspendCountResponse(JdwpResponse):
    """Represents the response of ThreadReference.SuspendCount command."""

    suspend_count: int

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(suspend_count=reader.read_int())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(self.suspend_count)


@register_command(SuspendCountResponse)
@dataclass
class SuspendCountCommand(JdwpCommand[SuspendCountResponse]):
    """JDWP Command Set 11, Command 12: ThreadReference.SuspendCount."""

    COMMAND_SET: ClassVar[int] = 11
    COMMAND: ClassVar[int] = 12

    thread: ThreadID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(thread=reader.read_thread_id())


@dataclass
class MonitorStackDepthInfoEntry:
    monitor: TaggedObjectID
    stack_depth: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_tagged_object(self.monitor)
        writer.write_int(self.stack_depth)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            monitor=reader.read_tagged_object(),
            stack_depth=reader.read_int(),
        )


@dataclass
class OwnedMonitorsStackDepthInfoResponse(JdwpResponse):
    """Represents the response of ThreadReference.OwnedMonitorsStackDepthInfo command."""

    monitors: list[MonitorStackDepthInfoEntry]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        monitors = [MonitorStackDepthInfoEntry.deserialize(reader) for _ in range(num)]
        return cls(monitors=monitors)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.monitors))
        for m in self.monitors:
            m.serialize(writer)


@register_command(OwnedMonitorsStackDepthInfoResponse)
@dataclass
class OwnedMonitorsStackDepthInfoCommand(
    JdwpCommand[OwnedMonitorsStackDepthInfoResponse]
):
    """JDWP Command Set 11, Command 13: ThreadReference.OwnedMonitorsStackDepthInfo."""

    COMMAND_SET: ClassVar[int] = 11
    COMMAND: ClassVar[int] = 13

    thread: ThreadID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(thread=reader.read_thread_id())


@dataclass
class ForceEarlyReturnResponse(JdwpResponse):
    """Represents the response of ThreadReference.ForceEarlyReturn command."""

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls()

    def serialize(self, writer: JdwpWriter) -> None:
        pass


@register_command(ForceEarlyReturnResponse)
@dataclass
class ForceEarlyReturnCommand(JdwpCommand[ForceEarlyReturnResponse]):
    """JDWP Command Set 11, Command 14: ThreadReference.ForceEarlyReturn."""

    COMMAND_SET: ClassVar[int] = 11
    COMMAND: ClassVar[int] = 14

    thread: ThreadID
    value: JdwpValue

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_id(self.thread)
        writer.write_value(self.value)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            thread=reader.read_thread_id(),
            value=reader.read_value(),
        )
