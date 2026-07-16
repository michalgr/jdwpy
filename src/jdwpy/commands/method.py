from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar, Self
from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import register_command
from jdwpy.io import JdwpReader, JdwpWriter
from jdwpy.spec import ReferenceTypeID, MethodID


@dataclass
class LineTableEntry:
    code_index: int  # long
    line_number: int  # int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_long(self.code_index)
        writer.write_int(self.line_number)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            code_index=reader.read_long(),
            line_number=reader.read_int(),
        )


@dataclass
class LineTableResponse(JdwpResponse):
    """Represents the response of Method.LineTable command."""

    start_code_index: int  # long
    end_code_index: int  # long
    lines: list[LineTableEntry]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        start_code_index = reader.read_long()
        end_code_index = reader.read_long()
        num = reader.read_int()
        lines = [LineTableEntry.deserialize(reader) for _ in range(num)]
        return cls(
            start_code_index=start_code_index,
            end_code_index=end_code_index,
            lines=lines,
        )

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_long(self.start_code_index)
        writer.write_long(self.end_code_index)
        writer.write_int(len(self.lines))
        for line in self.lines:
            line.serialize(writer)


@register_command(LineTableResponse)
@dataclass
class LineTableCommand(JdwpCommand[LineTableResponse]):
    """JDWP Command Set 6, Command 1: Method.LineTable."""

    COMMAND_SET: ClassVar[int] = 6
    COMMAND: ClassVar[int] = 1

    ref_type: ReferenceTypeID
    method: MethodID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)
        writer.write_method_id(self.method)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            ref_type=reader.read_reference_type_id(),
            method=reader.read_method_id(),
        )


@dataclass
class VariableTableEntry:
    code_index: int  # long
    name: str
    signature: str
    length: int
    slot: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_long(self.code_index)
        writer.write_string(self.name)
        writer.write_string(self.signature)
        writer.write_int(self.length)
        writer.write_int(self.slot)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            code_index=reader.read_long(),
            name=reader.read_string(),
            signature=reader.read_string(),
            length=reader.read_int(),
            slot=reader.read_int(),
        )


@dataclass
class VariableTableResponse(JdwpResponse):
    """Represents the response of Method.VariableTable command."""

    arg_cnt: int
    slots: list[VariableTableEntry]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        arg_cnt = reader.read_int()
        num = reader.read_int()
        slots = [VariableTableEntry.deserialize(reader) for _ in range(num)]
        return cls(arg_cnt=arg_cnt, slots=slots)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(self.arg_cnt)
        writer.write_int(len(self.slots))
        for s in self.slots:
            s.serialize(writer)


@register_command(VariableTableResponse)
@dataclass
class VariableTableCommand(JdwpCommand[VariableTableResponse]):
    """JDWP Command Set 6, Command 2: Method.VariableTable."""

    COMMAND_SET: ClassVar[int] = 6
    COMMAND: ClassVar[int] = 2

    ref_type: ReferenceTypeID
    method: MethodID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)
        writer.write_method_id(self.method)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            ref_type=reader.read_reference_type_id(),
            method=reader.read_method_id(),
        )


@dataclass
class BytecodesResponse(JdwpResponse):
    """Represents the response of Method.Bytecodes command."""

    bytecodes: bytes

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        num = reader.read_int()
        b = bytes(reader.read_byte() for _ in range(num))
        return cls(bytecodes=b)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(len(self.bytecodes))
        for b in self.bytecodes:
            writer.write_byte(b)


@register_command(BytecodesResponse)
@dataclass
class BytecodesCommand(JdwpCommand[BytecodesResponse]):
    """JDWP Command Set 6, Command 3: Method.Bytecodes."""

    COMMAND_SET: ClassVar[int] = 6
    COMMAND: ClassVar[int] = 3

    ref_type: ReferenceTypeID
    method: MethodID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)
        writer.write_method_id(self.method)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            ref_type=reader.read_reference_type_id(),
            method=reader.read_method_id(),
        )


@dataclass
class IsObsoleteResponse(JdwpResponse):
    """Represents the response of Method.IsObsolete command."""

    is_obsolete: bool

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(is_obsolete=reader.read_boolean())

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_boolean(self.is_obsolete)


@register_command(IsObsoleteResponse)
@dataclass
class IsObsoleteCommand(JdwpCommand[IsObsoleteResponse]):
    """JDWP Command Set 6, Command 4: Method.IsObsolete."""

    COMMAND_SET: ClassVar[int] = 6
    COMMAND: ClassVar[int] = 4

    ref_type: ReferenceTypeID
    method: MethodID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)
        writer.write_method_id(self.method)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            ref_type=reader.read_reference_type_id(),
            method=reader.read_method_id(),
        )


@dataclass
class VariableTableWithGenericEntry:
    code_index: int  # long
    name: str
    signature: str
    generic_signature: str
    length: int
    slot: int

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_long(self.code_index)
        writer.write_string(self.name)
        writer.write_string(self.signature)
        writer.write_string(self.generic_signature)
        writer.write_int(self.length)
        writer.write_int(self.slot)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            code_index=reader.read_long(),
            name=reader.read_string(),
            signature=reader.read_string(),
            generic_signature=reader.read_string(),
            length=reader.read_int(),
            slot=reader.read_int(),
        )


@dataclass
class VariableTableWithGenericResponse(JdwpResponse):
    """Represents the response of Method.VariableTableWithGeneric command."""

    arg_cnt: int
    slots: list[VariableTableWithGenericEntry]

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        arg_cnt = reader.read_int()
        num = reader.read_int()
        slots = [VariableTableWithGenericEntry.deserialize(reader) for _ in range(num)]
        return cls(arg_cnt=arg_cnt, slots=slots)

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_int(self.arg_cnt)
        writer.write_int(len(self.slots))
        for s in self.slots:
            s.serialize(writer)


@register_command(VariableTableWithGenericResponse)
@dataclass
class VariableTableWithGenericCommand(JdwpCommand[VariableTableWithGenericResponse]):
    """JDWP Command Set 6, Command 5: Method.VariableTableWithGeneric."""

    COMMAND_SET: ClassVar[int] = 6
    COMMAND: ClassVar[int] = 5

    ref_type: ReferenceTypeID
    method: MethodID

    def serialize(self, writer: JdwpWriter) -> None:
        writer.write_reference_type_id(self.ref_type)
        writer.write_method_id(self.method)

    @classmethod
    def deserialize(cls, reader: JdwpReader) -> Self:
        return cls(
            ref_type=reader.read_reference_type_id(),
            method=reader.read_method_id(),
        )
