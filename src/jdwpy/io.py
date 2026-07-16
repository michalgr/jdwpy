from __future__ import annotations
import struct
from typing import Self, Any
from jdwpy.constants import JdwpTag
from jdwpy.spec import (
    IdSizesSpec,
    ObjectID,
    ReferenceTypeID,
    FieldID,
    MethodID,
    FrameID,
    Location,
    TaggedObjectID,
    JdwpValue,
    ThreadID,
    ThreadGroupID,
    StringID,
    ClassLoaderID,
    ClassObjectID,
    InterfaceID,
    ClassID,
    ArrayTypeID,
    ArrayObjectID,
)


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

    def read_thread_id(self) -> ThreadID:
        """Reads a variable-length thread ID."""
        return ThreadID(self.read_object_id())

    def read_thread_group_id(self) -> ThreadGroupID:
        """Reads a variable-length thread group ID."""
        return ThreadGroupID(self.read_object_id())

    def read_string_id(self) -> StringID:
        """Reads a variable-length string ID."""
        return StringID(self.read_object_id())

    def read_class_loader_id(self) -> ClassLoaderID:
        """Reads a variable-length class loader ID."""
        return ClassLoaderID(self.read_object_id())

    def read_class_object_id(self) -> ClassObjectID:
        """Reads a variable-length class object ID."""
        return ClassObjectID(self.read_object_id())

    def read_interface_id(self) -> InterfaceID:
        """Reads a variable-length interface ID."""
        return InterfaceID(self.read_object_id())

    def read_class_id(self) -> ClassID:
        """Reads a variable-length class ID."""
        return ClassID(self.read_reference_type_id())

    def read_array_type_id(self) -> ArrayTypeID:
        """Reads a variable-length array type ID."""
        return ArrayTypeID(self.read_reference_type_id())

    def read_array_object_id(self) -> ArrayObjectID:
        """Reads a variable-length array object ID."""
        return ArrayObjectID(self.read_object_id())

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

    def read_location(self) -> Location:
        """Reads a composite Location structure."""
        return Location(
            type_tag=self.read_byte(),
            class_id=self.read_reference_type_id(),
            method_id=self.read_method_id(),
            index=self.read_long(),
        )

    def read_tagged_object(self) -> TaggedObjectID:
        """Reads a JDWP tagged object ID."""
        tag = JdwpTag(self.read_byte())
        object_id = self.read_object_id()
        return TaggedObjectID(tag, object_id)

    def read_value(self) -> JdwpValue:
        """Reads a JDWP value with a preceding tag byte."""
        tag_val = self.read_byte()
        try:
            tag = JdwpTag(tag_val)
        except ValueError:
            raise ValueError(f"Unknown JDWP tag byte: {tag_val}")

        val: Any
        if tag in (
            JdwpTag.ARRAY,
            JdwpTag.OBJECT,
            JdwpTag.STRING,
            JdwpTag.THREAD,
            JdwpTag.THREAD_GROUP,
            JdwpTag.CLASS_LOADER,
            JdwpTag.CLASS_OBJECT,
        ):
            val = self.read_object_id()
        elif tag == JdwpTag.BYTE:
            val = struct.unpack_from(">b", self.data, self.offset)[0]
            self.offset += 1
        elif tag == JdwpTag.CHAR:
            val = struct.unpack_from(">H", self.data, self.offset)[0]
            self.offset += 2
        elif tag == JdwpTag.FLOAT:
            val = struct.unpack_from(">f", self.data, self.offset)[0]
            self.offset += 4
        elif tag == JdwpTag.DOUBLE:
            val = struct.unpack_from(">d", self.data, self.offset)[0]
            self.offset += 8
        elif tag == JdwpTag.INT:
            val = self.read_int()
        elif tag == JdwpTag.LONG:
            val = self.read_long()
        elif tag == JdwpTag.SHORT:
            val = struct.unpack_from(">h", self.data, self.offset)[0]
            self.offset += 2
        elif tag == JdwpTag.VOID:
            val = None
        elif tag == JdwpTag.BOOLEAN:
            val = self.read_boolean()
        else:
            raise ValueError(f"Unsupported JDWP tag: {tag}")

        return JdwpValue(tag, val)


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

    def write_thread_id(self, val: ThreadID) -> Self:
        """Writes a variable-length thread ID."""
        self.write_object_id(ObjectID(val))
        return self

    def write_thread_group_id(self, val: ThreadGroupID) -> Self:
        """Writes a variable-length thread group ID."""
        self.write_object_id(ObjectID(val))
        return self

    def write_string_id(self, val: StringID) -> Self:
        """Writes a variable-length string ID."""
        self.write_object_id(ObjectID(val))
        return self

    def write_class_loader_id(self, val: ClassLoaderID) -> Self:
        """Writes a variable-length class loader ID."""
        self.write_object_id(ObjectID(val))
        return self

    def write_class_object_id(self, val: ClassObjectID) -> Self:
        """Writes a variable-length class object ID."""
        self.write_object_id(ObjectID(val))
        return self

    def write_interface_id(self, val: InterfaceID) -> Self:
        """Writes a variable-length interface ID."""
        self.write_object_id(ObjectID(val))
        return self

    def write_class_id(self, val: ClassID) -> Self:
        """Writes a variable-length class ID."""
        self.write_reference_type_id(ReferenceTypeID(val))
        return self

    def write_array_type_id(self, val: ArrayTypeID) -> Self:
        """Writes a variable-length array type ID."""
        self.write_reference_type_id(ReferenceTypeID(val))
        return self

    def write_array_object_id(self, val: ArrayObjectID) -> Self:
        """Writes a variable-length array object ID."""
        self.write_object_id(ObjectID(val))
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

    def write_location(self, val: Location) -> Self:
        """Writes a composite Location structure."""
        self.write_byte(val.type_tag)
        self.write_reference_type_id(val.class_id)
        self.write_method_id(val.method_id)
        self.write_long(val.index)
        return self

    def write_tagged_object(self, val: TaggedObjectID) -> Self:
        """Writes a JDWP tagged object ID."""
        self.write_byte(val.tag)
        self.write_object_id(val.object_id)
        return self

    def write_value(self, val: JdwpValue) -> Self:
        """Writes a JDWP value with a preceding tag byte."""
        self.write_byte(val.tag)
        tag = val.tag
        if tag in (
            JdwpTag.ARRAY,
            JdwpTag.OBJECT,
            JdwpTag.STRING,
            JdwpTag.THREAD,
            JdwpTag.THREAD_GROUP,
            JdwpTag.CLASS_LOADER,
            JdwpTag.CLASS_OBJECT,
        ):
            self.write_object_id(val.value)
        elif tag == JdwpTag.BYTE:
            self._buffer.extend(struct.pack(">b", val.value))
        elif tag == JdwpTag.CHAR:
            self._buffer.extend(struct.pack(">H", val.value))
        elif tag == JdwpTag.FLOAT:
            self._buffer.extend(struct.pack(">f", val.value))
        elif tag == JdwpTag.DOUBLE:
            self._buffer.extend(struct.pack(">d", val.value))
        elif tag == JdwpTag.INT:
            self.write_int(val.value)
        elif tag == JdwpTag.LONG:
            self.write_long(val.value)
        elif tag == JdwpTag.SHORT:
            self._buffer.extend(struct.pack(">h", val.value))
        elif tag == JdwpTag.VOID:
            pass
        elif tag == JdwpTag.BOOLEAN:
            self.write_boolean(val.value)
        else:
            raise ValueError(f"Unsupported JDWP tag: {tag}")
        return self
