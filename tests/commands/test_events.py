from __future__ import annotations
import pytest
from jdwpy.spec import (
    IdSizesSpec,
    ObjectID,
    ReferenceTypeID,
    Location,
    MethodID,
    FieldID,
    TaggedObjectID,
    JdwpValue,
)
from jdwpy.constants import (
    JdwpEventKind,
    JdwpSuspendPolicy,
    JdwpTypeTag,
    JdwpTag,
    JdwpClassStatus,
)
from jdwpy import commands

from tests.protocol_helpers import assert_command_roundtrip


@pytest.mark.asyncio
async def test_event_request_command_set() -> None:
    """Verifies flow and serialization for commands in the EventRequest Command Set (Set 15)."""
    # 4-byte JDWP spec configuration
    spec = IdSizesSpec.create(
        field_id_size=4,
        method_id_size=4,
        object_id_size=4,
        reference_type_id_size=4,
        frame_id_size=4,
    )

    # 1. ClearAllBreakpoints Command
    await assert_command_roundtrip(
        commands.event_request.ClearAllBreakpointsCommand(),
        commands.event_request.ClearAllBreakpointsResponse(),
        spec=spec,
    )

    # 2. Clear Command
    cmd_clear = commands.event_request.ClearCommand(
        event_kind=JdwpEventKind.BREAKPOINT, request_id=42
    )
    await assert_command_roundtrip(
        cmd_clear, commands.event_request.ClearResponse(), spec=spec
    )

    # 3. Set Command with no modifiers
    cmd_set_simple = commands.event_request.SetCommand(
        event_kind=JdwpEventKind.BREAKPOINT,
        suspend_policy=JdwpSuspendPolicy.NONE,
        modifiers=[],
    )
    await assert_command_roundtrip(
        cmd_set_simple, commands.event_request.SetResponse(request_id=100)
    )

    # 4. Set Command with various modifiers
    modifiers = [
        commands.event_request.CountModifier(count=5),
        commands.event_request.ConditionalModifier(expr_id=123),
        commands.event_request.ThreadOnlyModifier(thread=ObjectID(0x11223344)),
        commands.event_request.ClassOnlyModifier(clazz=ReferenceTypeID(0x55667788)),
        commands.event_request.ClassMatchModifier(class_pattern="java.lang.*"),
        commands.event_request.ClassExcludeModifier(class_pattern="sun.*"),
        commands.event_request.LocationOnlyModifier(
            loc=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x99AABBCC),
                method_id=MethodID(0xDDEEFF00),
                index=0x1122334455667788,
            )
        ),
        commands.event_request.ExceptionOnlyModifier(
            exception_or_null=ReferenceTypeID(0x77889900), caught=True, uncaught=False
        ),
        commands.event_request.FieldOnlyModifier(
            declaring=ReferenceTypeID(0x66554433), field=FieldID(0x221100AA)
        ),
        commands.event_request.StepModifier(
            thread=ObjectID(0xDEADBEEF), size=1, depth=2
        ),
        commands.event_request.InstanceOnlyModifier(instance=ObjectID(0xFEEDFACE)),
        commands.event_request.PlatformThreadsOnlyModifier(),
    ]
    cmd_set_complex = commands.event_request.SetCommand(
        event_kind=JdwpEventKind.BREAKPOINT,
        suspend_policy=JdwpSuspendPolicy.ALL,
        modifiers=modifiers,
    )
    await assert_command_roundtrip(
        cmd_set_complex, commands.event_request.SetResponse(request_id=42), spec=spec
    )


@pytest.mark.asyncio
async def test_composite_events_roundtrip() -> None:
    spec = IdSizesSpec.create(
        field_id_size=4,
        method_id_size=4,
        object_id_size=4,
        reference_type_id_size=4,
        frame_id_size=4,
    )

    events = [
        commands.event.VMStartEvent(request_id=0, thread=ObjectID(0x1111)),
        commands.event.SingleStepEvent(
            request_id=1,
            thread=ObjectID(0x1111),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
        ),
        commands.event.BreakpointEvent(
            request_id=42,
            thread=ObjectID(0x2222),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x3333),
                method_id=MethodID(0x4444),
                index=0x5555666677778888,
            ),
        ),
        commands.event.MethodEntryEvent(
            request_id=2,
            thread=ObjectID(0x1111),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
        ),
        commands.event.MethodExitEvent(
            request_id=3,
            thread=ObjectID(0x1111),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
        ),
        commands.event.MethodExitWithReturnValueEvent(
            request_id=4,
            thread=ObjectID(0x1111),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
            value=JdwpValue(tag=JdwpTag.STRING, value=ObjectID(0x5555)),
        ),
        commands.event.MonitorContendedEnterEvent(
            request_id=5,
            thread=ObjectID(0x1111),
            object=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0x5555)),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
        ),
        commands.event.MonitorContendedEnteredEvent(
            request_id=6,
            thread=ObjectID(0x1111),
            object=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0x5555)),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
        ),
        commands.event.MonitorWaitEvent(
            request_id=7,
            thread=ObjectID(0x1111),
            object=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0x5555)),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
            timeout=1000,
        ),
        commands.event.MonitorWaitedEvent(
            request_id=8,
            thread=ObjectID(0x1111),
            object=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0x5555)),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
            timed_out=True,
        ),
        commands.event.ExceptionEvent(
            request_id=9,
            thread=ObjectID(0x1111),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
            exception=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0x6666)),
            catch_location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x5555,
            ),
        ),
        commands.event.ThreadStartEvent(
            request_id=0,
            thread=ObjectID(0x1111),
        ),
        commands.event.ThreadDeathEvent(
            request_id=10,
            thread=ObjectID(0x1111),
        ),
        commands.event.ClassPrepareEvent(
            request_id=0,
            thread=ObjectID(0x1111),
            ref_type_tag=JdwpTypeTag.CLASS,
            type_id=ReferenceTypeID(0x3333),
            signature="Ljava/lang/String;",
            status=JdwpClassStatus.VERIFIED,
        ),
        commands.event.ClassUnloadEvent(
            request_id=11,
            signature="Ljava/lang/Object;",
        ),
        commands.event.FieldAccessEvent(
            request_id=12,
            thread=ObjectID(0x1111),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x2222),
                method_id=MethodID(0x3333),
                index=0x4444,
            ),
            ref_type_tag=JdwpTypeTag.CLASS,
            type_id=ReferenceTypeID(0x2222),
            field_id=FieldID(0x7777),
            object=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0x5555)),
        ),
        commands.event.FieldModificationEvent(
            request_id=77,
            thread=ObjectID(0x2222),
            location=Location(
                type_tag=JdwpTypeTag.CLASS,
                class_id=ReferenceTypeID(0x3333),
                method_id=MethodID(0x4444),
                index=0x5555666677778888,
            ),
            ref_type_tag=JdwpTypeTag.CLASS,
            type_id=ReferenceTypeID(0x3333),
            field_id=FieldID(0x9999),
            object=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0xAAAA)),
            value_to_be=JdwpValue(tag=JdwpTag.INT, value=42),
        ),
        commands.event.VMDeathEvent(
            request_id=13,
        ),
    ]

    composite = commands.event.CompositeCommand(
        suspend_policy=JdwpSuspendPolicy.ALL,
        events=events,
    )

    await assert_command_roundtrip(composite, None, spec=spec)
