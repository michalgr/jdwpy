from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, Self
from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import register_command
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.spec import ThreadGroupID, ThreadID


@dataclass
class ThreadGroupRefNameResponse(JdwpResponse):
    """Represents the response of ThreadGroupReference.Name command."""

    group_name: str

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(group_name=reader.read_string())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_string(self.group_name)


@register_command(ThreadGroupRefNameResponse)
@dataclass
class ThreadGroupRefNameCommand(JdwpCommand[ThreadGroupRefNameResponse]):
    """JDWP Command Set 12, Command 1: ThreadGroupReference.Name."""

    COMMAND_SET: ClassVar[int] = 12
    COMMAND: ClassVar[int] = 1

    group: ThreadGroupID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_group_id(self.group)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(group=reader.read_thread_group_id())


@dataclass
class ParentResponse(JdwpResponse):
    """Represents the response of ThreadGroupReference.Parent command."""

    parent_group: ThreadGroupID

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(parent_group=reader.read_thread_group_id())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_group_id(self.parent_group)


@register_command(ParentResponse)
@dataclass
class ParentCommand(JdwpCommand[ParentResponse]):
    """JDWP Command Set 12, Command 2: ThreadGroupReference.Parent."""

    COMMAND_SET: ClassVar[int] = 12
    COMMAND: ClassVar[int] = 2

    group: ThreadGroupID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_group_id(self.group)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(group=reader.read_thread_group_id())


@dataclass
class ChildrenResponse(JdwpResponse):
    """Represents the response of ThreadGroupReference.Children command."""

    child_threads: list[ThreadID]
    child_groups: list[ThreadGroupID]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num_threads = reader.read_int()
        child_threads = [reader.read_thread_id() for _ in range(num_threads)]
        num_groups = reader.read_int()
        child_groups = [reader.read_thread_group_id() for _ in range(num_groups)]
        return cls(child_threads=child_threads, child_groups=child_groups)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.child_threads))
        for t in self.child_threads:
            writer.write_thread_id(t)
        writer.write_int(len(self.child_groups))
        for g in self.child_groups:
            writer.write_thread_group_id(g)


@register_command(ChildrenResponse)
@dataclass
class ChildrenCommand(JdwpCommand[ChildrenResponse]):
    """JDWP Command Set 12, Command 3: ThreadGroupReference.Children."""

    COMMAND_SET: ClassVar[int] = 12
    COMMAND: ClassVar[int] = 3

    group: ThreadGroupID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_thread_group_id(self.group)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(group=reader.read_thread_group_id())
