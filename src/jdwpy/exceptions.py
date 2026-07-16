from __future__ import annotations
from typing import Any, TYPE_CHECKING
from jdwpy.constants import JdwpErrorCode

if TYPE_CHECKING:
    from jdwpy.commands.base import JdwpCommand


class JdwpException(Exception):
    """Exception raised when a JDWP command fails on the target VM."""

    error_code: JdwpErrorCode | None
    raw_error_code: int
    command: JdwpCommand[Any]

    def __init__(
        self,
        error_code: JdwpErrorCode | None,
        raw_error_code: int,
        command: JdwpCommand[Any],
    ) -> None:
        self.error_code = error_code
        self.raw_error_code = raw_error_code
        self.command = command
        err_name = error_code.name if error_code else "UNKNOWN"
        super().__init__(
            f"JDWP Command {command.__class__.__name__} failed with error: "
            f"{err_name} ({raw_error_code})"
        )
