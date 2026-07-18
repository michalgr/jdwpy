from __future__ import annotations
import pytest
from jdwpy.spec import (
    IdSizesSpec,
    ReferenceTypeID,
    MethodID,
)
from jdwpy import commands

from tests.protocol_helpers import assert_command_roundtrip


@pytest.mark.asyncio
async def test_method_command_set() -> None:
    """Verifies flow and serialization for commands in the Method Command Set (Set 6)."""
    spec = IdSizesSpec.create()
    ref_type = ReferenceTypeID(0x11223344)
    method = MethodID(0x55667788)

    # 1. LineTable Command
    await assert_command_roundtrip(
        commands.method.LineTableCommand(ref_type=ref_type, method=method),
        commands.method.LineTableResponse(
            start_code_index=10,
            end_code_index=100,
            lines=[commands.method.LineTableEntry(code_index=20, line_number=5)],
        ),
        spec=spec,
    )

    # 2. VariableTable Command
    await assert_command_roundtrip(
        commands.method.VariableTableCommand(ref_type=ref_type, method=method),
        commands.method.VariableTableResponse(
            arg_cnt=1,
            slots=[
                commands.method.VariableTableEntry(
                    code_index=10,
                    name="arg0",
                    signature="I",
                    length=90,
                    slot=0,
                )
            ],
        ),
        spec=spec,
    )

    # 3. Bytecodes Command
    await assert_command_roundtrip(
        commands.method.BytecodesCommand(ref_type=ref_type, method=method),
        commands.method.BytecodesResponse(bytecodes=b"\x1b\x3c\x1c\x3d"),
        spec=spec,
    )

    # 4. IsObsolete Command
    await assert_command_roundtrip(
        commands.method.IsObsoleteCommand(ref_type=ref_type, method=method),
        commands.method.IsObsoleteResponse(is_obsolete=False),
        spec=spec,
    )

    # 5. VariableTableWithGeneric Command
    await assert_command_roundtrip(
        commands.method.VariableTableWithGenericCommand(
            ref_type=ref_type, method=method
        ),
        commands.method.VariableTableWithGenericResponse(
            arg_cnt=1,
            slots=[
                commands.method.VariableTableWithGenericEntry(
                    code_index=10,
                    name="listArg",
                    signature="Ljava/util/List;",
                    generic_signature="Ljava/util/List<Ljava/lang/String;>;",
                    length=90,
                    slot=0,
                )
            ],
        ),
        spec=spec,
    )
