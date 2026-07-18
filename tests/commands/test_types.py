from __future__ import annotations
import pytest
from jdwpy.spec import (
    IdSizesSpec,
    ReferenceTypeID,
    ClassLoaderID,
    InterfaceID,
    ClassObjectID,
    ObjectID,
    ClassID,
    ThreadID,
    MethodID,
    TaggedObjectID,
    FieldID,
    JdwpValue,
    ArrayTypeID,
    ArrayObjectID,
)
from jdwpy.constants import (
    JdwpTypeTag,
    JdwpClassStatus,
    JdwpTag,
    JdwpInvokeOptions,
)
from jdwpy import commands

from tests.protocol_helpers import assert_command_roundtrip


@pytest.mark.asyncio
async def test_reference_type_command_set() -> None:
    """Verifies flow and serialization for commands in the ReferenceType Command Set (Set 2)."""
    spec = IdSizesSpec.create()
    ref_type = ReferenceTypeID(0x11223344)

    # 1. Signature Command
    await assert_command_roundtrip(
        commands.reference_type.SignatureCommand(ref_type=ref_type),
        commands.reference_type.SignatureResponse(signature="Ljava/lang/String;"),
        spec=spec,
    )

    # 2. ClassLoader Command
    await assert_command_roundtrip(
        commands.reference_type.ClassLoaderCommand(ref_type=ref_type),
        commands.reference_type.ClassLoaderResponse(
            class_loader=ClassLoaderID(0x55667788)
        ),
        spec=spec,
    )

    # 3. Modifiers Command
    await assert_command_roundtrip(
        commands.reference_type.ModifiersCommand(ref_type=ref_type),
        commands.reference_type.ModifiersResponse(mod_bits=0x21),
        spec=spec,
    )

    # 4. Fields Command
    await assert_command_roundtrip(
        commands.reference_type.FieldsCommand(ref_type=ref_type),
        commands.reference_type.FieldsResponse(
            fields=[
                commands.reference_type.FieldsEntry(
                    field_id=FieldID(0xAAAA),
                    name="value",
                    signature="[C",
                    mod_bits=0x12,
                )
            ]
        ),
        spec=spec,
    )

    # 5. Methods Command
    await assert_command_roundtrip(
        commands.reference_type.MethodsCommand(ref_type=ref_type),
        commands.reference_type.MethodsResponse(
            methods=[
                commands.reference_type.MethodsEntry(
                    method_id=MethodID(0xBBBB),
                    name="indexOf",
                    signature="(I)I",
                    mod_bits=0x1,
                )
            ]
        ),
        spec=spec,
    )

    # 6. RefTypeGetValues Command
    await assert_command_roundtrip(
        commands.reference_type.GetValuesCommand(
            ref_type=ref_type, fields=[FieldID(0xAAAA)]
        ),
        commands.reference_type.GetValuesResponse(
            values=[JdwpValue(tag=JdwpTag.INT, value=42)]
        ),
        spec=spec,
    )

    # 7. SourceFile Command
    await assert_command_roundtrip(
        commands.reference_type.SourceFileCommand(ref_type=ref_type),
        commands.reference_type.SourceFileResponse(source_file="String.java"),
        spec=spec,
    )

    # 8. NestedTypes Command
    await assert_command_roundtrip(
        commands.reference_type.NestedTypesCommand(ref_type=ref_type),
        commands.reference_type.NestedTypesResponse(
            nested_types=[
                commands.reference_type.NestedTypesEntry(
                    ref_type_tag=JdwpTypeTag.CLASS,
                    type_id=ReferenceTypeID(0x22334455),
                )
            ]
        ),
        spec=spec,
    )

    # 9. RefTypeStatus Command
    await assert_command_roundtrip(
        commands.reference_type.StatusCommand(ref_type=ref_type),
        commands.reference_type.StatusResponse(
            status=JdwpClassStatus.VERIFIED | JdwpClassStatus.PREPARED
        ),
        spec=spec,
    )

    # 10. Interfaces Command
    await assert_command_roundtrip(
        commands.reference_type.InterfacesCommand(ref_type=ref_type),
        commands.reference_type.InterfacesResponse(interfaces=[InterfaceID(0x9999)]),
        spec=spec,
    )

    # 11. ClassObject Command
    await assert_command_roundtrip(
        commands.reference_type.ClassObjectCommand(ref_type=ref_type),
        commands.reference_type.ClassObjectResponse(class_object=ClassObjectID(0x8888)),
        spec=spec,
    )

    # 12. SourceDebugExtension Command
    await assert_command_roundtrip(
        commands.reference_type.SourceDebugExtensionCommand(ref_type=ref_type),
        commands.reference_type.SourceDebugExtensionResponse(
            extension="KotlinDebugExtension"
        ),
        spec=spec,
    )

    # 13. SignatureWithGeneric Command
    await assert_command_roundtrip(
        commands.reference_type.SignatureWithGenericCommand(ref_type=ref_type),
        commands.reference_type.SignatureWithGenericResponse(
            signature="Ljava/util/List;",
            generic_signature="Ljava/util/List<TE;>;",
        ),
        spec=spec,
    )

    # 14. FieldsWithGeneric Command
    await assert_command_roundtrip(
        commands.reference_type.FieldsWithGenericCommand(ref_type=ref_type),
        commands.reference_type.FieldsWithGenericResponse(
            fields=[
                commands.reference_type.FieldsWithGenericEntry(
                    field_id=FieldID(0xCCCC),
                    name="list",
                    signature="Ljava/util/List;",
                    generic_signature="Ljava/util/List<Ljava/lang/String;>;",
                    mod_bits=0x2,
                )
            ]
        ),
        spec=spec,
    )

    # 15. MethodsWithGeneric Command
    await assert_command_roundtrip(
        commands.reference_type.MethodsWithGenericCommand(ref_type=ref_type),
        commands.reference_type.MethodsWithGenericResponse(
            methods=[
                commands.reference_type.MethodsWithGenericEntry(
                    method_id=MethodID(0xDDDD),
                    name="getList",
                    signature="()Ljava/util/List;",
                    generic_signature="()Ljava/util/List<Ljava/lang/String;>;",
                    mod_bits=0x1,
                )
            ]
        ),
        spec=spec,
    )

    # 16. Instances Command
    await assert_command_roundtrip(
        commands.reference_type.InstancesCommand(ref_type=ref_type, max_instances=5),
        commands.reference_type.InstancesResponse(
            instances=[
                TaggedObjectID(
                    tag=JdwpTag.OBJECT,
                    object_id=ObjectID(0xEEFF),
                )
            ]
        ),
        spec=spec,
    )

    # 17. ClassFileVersion Command
    await assert_command_roundtrip(
        commands.reference_type.ClassFileVersionCommand(ref_type=ref_type),
        commands.reference_type.ClassFileVersionResponse(
            major_version=52, minor_version=0
        ),
        spec=spec,
    )

    # 18. ConstantPool Command
    await assert_command_roundtrip(
        commands.reference_type.ConstantPoolCommand(ref_type=ref_type),
        commands.reference_type.ConstantPoolResponse(bytes=b"\xca\xfe\xba\xbe"),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_class_type_command_set() -> None:
    """Verifies flow and serialization for commands in the ClassType Command Set (Set 3)."""
    spec = IdSizesSpec.create()
    clazz = ClassID(0x11223344)
    thread = ThreadID(0x55667788)
    method = MethodID(0x99AABBCC)

    # 1. Superclass Command
    await assert_command_roundtrip(
        commands.class_type.SuperclassCommand(clazz=clazz),
        commands.class_type.SuperclassResponse(superclass=ClassID(0x22334455)),
        spec=spec,
    )

    # 2. ClassTypeSetValues Command
    await assert_command_roundtrip(
        commands.class_type.SetValuesCommand(
            clazz=clazz,
            slots=[
                commands.class_type.SetValuesRequestSlot(
                    field_id=FieldID(0xAAAA),
                    value=JdwpValue(tag=JdwpTag.INT, value=42),
                )
            ],
        ),
        commands.class_type.SetValuesResponse(),
        spec=spec,
    )

    # 3. ClassTypeInvokeMethod Command
    await assert_command_roundtrip(
        commands.class_type.InvokeMethodCommand(
            clazz=clazz,
            thread=thread,
            method=method,
            arguments=[JdwpValue(tag=JdwpTag.INT, value=100)],
            options=JdwpInvokeOptions.INVOKE_NONVIRTUAL,
        ),
        commands.class_type.InvokeMethodResponse(
            return_value=JdwpValue(tag=JdwpTag.INT, value=200),
            exception=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0)),
        ),
        spec=spec,
    )

    # 4. NewInstance Command
    await assert_command_roundtrip(
        commands.class_type.NewInstanceCommand(
            clazz=clazz,
            thread=thread,
            method=method,
            arguments=[JdwpValue(tag=JdwpTag.INT, value=100)],
            options=JdwpInvokeOptions.INVOKE_NONVIRTUAL,
        ),
        commands.class_type.NewInstanceResponse(
            new_object=TaggedObjectID(
                tag=JdwpTag.OBJECT, object_id=ObjectID(0xDEADBEEF)
            ),
            exception=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0)),
        ),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_array_type_command_set() -> None:
    """Verifies flow and serialization for commands in the ArrayType Command Set (Set 4)."""
    spec = IdSizesSpec.create()

    # 1. NewInstance Command
    await assert_command_roundtrip(
        commands.array_type.NewInstanceCommand(
            arr_type=ArrayTypeID(0x11223344), length=10
        ),
        commands.array_type.NewInstanceResponse(new_array=ArrayObjectID(0x55667788)),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_interface_type_command_set() -> None:
    """Verifies flow and serialization for commands in the InterfaceType Command Set (Set 5)."""
    spec = IdSizesSpec.create()

    # 1. InvokeMethod Command
    await assert_command_roundtrip(
        commands.interface_type.InvokeMethodCommand(
            clazz=InterfaceID(0x11223344),
            thread=ThreadID(0x55667788),
            method=MethodID(0x99AABBCC),
            arguments=[JdwpValue(tag=JdwpTag.INT, value=100)],
            options=JdwpInvokeOptions.INVOKE_NONVIRTUAL,
        ),
        commands.interface_type.InvokeMethodResponse(
            return_value=JdwpValue(tag=JdwpTag.INT, value=200),
            exception=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0)),
        ),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_class_object_reference_command_set() -> None:
    """Verifies flow and serialization for commands in the ClassObjectReference Command Set (Set 17)."""
    spec = IdSizesSpec.create()

    # 1. ReflectedType Command
    await assert_command_roundtrip(
        commands.class_object_reference.ReflectedTypeCommand(
            class_object=ObjectID(0x11223344)
        ),
        commands.class_object_reference.ReflectedTypeResponse(
            ref_type_tag=JdwpTypeTag.CLASS, type_id=ReferenceTypeID(0x55667788)
        ),
        spec=spec,
    )
