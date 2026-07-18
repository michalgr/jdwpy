from __future__ import annotations
from jdwpy.spec import IdSizesSpec, ObjectID
from jdwpy.io import JdwpReader, JdwpWriter


def test_id_sizes_spec_struct_compilation() -> None:
    """Verifies that IdSizesSpec pre-compiles correct struct sizes and formats."""
    # Test 8-byte spec (typical 64-bit JVM)
    spec_8 = IdSizesSpec.create(
        field_id_size=8,
        method_id_size=8,
        object_id_size=8,
        reference_type_id_size=8,
        frame_id_size=8,
    )
    assert spec_8.field_id_struct.format == ">Q"
    assert spec_8.object_id_struct.format == ">Q"
    assert spec_8.field_id_struct.size == 8

    # Test 4-byte spec (typical 32-bit JVM)
    spec_4 = IdSizesSpec.create(
        field_id_size=4,
        method_id_size=4,
        object_id_size=4,
        reference_type_id_size=4,
        frame_id_size=4,
    )
    assert spec_4.field_id_struct.format == ">I"
    assert spec_4.object_id_struct.format == ">I"
    assert spec_4.field_id_struct.size == 4


def test_jdwp_writer_and_reader_primitives() -> None:
    """Tests big-endian serialization and parsing of primitives."""
    spec = IdSizesSpec.create()
    writer = JdwpWriter(spec)

    writer.write_byte(0xAB)
    writer.write_boolean(True)
    writer.write_boolean(False)
    writer.write_int(0x12345678)
    writer.write_long(0x1122334455667788)
    writer.write_string("Hello JDWP!")

    serialized = writer.get_bytes()
    reader = JdwpReader(serialized, spec)

    assert reader.read_byte() == 0xAB
    assert reader.read_boolean() is True
    assert reader.read_boolean() is False
    assert reader.read_int() == 0x12345678
    assert reader.read_long() == 0x1122334455667788
    assert reader.read_string() == "Hello JDWP!"
    assert reader.remaining == 0


def test_jdwp_writer_and_reader_ids() -> None:
    """Verifies variable length JDWP ID writing and reading."""
    # Test 8-byte mode
    spec_8 = IdSizesSpec.create(object_id_size=8)
    writer_8 = JdwpWriter(spec_8)
    writer_8.write_object_id(ObjectID(0xABCDEF1234567890))

    reader_8 = JdwpReader(writer_8.get_bytes(), spec_8)
    assert reader_8.read_object_id() == 0xABCDEF1234567890

    # Test 4-byte mode
    spec_4 = IdSizesSpec.create(object_id_size=4)
    writer_4 = JdwpWriter(spec_4)
    writer_4.write_object_id(ObjectID(0x76543210))

    reader_4 = JdwpReader(writer_4.get_bytes(), spec_4)
    assert reader_4.read_object_id() == 0x76543210
