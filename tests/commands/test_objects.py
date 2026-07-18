from __future__ import annotations
import pytest
from jdwpy.spec import (
    IdSizesSpec,
    ObjectID,
    ThreadID,
    ClassID,
    MethodID,
    ReferenceTypeID,
    TaggedObjectID,
    FieldID,
    JdwpValue,
    StringID,
    ArrayObjectID,
    ClassLoaderID,
)
from jdwpy.constants import (
    JdwpTypeTag,
    JdwpTag,
    JdwpInvokeOptions,
)
from jdwpy import commands

from tests.protocol_helpers import assert_command_roundtrip


@pytest.mark.asyncio
async def test_object_reference_command_set() -> None:
    """Verifies flow and serialization for commands in the ObjectReference Command Set (Set 9)."""
    spec = IdSizesSpec.create()
    obj = ObjectID(0x11223344)
    thread = ThreadID(0x55667788)
    clazz = ClassID(0x99AABBCC)
    method = MethodID(0xDDDEEEFF)

    # 1. ReferenceType Command
    await assert_command_roundtrip(
        commands.object_reference.ReferenceTypeCommand(object=obj),
        commands.object_reference.ReferenceTypeResponse(
            ref_type_tag=JdwpTypeTag.CLASS, type_id=ReferenceTypeID(0x7777)
        ),
        spec=spec,
    )

    # 2. GetValues Command
    await assert_command_roundtrip(
        commands.object_reference.GetValuesCommand(
            object=obj, fields=[FieldID(0xAAAA)]
        ),
        commands.object_reference.GetValuesResponse(
            values=[JdwpValue(tag=JdwpTag.INT, value=42)]
        ),
        spec=spec,
    )

    # 3. SetValues Command
    await assert_command_roundtrip(
        commands.object_reference.SetValuesCommand(
            object=obj,
            slots=[
                commands.object_reference.SetValuesRequestSlot(
                    field_id=FieldID(0xAAAA),
                    value=JdwpValue(tag=JdwpTag.INT, value=42),
                )
            ],
        ),
        commands.object_reference.SetValuesResponse(),
        spec=spec,
    )

    # 5. MonitorInfo Command
    await assert_command_roundtrip(
        commands.object_reference.MonitorInfoCommand(object=obj),
        commands.object_reference.MonitorInfoResponse(
            owner=ThreadID(0x8888),
            entry_count=1,
            waiters=[ThreadID(0x9999)],
        ),
        spec=spec,
    )

    # 6. InvokeMethod Command
    await assert_command_roundtrip(
        commands.object_reference.InvokeMethodCommand(
            object=obj,
            thread=thread,
            clazz=clazz,
            method=method,
            arguments=[JdwpValue(tag=JdwpTag.INT, value=100)],
            options=JdwpInvokeOptions.INVOKE_NONVIRTUAL,
        ),
        commands.object_reference.InvokeMethodResponse(
            return_value=JdwpValue(tag=JdwpTag.INT, value=200),
            exception=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0)),
        ),
        spec=spec,
    )

    # 7. DisableCollection Command
    await assert_command_roundtrip(
        commands.object_reference.DisableCollectionCommand(object=obj),
        commands.object_reference.DisableCollectionResponse(),
        spec=spec,
    )

    # 8. EnableCollection Command
    await assert_command_roundtrip(
        commands.object_reference.EnableCollectionCommand(object=obj),
        commands.object_reference.EnableCollectionResponse(),
        spec=spec,
    )

    # 9. IsCollected Command
    await assert_command_roundtrip(
        commands.object_reference.IsCollectedCommand(object=obj),
        commands.object_reference.IsCollectedResponse(is_collected=False),
        spec=spec,
    )

    # 10. ReferringObjects Command
    await assert_command_roundtrip(
        commands.object_reference.ReferringObjectsCommand(object=obj, max_referrers=5),
        commands.object_reference.ReferringObjectsResponse(
            referring_objects=[
                TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0xFEED))
            ]
        ),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_string_reference_command_set() -> None:
    """Verifies flow and serialization for commands in the StringReference Command Set (Set 10)."""
    spec = IdSizesSpec.create()

    # 1. Value Command
    await assert_command_roundtrip(
        commands.string_reference.ValueCommand(string_object=StringID(0x11223344)),
        commands.string_reference.ValueResponse(string_value="Hello World"),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_array_reference_command_set() -> None:
    """Verifies flow and serialization for commands in the ArrayReference Command Set (Set 13)."""
    spec = IdSizesSpec.create()
    arr = ArrayObjectID(0x11223344)

    # 1. Length Command
    await assert_command_roundtrip(
        commands.array_reference.LengthCommand(array_object=arr),
        commands.array_reference.LengthResponse(array_length=5),
        spec=spec,
    )

    # 2. GetValues Command
    await assert_command_roundtrip(
        commands.array_reference.GetValuesCommand(
            array_object=arr, first_index=0, length=2
        ),
        commands.array_reference.GetValuesResponse(
            values=commands.array_reference.JdwpArrayRegion(
                tag=JdwpTag.INT,
                values=[
                    JdwpValue(tag=JdwpTag.INT, value=100),
                    JdwpValue(tag=JdwpTag.INT, value=200),
                ],
            )
        ),
        spec=spec,
    )

    # 3. SetValues Command
    await assert_command_roundtrip(
        commands.array_reference.SetValuesCommand(
            array_object=arr,
            first_index=0,
            tag=JdwpTag.INT,
            values=[
                JdwpValue(tag=JdwpTag.INT, value=300),
                JdwpValue(tag=JdwpTag.INT, value=400),
            ],
        ),
        commands.array_reference.SetValuesResponse(),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_class_loader_reference_command_set() -> None:
    """Verifies flow and serialization for commands in the ClassLoaderReference Command Set (Set 14)."""
    spec = IdSizesSpec.create()

    # 1. VisibleClasses Command
    await assert_command_roundtrip(
        commands.class_loader_reference.VisibleClassesCommand(
            class_loader=ClassLoaderID(0x11223344)
        ),
        commands.class_loader_reference.VisibleClassesResponse(
            classes=[
                commands.class_loader_reference.VisibleClassesEntry(
                    ref_type_tag=JdwpTypeTag.CLASS,
                    type_id=ReferenceTypeID(0x55667788),
                )
            ]
        ),
        spec=spec,
    )
