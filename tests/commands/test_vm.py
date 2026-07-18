from __future__ import annotations
import pytest
from jdwpy.spec import (
    IdSizesSpec,
    ReferenceTypeID,
    ThreadID,
    ThreadGroupID,
    StringID,
    ObjectID,
)
from jdwpy.constants import (
    JdwpTypeTag,
    JdwpClassStatus,
)
from jdwpy import commands

from tests.protocol_helpers import assert_command_roundtrip


@pytest.mark.asyncio
async def test_virtual_machine_command_set() -> None:
    """Verifies flow and serialization for commands in the VirtualMachine Command Set (Set 1)."""
    spec = IdSizesSpec.create()

    # 1. Version Command
    resp_version = commands.vm.VersionResponse(
        description="JVM 14.0",
        jdwp_major=1,
        jdwp_minor=6,
        vm_version="14.0.1",
        vm_name="OpenJDK",
    )
    await assert_command_roundtrip(
        commands.vm.VersionCommand(), resp_version, spec=spec
    )

    # 2. IDSizes Command & spec update verification
    resp_ids = commands.vm.IDSizesResponse(
        field_id_size=4,
        method_id_size=4,
        object_id_size=8,
        reference_type_id_size=8,
        frame_id_size=8,
    )
    await assert_command_roundtrip(commands.vm.IDSizesCommand(), resp_ids, spec=spec)

    # 3. ClassesBySignature Command
    classes_by_sig_resp = commands.vm.ClassesBySignatureResponse(
        classes=[
            commands.vm.ClassesBySignatureEntry(
                ref_type_tag=JdwpTypeTag.CLASS,
                type_id=ReferenceTypeID(42),
                status=JdwpClassStatus.VERIFIED,
            )
        ]
    )
    await assert_command_roundtrip(
        commands.vm.ClassesBySignatureCommand(signature="Ljava/lang/String;"),
        classes_by_sig_resp,
        spec=spec,
    )

    # 4. AllClasses Command
    all_classes_resp = commands.vm.AllClassesResponse(
        classes=[
            commands.vm.AllClassesEntry(
                ref_type_tag=JdwpTypeTag.CLASS,
                type_id=ReferenceTypeID(42),
                signature="Ljava/lang/String;",
                status=JdwpClassStatus.VERIFIED,
            )
        ]
    )
    await assert_command_roundtrip(
        commands.vm.AllClassesCommand(),
        all_classes_resp,
        spec=spec,
    )

    # 5. AllThreads Command
    all_threads_resp = commands.vm.AllThreadsResponse(
        threads=[ThreadID(42), ThreadID(43)]
    )
    await assert_command_roundtrip(
        commands.vm.AllThreadsCommand(),
        all_threads_resp,
        spec=spec,
    )

    # 6. TopLevelThreadGroups Command
    top_level_groups_resp = commands.vm.TopLevelThreadGroupsResponse(
        groups=[ThreadGroupID(44)]
    )
    await assert_command_roundtrip(
        commands.vm.TopLevelThreadGroupsCommand(),
        top_level_groups_resp,
        spec=spec,
    )

    # 7. Dispose Command
    await assert_command_roundtrip(
        commands.vm.DisposeCommand(),
        commands.vm.DisposeResponse(),
        spec=spec,
    )

    # 8. Suspend Command
    await assert_command_roundtrip(
        commands.vm.SuspendCommand(),
        commands.vm.SuspendResponse(),
        spec=spec,
    )

    # 9. Resume Command
    await assert_command_roundtrip(
        commands.vm.ResumeCommand(),
        commands.vm.ResumeResponse(),
        spec=spec,
    )

    # 10. Exit Command
    await assert_command_roundtrip(
        commands.vm.ExitCommand(exit_code=42),
        commands.vm.ExitResponse(),
        spec=spec,
    )

    # 11. CreateString Command
    await assert_command_roundtrip(
        commands.vm.CreateStringCommand(utf="hello"),
        commands.vm.CreateStringResponse(string_object=StringID(45)),
        spec=spec,
    )

    # 12. Capabilities Command
    caps_resp = commands.vm.CapabilitiesResponse(
        can_watch_field_modification=True,
        can_watch_field_access=True,
        can_get_bytecodes=True,
        can_get_synthetic_attribute=True,
        can_get_owned_monitor_info=True,
        can_get_current_contended_monitor=True,
        can_get_monitor_info=True,
    )
    await assert_command_roundtrip(
        commands.vm.CapabilitiesCommand(),
        caps_resp,
        spec=spec,
    )

    # 13. ClassPaths Command
    class_paths_resp = commands.vm.ClassPathsResponse(
        base_dir="/base",
        classpaths=["/cp1"],
        bootclasspaths=["/bcp1"],
    )
    await assert_command_roundtrip(
        commands.vm.ClassPathsCommand(),
        class_paths_resp,
        spec=spec,
    )

    # 14. DisposeObjects Command
    await assert_command_roundtrip(
        commands.vm.DisposeObjectsCommand(
            requests=[
                commands.vm.DisposeObjectsRequest(object_id=ObjectID(46), ref_cnt=2)
            ]
        ),
        commands.vm.DisposeObjectsResponse(),
        spec=spec,
    )

    # 15. HoldEvents Command
    await assert_command_roundtrip(
        commands.vm.HoldEventsCommand(),
        commands.vm.HoldEventsResponse(),
        spec=spec,
    )

    # 16. ReleaseEvents Command
    await assert_command_roundtrip(
        commands.vm.ReleaseEventsCommand(),
        commands.vm.ReleaseEventsResponse(),
        spec=spec,
    )

    # 17. CapabilitiesNew Command
    caps_new_resp = commands.vm.CapabilitiesNewResponse(
        can_watch_field_modification=True,
        can_watch_field_access=True,
        can_get_bytecodes=True,
        can_get_synthetic_attribute=True,
        can_get_owned_monitor_info=True,
        can_get_current_contended_monitor=True,
        can_get_monitor_info=True,
        can_redefine_classes=True,
        can_add_method=True,
        can_unrestrictedly_redefine_classes=True,
        can_pop_frames=True,
        can_use_instance_filters=True,
        can_get_source_debug_extension=True,
        can_request_vm_death_event=True,
        can_set_default_stratum=True,
        can_get_instance_info=True,
        can_request_monitor_events=True,
        can_get_monitor_frame_info=True,
        can_use_source_name_filters=True,
        can_get_constant_pool=True,
        can_force_early_return=True,
        reserved22=False,
        reserved23=False,
        reserved24=False,
        reserved25=False,
        reserved26=False,
        reserved27=False,
        reserved28=False,
        reserved29=False,
        reserved30=False,
        reserved31=False,
        reserved32=False,
    )
    await assert_command_roundtrip(
        commands.vm.CapabilitiesNewCommand(),
        caps_new_resp,
        spec=spec,
    )

    # 18. RedefineClasses Command
    await assert_command_roundtrip(
        commands.vm.RedefineClassesCommand(
            classes=[
                commands.vm.RedefineClassesRequest(
                    ref_type=ReferenceTypeID(47),
                    class_bytes=b"\xca\xfe\xba\xbe",
                )
            ]
        ),
        commands.vm.RedefineClassesResponse(),
        spec=spec,
    )

    # 19. SetDefaultStratum Command
    await assert_command_roundtrip(
        commands.vm.SetDefaultStratumCommand(stratum_id="Java"),
        commands.vm.SetDefaultStratumResponse(),
        spec=spec,
    )

    # 20. AllClassesWithGeneric Command
    all_classes_generic_resp = commands.vm.AllClassesWithGenericResponse(
        classes=[
            commands.vm.AllClassesWithGenericEntry(
                ref_type_tag=JdwpTypeTag.CLASS,
                type_id=ReferenceTypeID(48),
                signature="Ljava/util/List;",
                generic_signature="Ljava/util/List<TE;>;",
                status=JdwpClassStatus.VERIFIED,
            )
        ]
    )
    await assert_command_roundtrip(
        commands.vm.AllClassesWithGenericCommand(),
        all_classes_generic_resp,
        spec=spec,
    )

    # 21. InstanceCounts Command
    await assert_command_roundtrip(
        commands.vm.InstanceCountsCommand(ref_types=[ReferenceTypeID(49)]),
        commands.vm.InstanceCountsResponse(counts=[100]),
        spec=spec,
    )
