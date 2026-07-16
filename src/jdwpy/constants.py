from __future__ import annotations
from enum import IntEnum, IntFlag

HANDSHAKE = b"JDWP-Handshake"


class JdwpTag(IntEnum):
    """JDWP Type Tag Signatures (usually ASCII character values)."""

    ARRAY = 91  # '['
    BYTE = 66  # 'B'
    CHAR = 67  # 'C'
    OBJECT = 76  # 'L'
    FLOAT = 70  # 'F'
    DOUBLE = 68  # 'D'
    INT = 73  # 'I'
    LONG = 74  # 'J'
    SHORT = 83  # 'S'
    VOID = 86  # 'V'
    BOOLEAN = 90  # 'Z'
    STRING = 115  # 's'
    THREAD = 116  # 't'
    THREAD_GROUP = 103  # 'g'
    CLASS_LOADER = 108  # 'l'
    CLASS_OBJECT = 99  # 'c'


class JdwpErrorCode(IntEnum):
    """JDWP Error Codes mapped to their standard protocol definitions."""

    NONE = 0
    INVALID_THREAD = 10
    INVALID_THREAD_GROUP = 11
    INVALID_PRIORITY = 12
    THREAD_NOT_SUSPENDED = 13
    THREAD_SUSPENDED = 14
    INVALID_OBJECT = 20
    INVALID_CLASS = 21
    CLASS_NOT_PREPARED = 22
    INVALID_METHODID = 23
    INVALID_LOCATION = 24
    INVALID_FIELDID = 25
    INVALID_FRAMEID = 30
    NO_MORE_FRAMES = 31
    OPAQUE_FRAME = 32
    NOT_CURRENT_FRAME = 33
    TYPE_MISMATCH = 34
    INVALID_SLOT = 35
    DUPLICATE = 40
    NOT_FOUND = 41
    INVALID_MONITOR = 50
    NOT_MONITOR_OWNER = 51
    INTERRUPTED = 52
    INVALID_CLASS_FORMAT = 60
    CIRCULAR_CLASS_DEFINITION = 61
    FAILS_VERIFICATION = 62
    ADD_METHOD_NOT_IMPLEMENTED = 63
    SCHEMA_CHANGE_NOT_IMPLEMENTED = 64
    INVALID_TYPESTATE = 65
    HIERARCHY_CHANGE_NOT_IMPLEMENTED = 66
    DELETE_METHOD_NOT_IMPLEMENTED = 67
    UNSUPPORTED_VERSION = 68
    NAMES_DONT_MATCH = 69
    CLASS_MODIFIERS_CHANGE_NOT_IMPLEMENTED = 70
    METHOD_MODIFIERS_CHANGE_NOT_IMPLEMENTED = 71
    NOT_IMPLEMENTED = 99
    NULL_POINTER = 100
    ABSENT_INFORMATION = 101
    INTERNAL = 102
    COULD_NOT_WRITE_FILE = 103
    NATIVE_METHOD = 104
    OPAQUE_METHOD = 105
    INVALID_CLASS_LOADER = 106
    INVALID_ARRAY = 107
    TRANSPORT_LOAD = 108
    TRANSPORT_INIT = 109
    NATIVE_METHOD_BIND_FAILED = 110
    INVALID_STAGE = 111
    VM_DEAD = 112
    OUT_OF_MEMORY = 113
    ACCESS_DENIED = 115


class JdwpEventKind(IntEnum):
    """JDWP Event Kind constants."""

    SINGLE_STEP = 1
    BREAKPOINT = 2
    FRAME_POP = 3
    EXCEPTION = 4
    USER_DEFINED = 5
    THREAD_START = 6
    THREAD_DEATH = 7
    CLASS_PREPARE = 8
    CLASS_UNLOAD = 9
    CLASS_LOAD = 10
    FIELD_ACCESS = 20
    FIELD_MODIFICATION = 21
    EXCEPTION_CATCH = 30
    METHOD_ENTRY = 40
    METHOD_EXIT = 41
    METHOD_EXIT_WITH_RETURN_VALUE = 42
    MONITOR_CONTENDED_ENTER = 43
    MONITOR_CONTENDED_ENTERED = 44
    MONITOR_WAIT = 45
    MONITOR_WAITED = 46
    VM_START = 90
    VM_DEATH = 99


class JdwpSuspendPolicy(IntEnum):
    """JDWP Suspend Policy constants."""

    NONE = 0
    EVENT_THREAD = 1
    ALL = 2


class JdwpTypeTag(IntEnum):
    """JDWP Type Tag constants."""

    CLASS = 1
    INTERFACE = 2
    ARRAY = 3


class JdwpClassStatus(IntFlag):
    """JDWP Class Status constants."""

    VERIFIED = 1
    PREPARED = 2
    INITIALIZED = 4
    ERROR = 8


class JdwpInvokeOptions(IntFlag):
    """JDWP Method Invocation Options."""

    NONE = 0
    INVOKE_SINGLE_THREADED = 0x01
    INVOKE_NONVIRTUAL = 0x02


class JdwpThreadStatus(IntEnum):
    """JDWP Thread Status constants."""

    ZOMBIE = 0
    RUNNING = 1
    SLEEPING = 2
    MONITOR = 3
    WAIT = 4


class JdwpSuspendStatus(IntEnum):
    """JDWP Suspend Status constants."""

    NONE = 0
    SUSPENDED = 1
