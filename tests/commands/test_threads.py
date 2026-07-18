from __future__ import annotations
import pytest
from jdwpy.spec import (
    IdSizesSpec,
    ThreadID,
    ReferenceTypeID,
    MethodID,
    Location,
    FrameID,
    TaggedObjectID,
    ObjectID,
    ThreadGroupID,
    JdwpValue,
)
from jdwpy.constants import (
    JdwpTypeTag,
    JdwpThreadStatus,
    JdwpSuspendStatus,
    JdwpTag,
)
from jdwpy import commands

from tests.protocol_helpers import assert_command_roundtrip


@pytest.mark.asyncio
async def test_stack_frame_command_set() -> None:
    """Verifies flow and serialization for commands in the StackFrame Command Set (Set 16)."""
    spec = IdSizesSpec.create()
    thread_id = ThreadID(0x11223344)
    frame_id = FrameID(0x55667788)

    # 1. GetValues Command
    await assert_command_roundtrip(
        commands.stack_frame.GetValuesCommand(
            thread=thread_id,
            frame=frame_id,
            slots=[
                commands.stack_frame.GetValuesRequestSlot(slot=0, sig_byte=JdwpTag.INT),
                commands.stack_frame.GetValuesRequestSlot(
                    slot=1, sig_byte=JdwpTag.OBJECT
                ),
            ],
        ),
        commands.stack_frame.GetValuesResponse(
            values=[
                JdwpValue(tag=JdwpTag.INT, value=42),
                JdwpValue(tag=JdwpTag.OBJECT, value=ObjectID(0xDEADBEEF)),
            ]
        ),
        spec=spec,
    )

    # 2. SetValues Command
    await assert_command_roundtrip(
        commands.stack_frame.SetValuesCommand(
            thread=thread_id,
            frame=frame_id,
            slots=[
                commands.stack_frame.SetValuesRequestSlot(
                    slot=0, value=JdwpValue(tag=JdwpTag.INT, value=42)
                ),
                commands.stack_frame.SetValuesRequestSlot(
                    slot=1,
                    value=JdwpValue(tag=JdwpTag.OBJECT, value=ObjectID(0xDEADBEEF)),
                ),
            ],
        ),
        commands.stack_frame.SetValuesResponse(),
        spec=spec,
    )

    # 3. ThisObject Command
    await assert_command_roundtrip(
        commands.stack_frame.ThisObjectCommand(thread=thread_id, frame=frame_id),
        commands.stack_frame.ThisObjectResponse(
            this_object=TaggedObjectID(
                tag=JdwpTag.OBJECT, object_id=ObjectID(0xFEEDFACE)
            )
        ),
        spec=spec,
    )

    # 4. PopFrames Command
    await assert_command_roundtrip(
        commands.stack_frame.PopFramesCommand(thread=thread_id, frame=frame_id),
        commands.stack_frame.PopFramesResponse(),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_thread_reference_command_set() -> None:
    """Verifies flow and serialization for commands in the ThreadReference Command Set (Set 11)."""
    spec = IdSizesSpec.create()
    thread = ThreadID(0x11223344)
    ref_type = ReferenceTypeID(0x55667788)
    method = MethodID(0x99AABBCC)
    location = Location(
        type_tag=JdwpTypeTag.CLASS, class_id=ref_type, method_id=method, index=42
    )

    # 1. Name Command
    await assert_command_roundtrip(
        commands.thread_reference.NameCommand(thread=thread),
        commands.thread_reference.NameResponse(thread_name="main"),
        spec=spec,
    )

    # 2. Suspend Command
    await assert_command_roundtrip(
        commands.thread_reference.SuspendCommand(thread=thread),
        commands.thread_reference.SuspendResponse(),
        spec=spec,
    )

    # 3. Resume Command
    await assert_command_roundtrip(
        commands.thread_reference.ResumeCommand(thread=thread),
        commands.thread_reference.ResumeResponse(),
        spec=spec,
    )

    # 4. Status Command
    await assert_command_roundtrip(
        commands.thread_reference.StatusCommand(thread=thread),
        commands.thread_reference.StatusResponse(
            thread_status=JdwpThreadStatus.RUNNING,
            suspend_status=JdwpSuspendStatus.SUSPENDED,
        ),
        spec=spec,
    )

    # 5. ThreadGroup Command
    await assert_command_roundtrip(
        commands.thread_reference.ThreadGroupCommand(thread=thread),
        commands.thread_reference.ThreadGroupResponse(
            thread_group=ThreadGroupID(0x9999)
        ),
        spec=spec,
    )

    # 6. Frames Command
    await assert_command_roundtrip(
        commands.thread_reference.FramesCommand(thread=thread, start_frame=0, length=5),
        commands.thread_reference.FramesResponse(
            frames=[
                commands.thread_reference.FramesEntry(
                    frame_id=FrameID(0xAAAA),
                    location=location,
                )
            ]
        ),
        spec=spec,
    )

    # 7. FrameCount Command
    await assert_command_roundtrip(
        commands.thread_reference.FrameCountCommand(thread=thread),
        commands.thread_reference.FrameCountResponse(frame_count=1),
        spec=spec,
    )

    # 8. OwnedMonitors Command
    await assert_command_roundtrip(
        commands.thread_reference.OwnedMonitorsCommand(thread=thread),
        commands.thread_reference.OwnedMonitorsResponse(
            monitors=[TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0xBBBB))]
        ),
        spec=spec,
    )

    # 9. CurrentContendedMonitor Command
    await assert_command_roundtrip(
        commands.thread_reference.CurrentContendedMonitorCommand(thread=thread),
        commands.thread_reference.CurrentContendedMonitorResponse(
            monitor=TaggedObjectID(tag=JdwpTag.OBJECT, object_id=ObjectID(0xCCCC))
        ),
        spec=spec,
    )

    # 10. Stop Command
    await assert_command_roundtrip(
        commands.thread_reference.StopCommand(
            thread=thread, throwable=ObjectID(0xDDDD)
        ),
        commands.thread_reference.StopResponse(),
        spec=spec,
    )

    # 11. Interrupt Command
    await assert_command_roundtrip(
        commands.thread_reference.InterruptCommand(thread=thread),
        commands.thread_reference.InterruptResponse(),
        spec=spec,
    )

    # 12. SuspendCount Command
    await assert_command_roundtrip(
        commands.thread_reference.SuspendCountCommand(thread=thread),
        commands.thread_reference.SuspendCountResponse(suspend_count=1),
        spec=spec,
    )

    # 13. OwnedMonitorsStackDepthInfo Command
    await assert_command_roundtrip(
        commands.thread_reference.OwnedMonitorsStackDepthInfoCommand(thread=thread),
        commands.thread_reference.OwnedMonitorsStackDepthInfoResponse(
            monitors=[
                commands.thread_reference.MonitorStackDepthInfoEntry(
                    monitor=TaggedObjectID(
                        tag=JdwpTag.OBJECT, object_id=ObjectID(0xEEEE)
                    ),
                    stack_depth=2,
                )
            ]
        ),
        spec=spec,
    )

    # 14. ForceEarlyReturn Command
    await assert_command_roundtrip(
        commands.thread_reference.ForceEarlyReturnCommand(
            thread=thread, value=JdwpValue(tag=JdwpTag.INT, value=42)
        ),
        commands.thread_reference.ForceEarlyReturnResponse(),
        spec=spec,
    )


@pytest.mark.asyncio
async def test_thread_group_reference_command_set() -> None:
    """Verifies flow and serialization for commands in the ThreadGroupReference Command Set (Set 12)."""
    spec = IdSizesSpec.create()
    group = ThreadGroupID(0x11223344)

    # 1. Name Command
    await assert_command_roundtrip(
        commands.thread_group_reference.NameCommand(group=group),
        commands.thread_group_reference.NameResponse(group_name="system"),
        spec=spec,
    )

    # 2. Parent Command
    await assert_command_roundtrip(
        commands.thread_group_reference.ParentCommand(group=group),
        commands.thread_group_reference.ParentResponse(
            parent_group=ThreadGroupID(0x55667788)
        ),
        spec=spec,
    )

    # 3. Children Command
    await assert_command_roundtrip(
        commands.thread_group_reference.ChildrenCommand(group=group),
        commands.thread_group_reference.ChildrenResponse(
            child_threads=[ThreadID(0xAAAA)],
            child_groups=[ThreadGroupID(0xBBBB)],
        ),
        spec=spec,
    )
