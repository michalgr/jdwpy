from __future__ import annotations
import struct
from typing import Self
from jdwpy.spec import IdSizesSpec, ObjectID, ReferenceTypeID, FieldID, MethodID, FrameID

class JdwpReader:
    """Helper stream reader to deserialize big-endian JDWP values from a bytes buffer."""
    spec: IdSizesSpec
    data: bytes
    offset: int

    def __init__(self, data: bytes, spec: IdSizesSpec) -> None:
        self.data = data
        self.spec = spec
        self.offset = 0

    @property
    def remaining(self) -> int:
        """Returns the number of remaining bytes in the buffer."""
        return len(self.data) - self.offset

    def read_byte(self) -> int:
        """Reads a single byte."""
        val = self.data[self.offset]
        self.offset += 1
        return val

    def read_boolean(self) -> bool:
        """Reads a boolean."""
        return bool(self.read_byte())

    def read_int(self) -> int:
        """Reads a signed 32-bit integer."""
        val = struct.unpack_from(">i", self.data, self.offset)[0]
        self.offset += 4
        return val

    def read_long(self) -> int:
        """Reads a signed 64-bit integer."""
        val = struct.unpack_from(">q", self.data, self.offset)[0]
        self.offset += 8
        return val

    def read_string(self) -> str:
        """Reads a length-prefixed UTF-8 JDWP string."""
        length = self.read_int()
        val = self.data[self.offset : self.offset + length].decode("utf-8")
        self.offset += length
        return val

    def _read_id(self, struct_obj: struct.Struct) -> int:
        val = struct_obj.unpack_from(self.data, self.offset)[0]
        self.offset += struct_obj.size
        return val

    def read_object_id(self) -> ObjectID:
        """Reads a variable-length object ID."""
        return ObjectID(self._read_id(self.spec.object_id_struct))

    def read_reference_type_id(self) -> ReferenceTypeID:
        """Reads a variable-length reference type ID."""
        return ReferenceTypeID(self._read_id(self.spec.reference_type_id_struct))

    def read_field_id(self) -> FieldID:
        """Reads a variable-length field ID."""
        return FieldID(self._read_id(self.spec.field_id_struct))

    def read_method_id(self) -> MethodID:
        """Reads a variable-length method ID."""
        return MethodID(self._read_id(self.spec.method_id_struct))

    def read_frame_id(self) -> FrameID:
        """Reads a variable-length frame ID."""
        return FrameID(self._read_id(self.spec.frame_id_struct))


class JdwpWriter:
    """Helper stream writer to serialize big-endian JDWP values to an in-memory bytearray."""
    spec: IdSizesSpec
    _buffer: bytearray

    def __init__(self, spec: IdSizesSpec) -> None:
        self.spec = spec
        self._buffer = bytearray()

    def get_bytes(self) -> bytes:
        """Returns the serialized bytes from the internal buffer."""
        return bytes(self._buffer)

    def write_byte(self, val: int) -> Self:
        """Writes a single byte."""
        self._buffer.append(val & 0xFF)
        return self

    def write_boolean(self, val: bool) -> Self:
        """Writes a boolean."""
        self._buffer.append(1 if val else 0)
        return self

    def write_int(self, val: int) -> Self:
        """Writes a signed 32-bit integer."""
        self._buffer.extend(struct.pack(">i", val))
        return self

    def write_long(self, val: int) -> Self:
        """Writes a signed 64-bit integer."""
        self._buffer.extend(struct.pack(">q", val))
        return self

    def write_string(self, val: str) -> Self:
        """Writes a length-prefixed UTF-8 JDWP string."""
        encoded = val.encode("utf-8")
        self.write_int(len(encoded))
        self._buffer.extend(encoded)
        return self

    def write_object_id(self, val: ObjectID) -> Self:
        """Writes a variable-length object ID."""
        self._buffer.extend(self.spec.object_id_struct.pack(val))
        return self

    def write_reference_type_id(self, val: ReferenceTypeID) -> Self:
        """Writes a variable-length reference type ID."""
        self._buffer.extend(self.spec.reference_type_id_struct.pack(val))
        return self

    def write_field_id(self, val: FieldID) -> Self:
        """Writes a variable-length field ID."""
        self._buffer.extend(self.spec.field_id_struct.pack(val))
        return self

    def write_method_id(self, val: MethodID) -> Self:
        """Writes a variable-length method ID."""
        self._buffer.extend(self.spec.method_id_struct.pack(val))
        return self

    def write_frame_id(self, val: FrameID) -> Self:
        """Writes a variable-length frame ID."""
        self._buffer.extend(self.spec.frame_id_struct.pack(val))
        return self
