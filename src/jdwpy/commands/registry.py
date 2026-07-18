from typing import TYPE_CHECKING, overload, Any

if TYPE_CHECKING:
    from jdwpy.commands.base import JdwpCommand, JdwpResponse

# Global dictionary indexing commands by (COMMAND_SET, COMMAND)
_COMMAND_REGISTRY: dict[tuple[int, int], type[JdwpCommand[Any]]] = {}
_COMMAND_TO_RESPONSE: dict[type[JdwpCommand[Any]], type[JdwpResponse]] = {}


def register_command(response_class: type[JdwpResponse] | None = None):
    """Decorator to register a JdwpCommand concrete subclass and its response type mapping."""

    def decorator[C: JdwpCommand[Any]](cls: type[C]) -> type[C]:
        _COMMAND_REGISTRY[(cls.COMMAND_SET, cls.COMMAND)] = cls
        if response_class is not None:
            _COMMAND_TO_RESPONSE[cls] = response_class
        return cls

    return decorator


def get_command_class(command_set: int, command: int) -> type[JdwpCommand[Any]] | None:
    """Retrieves the registered JdwpCommand subclass for a given command set and command code."""
    return _COMMAND_REGISTRY.get((command_set, command))


@overload
def get_response_class(cmd_cls: type[JdwpCommand[None]]) -> None: ...


@overload
def get_response_class[T: JdwpResponse](cmd_cls: type[JdwpCommand[T]]) -> type[T]: ...


def get_response_class(cmd_cls: type[JdwpCommand[Any]]) -> type[JdwpResponse] | None:
    """Retrieves the registered response class for a given JdwpCommand class."""
    return _COMMAND_TO_RESPONSE.get(cmd_cls)
