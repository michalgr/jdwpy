from __future__ import annotations
from abc import ABC, abstractmethod
from typing import ClassVar, Self
from jdwpy.constants import JdwpErrorCode
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.spec import IdSizesSpec


class JdwpResponse(ABC):
    """Abstract Base Class representing a JDWP Command Response payload."""

    @classmethod
    @abstractmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        """Parses response payload bytes into a typed response object."""
        pass

    @abstractmethod
    def serialize(self, writer: JdwpWriter) -> None:
        """Serializes response object fields into big-endian bytes."""
        pass

    def to_bytes(self, spec: IdSizesSpec) -> bytes:
        """Helper to serialize response payload directly to bytes."""
        writer = JdwpWriter(spec)
        self.serialize(writer)
        return writer.get_bytes()

    @classmethod
    def from_bytes(cls, data: bytes, spec: IdSizesSpec) -> Self:
        """Helper to deserialize response payload directly from bytes."""
        reader = JdwpReader(data, spec)
        return cls.deserialize(reader)


class JdwpCommand[T: JdwpResponse | None](ABC):
    """Abstract Base Class representing a JDWP Command payload."""

    COMMAND_SET: ClassVar[int]
    COMMAND: ClassVar[int]

    # Restricts allowed error codes for validation checking.
    ALLOWED_ERRORS: ClassVar[frozenset[JdwpErrorCode]] = frozenset([JdwpErrorCode.NONE])

    @abstractmethod
    def serialize(self, writer: JdwpWriter) -> None:
        """Serializes command parameters into big-endian bytes."""
        pass

    @classmethod
    @abstractmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        """Parses command payload bytes into a typed command object."""
        pass

    def to_bytes(self, spec: IdSizesSpec) -> bytes:
        """Helper to serialize command parameters directly to bytes."""
        writer = JdwpWriter(spec)
        self.serialize(writer)
        return writer.get_bytes()

    @classmethod
    def from_bytes(cls, data: bytes, spec: IdSizesSpec) -> Self:
        """Helper to deserialize command parameters directly from bytes."""
        reader = JdwpReader(data, spec)
        return cls.deserialize(reader)
