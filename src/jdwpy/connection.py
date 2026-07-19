from __future__ import annotations
import asyncio
import logging
from typing import Self, overload, Any, Protocol
from jdwpy.constants import JdwpErrorCode, HANDSHAKE
from jdwpy.spec import IdSizesSpec
from jdwpy.packet import JdwpPacket, JdwpCommandPacket, JdwpReplyPacket
from jdwpy.exceptions import JdwpException

from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import get_response_class, get_command_class
from jdwpy.commands.vm import IDSizesResponse

logger = logging.getLogger(__name__)


class JdwpPacketSender(Protocol):
    """Interface for writing JdwpPacket objects to a stream or buffer."""

    async def send(self, packet: JdwpPacket) -> None:
        """Writes and flushes a JdwpPacket to the target."""
        ...

    async def close(self) -> None:
        """Closes the packet sender."""
        ...


class StreamJdwpPacketSender(JdwpPacketSender):
    """Handles writing and flushing JdwpPacket objects to a stream writer."""

    _writer: asyncio.StreamWriter

    def __init__(self, writer: asyncio.StreamWriter) -> None:
        self._writer = writer

    async def send(self, packet: JdwpPacket) -> None:
        """Writes and flushes a JdwpPacket to the underlying socket stream."""
        packet.serialize(self._writer)
        await self._writer.drain()

    async def close(self) -> None:
        """Closes the stream writer."""
        self._writer.close()
        await self._writer.wait_closed()


class JdwpPacketReceiver(Protocol):
    """Interface for reading JdwpPacket objects from a stream or buffer."""

    async def receive(self) -> JdwpPacket:
        """Reads a single JdwpPacket."""
        ...

    async def close(self) -> None:
        """Closes the packet receiver."""
        ...


class StreamJdwpPacketReceiver(JdwpPacketReceiver):
    """Reads JdwpPacket objects from a stream reader."""

    _reader: asyncio.StreamReader

    def __init__(self, reader: asyncio.StreamReader) -> None:
        self._reader = reader

    async def receive(self) -> JdwpPacket:
        """Reads a single JdwpPacket from the stream."""
        return await JdwpPacket.deserialize(self._reader)

    async def close(self) -> None:
        """Closes the receiver."""
        pass


async def establish_jdwp_connection(
    host: str, port: int
) -> tuple[JdwpPacketSender, JdwpPacketReceiver]:
    """Establishes TCP connection, runs JDWP handshake, and returns packet sender/receiver."""
    reader, writer = await asyncio.open_connection(host, port)

    # Handshake negotiation on raw socket
    writer.write(HANDSHAKE)
    await writer.drain()
    response = await reader.readexactly(len(HANDSHAKE))
    if response != HANDSHAKE:
        writer.close()
        await writer.wait_closed()
        raise RuntimeError(
            f"Handshake failed. Expected '{HANDSHAKE.decode()}', got '{response.decode(errors='replace')}'"
        )

    return StreamJdwpPacketSender(writer), StreamJdwpPacketReceiver(reader)


class ConnectionState:
    """Manages the lifecycle state (closed/error) of a connection or event loop."""

    _closed: bool
    _error: BaseException | None

    def __init__(self) -> None:
        self._closed = False
        self._error = None

    @property
    def is_closed(self) -> bool:
        """Returns True if the connection has been explicitly closed."""
        return self._closed

    @property
    def error(self) -> BaseException | None:
        """Returns the exception that caused the connection to error out, if any."""
        return self._error

    def mark_closed(self) -> None:
        """Marks the connection state as closed."""
        self._closed = True

    def mark_error(self, error: BaseException) -> None:
        """Marks the connection state as errored due to the given exception."""
        if self._error is None:
            self._error = error

    def check(self) -> None:
        """Raises RuntimeError if the state indicates closed or errored."""
        if self._closed:
            raise RuntimeError("Connection closed")
        if self._error:
            raise RuntimeError("Connection closed due to error") from self._error


class JdwpPacketConnection:
    """Coordinates JdwpPacketSender and JdwpPacketReceiver for client request-reply mapping."""

    sender: JdwpPacketSender
    receiver: JdwpPacketReceiver
    _pending_replies: dict[int, asyncio.Future[JdwpReplyPacket]]
    _state: ConnectionState

    def __init__(self, sender: JdwpPacketSender, receiver: JdwpPacketReceiver) -> None:
        self.sender = sender
        self.receiver = receiver
        self._pending_replies = {}
        self._state = ConnectionState()

    def _clear_pending_replies(self) -> list[asyncio.Future[JdwpReplyPacket]]:
        """Clears the pending replies and returns the list of unresolved futures."""
        unresolved = [fut for fut in self._pending_replies.values() if not fut.done()]
        self._pending_replies.clear()
        return unresolved

    @classmethod
    async def connect(cls, host: str, port: int) -> Self:
        """Establishes TCP connection and runs JDWP handshake."""
        sender, receiver = await establish_jdwp_connection(host, port)
        return cls(sender, receiver)

    async def receive_command(self) -> JdwpCommandPacket:
        """Receives packets from the receiver until a JdwpCommandPacket is received,

        resolving pending reply futures as JdwpReplyPackets are encountered.
        """
        self._state.check()
        try:
            while True:
                packet = await self.receiver.receive()
                if isinstance(packet, JdwpReplyPacket):
                    future = self._pending_replies.pop(packet.id, None)
                    if future and not future.done():
                        future.set_result(packet)
                    else:
                        logger.warning(
                            "Received JDWP reply with ID %d but no active pending request",
                            packet.id,
                        )
                elif isinstance(packet, JdwpCommandPacket):
                    return packet
        except asyncio.CancelledError as e:
            self._state.mark_error(e)
            for fut in self._clear_pending_replies():
                fut.cancel()
            raise
        except BaseException as e:
            self._state.mark_error(e)
            for fut in self._clear_pending_replies():
                fut.set_exception(e)
            raise

    async def send_command_packet(self, packet: JdwpCommandPacket) -> JdwpReplyPacket:
        """Sends a JdwpCommandPacket and awaits the corresponding JdwpReplyPacket."""
        self._state.check()
        if packet.id in self._pending_replies:
            raise RuntimeError(f"Duplicate JDWP packet ID: {packet.id}")
        future = asyncio.get_running_loop().create_future()
        self._pending_replies[packet.id] = future
        try:
            await self.sender.send(packet)
            return await future
        finally:
            self._pending_replies.pop(packet.id, None)

    async def close(self) -> None:
        """Gracefully closes sender and receiver."""
        self._state.mark_closed()
        for fut in self._clear_pending_replies():
            fut.cancel()
        await self.receiver.close()
        await self.sender.close()


class JdwpConnection(Protocol):
    """Interface for sending and receiving high-level JdwpCommand and JdwpResponse objects."""

    async def receive_command(self) -> JdwpCommand[Any]:
        """Receives a high-level JdwpCommand from the connection."""
        ...

    @overload
    async def send_command(self, cmd: JdwpCommand[None]) -> None: ...

    @overload
    async def send_command[T: JdwpResponse](self, cmd: JdwpCommand[T]) -> T: ...

    async def send_command(self, cmd: JdwpCommand[Any]) -> JdwpResponse | None:
        """Sends a JdwpCommand, awaiting and validating the response."""
        ...

    async def close(self) -> None:
        """Closes the connection."""
        ...

    def __aiter__(self) -> Self:
        return self

    async def __anext__(self) -> JdwpCommand[Any]:
        try:
            return await self.receive_command()
        except RuntimeError:
            raise StopAsyncIteration

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    @classmethod
    async def connect(cls, host: str, port: int) -> JdwpConnection:
        """Establishes connection to JDWP agent and returns JdwpConnection with async loop."""
        return await JdwpConnectionWithAsyncLoop.connect(host, port)


class SimpleJdwpConnection(JdwpConnection):
    """Simple concrete implementation of JdwpConnection interface focusing on request-reply."""

    _packet_conn: JdwpPacketConnection
    spec: IdSizesSpec
    _next_packet_id: int

    def __init__(
        self,
        packet_conn: JdwpPacketConnection,
        spec: IdSizesSpec | None = None,
    ) -> None:
        self._packet_conn = packet_conn
        self.spec = spec or IdSizesSpec.create()
        self._next_packet_id = 1

    def _allocate_packet_id(self) -> int:
        """Allocates a unique packet identifier for a new JDWP request."""
        pkt_id = self._next_packet_id
        self._next_packet_id += 1
        return pkt_id

    @classmethod
    async def connect(cls, host: str, port: int) -> SimpleJdwpConnection:
        """Establishes connection to JDWP agent and returns SimpleJdwpConnection."""
        packet_conn = await JdwpPacketConnection.connect(host, port)
        return cls(packet_conn)

    async def receive_command(self) -> JdwpCommand[Any]:
        """Receives a raw command packet from the packet connection and parses it."""
        packet = await self._packet_conn.receive_command()
        cmd_cls = get_command_class(packet.command_set, packet.command)
        if cmd_cls is None:
            raise RuntimeError(
                f"Unknown command received from VM: Set {packet.command_set}, Command {packet.command}"
            )
        cmd = cmd_cls.from_bytes(packet.data, self.spec)
        return cmd

    @overload
    async def send_command(self, cmd: JdwpCommand[None]) -> None: ...

    @overload
    async def send_command[T: JdwpResponse](self, cmd: JdwpCommand[T]) -> T: ...

    async def send_command(self, cmd: JdwpCommand[Any]) -> JdwpResponse | None:
        """Sends a JdwpCommand, awaiting and validating the response packet dynamically."""
        packet = JdwpCommandPacket(
            id=self._allocate_packet_id(),
            flags=0,
            command_set=cmd.COMMAND_SET,
            command=cmd.COMMAND,
            data=cmd.to_bytes(self.spec),
        )

        response_class = get_response_class(cmd.__class__)
        if response_class is None:
            await self._packet_conn.sender.send(packet)
            return None

        # Send command packet and await corresponding raw reply packet
        reply = await self._packet_conn.send_command_packet(packet)

        # Validate error code
        if reply.error_code != JdwpErrorCode.NONE:
            err_code = JdwpErrorCode.from_int(reply.error_code)

            if err_code is None or err_code not in cmd.ALLOWED_ERRORS:
                logger.warning(
                    "Received unexpected JDWP error code %s (%d) for command %s",
                    err_code.name if err_code else "UNKNOWN",
                    reply.error_code,
                    cmd.__class__.__name__,
                )

            raise JdwpException(
                error_code=err_code,
                raw_error_code=reply.error_code,
                command=cmd,
            )

        # Deserialize response
        response = response_class.from_bytes(reply.data, self.spec)

        # Dynamic ID sizes spec upgrade detection
        if isinstance(response, IDSizesResponse):
            self.spec = IdSizesSpec.from_response(response)

        return response

    async def close(self) -> None:
        """Closes the underlying packet connection."""
        await self._packet_conn.close()


class JdwpConnectionWithAsyncLoop(JdwpConnection):
    """Implementation of JdwpConnection that delegates to SimpleJdwpConnection

    while managing a background async read loop and incoming command queue.
    """

    delegate: SimpleJdwpConnection
    _incoming_commands: asyncio.Queue[JdwpCommand[Any]]
    _read_task: asyncio.Task | None
    _state: ConnectionState

    def __init__(self, delegate: SimpleJdwpConnection) -> None:
        self.delegate = delegate
        self._incoming_commands = asyncio.Queue()
        self._read_task = None
        self._state = ConnectionState()

    def start(self) -> None:
        """Starts the background reading task."""
        if self._read_task is None:
            self._read_task = asyncio.create_task(self._read_loop())

    async def _read_loop(self) -> None:
        try:
            while True:
                cmd = await self.delegate.receive_command()
                await self._incoming_commands.put(cmd)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug("JdwpConnectionWithAsyncLoop read loop exception: %r", e)
            self._state.mark_error(e)
        finally:
            self._incoming_commands.shutdown()

    @classmethod
    async def connect(cls, host: str, port: int) -> JdwpConnectionWithAsyncLoop:
        """Establishes connection to JDWP agent and returns JdwpConnectionWithAsyncLoop."""
        delegate = await SimpleJdwpConnection.connect(host, port)
        return cls(delegate)

    async def receive_command(self) -> JdwpCommand[Any]:
        """Receives a high-level JdwpCommand from the background queue."""
        self.start()
        try:
            return await self._incoming_commands.get()
        except asyncio.QueueShutDown:
            self._state.check()
            raise RuntimeError("Connection closed")

    @overload
    async def send_command(self, cmd: JdwpCommand[None]) -> None: ...

    @overload
    async def send_command[T: JdwpResponse](self, cmd: JdwpCommand[T]) -> T: ...

    async def send_command(self, cmd: JdwpCommand[Any]) -> JdwpResponse | None:
        """Sends a JdwpCommand, awaiting and validating the response."""
        self.start()  # Auto-start read loop if not started
        self._state.check()
        return await self.delegate.send_command(cmd)

    async def close(self) -> None:
        """Stops the background task and closes the connection."""
        self._state.mark_closed()
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        await self.delegate.close()

    async def __aenter__(self) -> Self:
        self.start()
        return self
