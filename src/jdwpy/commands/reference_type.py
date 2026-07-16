from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, Self
from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import register_command
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.spec import (
    ReferenceTypeID,
    ClassLoaderID,
    ClassObjectID,
    FieldID,
    MethodID,
    TaggedObjectID,
    JdwpValue,
    InterfaceID,
)
from jdwpy.constants import JdwpTypeTag, JdwpClassStatus


@dataclass
class SignatureResponse(JdwpResponse):
    """Represents the response of ReferenceType.Signature command."""

    signature: str

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(signature=reader.read_string())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_string(self.signature)


@register_command(SignatureResponse)
@dataclass
class SignatureCommand(JdwpCommand[SignatureResponse]):
    """JDWP Command Set 2, Command 1: ReferenceType.Signature."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 1

    ref_type: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(ref_type=reader.read_reference_type_id())


@dataclass
class ClassLoaderResponse(JdwpResponse):
    """Represents the response of ReferenceType.ClassLoader command."""

    class_loader: ClassLoaderID

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(class_loader=reader.read_class_loader_id())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_class_loader_id(self.class_loader)


@register_command(ClassLoaderResponse)
@dataclass
class ClassLoaderCommand(JdwpCommand[ClassLoaderResponse]):
    """JDWP Command Set 2, Command 2: ReferenceType.ClassLoader."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 2

    ref_type: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(ref_type=reader.read_reference_type_id())


@dataclass
class ModifiersResponse(JdwpResponse):
    """Represents the response of ReferenceType.Modifiers command."""

    mod_bits: int

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(mod_bits=reader.read_int())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(self.mod_bits)


@register_command(ModifiersResponse)
@dataclass
class ModifiersCommand(JdwpCommand[ModifiersResponse]):
    """JDWP Command Set 2, Command 3: ReferenceType.Modifiers."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 3

    ref_type: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(ref_type=reader.read_reference_type_id())


@dataclass
class FieldsEntry:
    field_id: FieldID
    name: str
    signature: str
    mod_bits: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_field_id(self.field_id)
        writer.write_string(self.name)
        writer.write_string(self.signature)
        writer.write_int(self.mod_bits)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            field_id=reader.read_field_id(),
            name=reader.read_string(),
            signature=reader.read_string(),
            mod_bits=reader.read_int(),
        )


@dataclass
class FieldsResponse(JdwpResponse):
    """Represents the response of ReferenceType.Fields command."""

    fields: list[FieldsEntry]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        fields = [FieldsEntry.deserialize(reader) for _ in range(num)]
        return cls(fields=fields)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.fields))
        for f in self.fields:
            f.serialize(writer)


@register_command(FieldsResponse)
@dataclass
class FieldsCommand(JdwpCommand[FieldsResponse]):
    """JDWP Command Set 2, Command 4: ReferenceType.Fields."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 4

    ref_type: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(ref_type=reader.read_reference_type_id())


@dataclass
class MethodsEntry:
    method_id: MethodID
    name: str
    signature: str
    mod_bits: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_method_id(self.method_id)
        writer.write_string(self.name)
        writer.write_string(self.signature)
        writer.write_int(self.mod_bits)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            method_id=reader.read_method_id(),
            name=reader.read_string(),
            signature=reader.read_string(),
            mod_bits=reader.read_int(),
        )


@dataclass
class MethodsResponse(JdwpResponse):
    """Represents the response of ReferenceType.Methods command."""

    methods: list[MethodsEntry]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        methods = [MethodsEntry.deserialize(reader) for _ in range(num)]
        return cls(methods=methods)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.methods))
        for m in self.methods:
            m.serialize(writer)


@register_command(MethodsResponse)
@dataclass
class MethodsCommand(JdwpCommand[MethodsResponse]):
    """JDWP Command Set 2, Command 5: ReferenceType.Methods."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 5

    ref_type: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(ref_type=reader.read_reference_type_id())


@dataclass
class RefTypeGetValuesResponse(JdwpResponse):
    """Represents the response of ReferenceType.GetValues command."""

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


@register_command(RefTypeGetValuesResponse)
@dataclass
class RefTypeGetValuesCommand(JdwpCommand[RefTypeGetValuesResponse]):
    """JDWP Command Set 2, Command 6: ReferenceType.GetValues."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 6

    ref_type: ReferenceTypeID
    fields: list[FieldID]

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)
        writer.write_int(len(self.fields))
        for f in self.fields:
            writer.write_field_id(f)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        ref_type = reader.read_reference_type_id()
        num = reader.read_int()
        fields = [reader.read_field_id() for _ in range(num)]
        return cls(ref_type=ref_type, fields=fields)


@dataclass
class SourceFileResponse(JdwpResponse):
    """Represents the response of ReferenceType.SourceFile command."""

    source_file: str

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(source_file=reader.read_string())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_string(self.source_file)


@register_command(SourceFileResponse)
@dataclass
class SourceFileCommand(JdwpCommand[SourceFileResponse]):
    """JDWP Command Set 2, Command 7: ReferenceType.SourceFile."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 7

    ref_type: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(ref_type=reader.read_reference_type_id())


@dataclass
class NestedTypesEntry:
    ref_type_tag: JdwpTypeTag
    type_id: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_byte(self.ref_type_tag)
        writer.write_reference_type_id(self.type_id)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            ref_type_tag=JdwpTypeTag(reader.read_byte()),
            type_id=reader.read_reference_type_id(),
        )


@dataclass
class NestedTypesResponse(JdwpResponse):
    """Represents the response of ReferenceType.NestedTypes command."""

    nested_types: list[NestedTypesEntry]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        nested_types = [NestedTypesEntry.deserialize(reader) for _ in range(num)]
        return cls(nested_types=nested_types)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.nested_types))
        for t in self.nested_types:
            t.serialize(writer)


@register_command(NestedTypesResponse)
@dataclass
class NestedTypesCommand(JdwpCommand[NestedTypesResponse]):
    """JDWP Command Set 2, Command 8: ReferenceType.NestedTypes."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 8

    ref_type: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(ref_type=reader.read_reference_type_id())


@dataclass
class RefTypeStatusResponse(JdwpResponse):
    """Represents the response of ReferenceType.Status command."""

    status: JdwpClassStatus

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(status=JdwpClassStatus(reader.read_int()))

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(self.status)


@register_command(RefTypeStatusResponse)
@dataclass
class RefTypeStatusCommand(JdwpCommand[RefTypeStatusResponse]):
    """JDWP Command Set 2, Command 9: ReferenceType.Status."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 9

    ref_type: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(ref_type=reader.read_reference_type_id())


@dataclass
class InterfacesResponse(JdwpResponse):
    """Represents the response of ReferenceType.Interfaces command."""

    interfaces: list[InterfaceID]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        interfaces = [reader.read_interface_id() for _ in range(num)]
        return cls(interfaces=interfaces)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.interfaces))
        for i in self.interfaces:
            writer.write_interface_id(i)


@register_command(InterfacesResponse)
@dataclass
class InterfacesCommand(JdwpCommand[InterfacesResponse]):
    """JDWP Command Set 2, Command 10: ReferenceType.Interfaces."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 10

    ref_type: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(ref_type=reader.read_reference_type_id())


@dataclass
class ClassObjectResponse(JdwpResponse):
    """Represents the response of ReferenceType.ClassObject command."""

    class_object: ClassObjectID

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(class_object=reader.read_class_object_id())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_class_object_id(self.class_object)


@register_command(ClassObjectResponse)
@dataclass
class ClassObjectCommand(JdwpCommand[ClassObjectResponse]):
    """JDWP Command Set 2, Command 11: ReferenceType.ClassObject."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 11

    ref_type: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(ref_type=reader.read_reference_type_id())


@dataclass
class SourceDebugExtensionResponse(JdwpResponse):
    """Represents the response of ReferenceType.SourceDebugExtension command."""

    extension: str

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(extension=reader.read_string())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_string(self.extension)


@register_command(SourceDebugExtensionResponse)
@dataclass
class SourceDebugExtensionCommand(JdwpCommand[SourceDebugExtensionResponse]):
    """JDWP Command Set 2, Command 12: ReferenceType.SourceDebugExtension."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 12

    ref_type: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(ref_type=reader.read_reference_type_id())


@dataclass
class SignatureWithGenericResponse(JdwpResponse):
    """Represents the response of ReferenceType.SignatureWithGeneric command."""

    signature: str
    generic_signature: str

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            signature=reader.read_string(),
            generic_signature=reader.read_string(),
        )

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_string(self.signature)
        writer.write_string(self.generic_signature)


@register_command(SignatureWithGenericResponse)
@dataclass
class SignatureWithGenericCommand(JdwpCommand[SignatureWithGenericResponse]):
    """JDWP Command Set 2, Command 13: ReferenceType.SignatureWithGeneric."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 13

    ref_type: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(ref_type=reader.read_reference_type_id())


@dataclass
class FieldsWithGenericEntry:
    field_id: FieldID
    name: str
    signature: str
    generic_signature: str
    mod_bits: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_field_id(self.field_id)
        writer.write_string(self.name)
        writer.write_string(self.signature)
        writer.write_string(self.generic_signature)
        writer.write_int(self.mod_bits)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            field_id=reader.read_field_id(),
            name=reader.read_string(),
            signature=reader.read_string(),
            generic_signature=reader.read_string(),
            mod_bits=reader.read_int(),
        )


@dataclass
class FieldsWithGenericResponse(JdwpResponse):
    """Represents the response of ReferenceType.FieldsWithGeneric command."""

    fields: list[FieldsWithGenericEntry]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        fields = [FieldsWithGenericEntry.deserialize(reader) for _ in range(num)]
        return cls(fields=fields)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.fields))
        for f in self.fields:
            f.serialize(writer)


@register_command(FieldsWithGenericResponse)
@dataclass
class FieldsWithGenericCommand(JdwpCommand[FieldsWithGenericResponse]):
    """JDWP Command Set 2, Command 14: ReferenceType.FieldsWithGeneric."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 14

    ref_type: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(ref_type=reader.read_reference_type_id())


@dataclass
class MethodsWithGenericEntry:
    method_id: MethodID
    name: str
    signature: str
    generic_signature: str
    mod_bits: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_method_id(self.method_id)
        writer.write_string(self.name)
        writer.write_string(self.signature)
        writer.write_string(self.generic_signature)
        writer.write_int(self.mod_bits)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            method_id=reader.read_method_id(),
            name=reader.read_string(),
            signature=reader.read_string(),
            generic_signature=reader.read_string(),
            mod_bits=reader.read_int(),
        )


@dataclass
class MethodsWithGenericResponse(JdwpResponse):
    """Represents the response of ReferenceType.MethodsWithGeneric command."""

    methods: list[MethodsWithGenericEntry]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        methods = [MethodsWithGenericEntry.deserialize(reader) for _ in range(num)]
        return cls(methods=methods)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.methods))
        for m in self.methods:
            m.serialize(writer)


@register_command(MethodsWithGenericResponse)
@dataclass
class MethodsWithGenericCommand(JdwpCommand[MethodsWithGenericResponse]):
    """JDWP Command Set 2, Command 15: ReferenceType.MethodsWithGeneric."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 15

    ref_type: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(ref_type=reader.read_reference_type_id())


@dataclass
class InstancesResponse(JdwpResponse):
    """Represents the response of ReferenceType.Instances command."""

    instances: list[TaggedObjectID]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        instances = [reader.read_tagged_object() for _ in range(num)]
        return cls(instances=instances)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.instances))
        for i in self.instances:
            writer.write_tagged_object(i)


@register_command(InstancesResponse)
@dataclass
class InstancesCommand(JdwpCommand[InstancesResponse]):
    """JDWP Command Set 2, Command 16: ReferenceType.Instances."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 16

    ref_type: ReferenceTypeID
    max_instances: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)
        writer.write_int(self.max_instances)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            ref_type=reader.read_reference_type_id(),
            max_instances=reader.read_int(),
        )


@dataclass
class ClassFileVersionResponse(JdwpResponse):
    """Represents the response of ReferenceType.ClassFileVersion command."""

    major_version: int
    minor_version: int

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            major_version=reader.read_int(),
            minor_version=reader.read_int(),
        )

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(self.major_version)
        writer.write_int(self.minor_version)


@register_command(ClassFileVersionResponse)
@dataclass
class ClassFileVersionCommand(JdwpCommand[ClassFileVersionResponse]):
    """JDWP Command Set 2, Command 17: ReferenceType.ClassFileVersion."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 17

    ref_type: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(ref_type=reader.read_reference_type_id())


@dataclass
class ConstantPoolResponse(JdwpResponse):
    """Represents the response of ReferenceType.ConstantPool command."""

    bytes: bytes

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        b = bytes(reader.read_byte() for _ in range(num))
        return cls(bytes=b)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.bytes))
        for b in self.bytes:
            writer.write_byte(b)


@register_command(ConstantPoolResponse)
@dataclass
class ConstantPoolCommand(JdwpCommand[ConstantPoolResponse]):
    """JDWP Command Set 2, Command 18: ReferenceType.ConstantPool."""

    COMMAND_SET: ClassVar[int] = 2
    COMMAND: ClassVar[int] = 18

    ref_type: ReferenceTypeID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(ref_type=reader.read_reference_type_id())
