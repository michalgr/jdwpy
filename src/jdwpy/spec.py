from __future__ import annotations
import struct
from dataclasses import dataclass
from typing import NewType, Self, TYPE_CHECKING

if TYPE_CHECKING:
    from jdwpy.commands.vm import IDSizesResponse

# Strong semantic type aliases for static analysis documentation
ObjectID = NewType("ObjectID", int)
ReferenceTypeID = NewType("ReferenceTypeID", int)
FieldID = NewType("FieldID", int)
MethodID = NewType("MethodID", int)
FrameID = NewType("FrameID", int)

_STRUCT_32 = struct.Struct(">I")
_STRUCT_64 = struct.Struct(">Q")


def _get_struct_for_size(size: int) -> struct.Struct:
    if size == 4:
        return _STRUCT_32
    elif size == 8:
        return _STRUCT_64
    raise ValueError(f"Unsupported ID size: {size}")


@dataclass(frozen=True)
class IdSizesSpec:
    """Tracks and pre-compiles JVM-specific Struct formats for variable length JDWP IDs."""

    field_id_struct: struct.Struct
    method_id_struct: struct.Struct
    object_id_struct: struct.Struct
    reference_type_id_struct: struct.Struct
    frame_id_struct: struct.Struct

    @classmethod
    def create(
        cls,
        field_id_size: int = 8,
        method_id_size: int = 8,
        object_id_size: int = 8,
        reference_type_id_size: int = 8,
        frame_id_size: int = 8,
    ) -> Self:
        return cls(
            field_id_struct=_get_struct_for_size(field_id_size),
            method_id_struct=_get_struct_for_size(method_id_size),
            object_id_struct=_get_struct_for_size(object_id_size),
            reference_type_id_struct=_get_struct_for_size(reference_type_id_size),
            frame_id_struct=_get_struct_for_size(frame_id_size),
        )

    @classmethod
    def from_response(cls, response: IDSizesResponse) -> Self:
        """Constructs an IdSizesSpec from a VirtualMachine.IDSizes response."""
        return cls.create(
            field_id_size=response.field_id_size,
            method_id_size=response.method_id_size,
            object_id_size=response.object_id_size,
            reference_type_id_size=response.reference_type_id_size,
            frame_id_size=response.frame_id_size,
        )
