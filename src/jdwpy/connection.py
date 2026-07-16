from __future__ import annotations
import asyncio
import logging
from typing import Callable, Awaitable, Self, overload, Any
from jdwpy.constants import JdwpErrorCode, HANDSHAKE
from jdwpy.spec import IdSizesSpec
from jdwpy.packet import JdwpPacket, JdwpCommandPacket, JdwpReplyPacket
from jdwpy.exceptions import JdwpException

logger = logging.getLogger(__name__)

from jdwpy.commands.base import JdwpCommand, JdwpResponse
from jdwpy.commands.registry import get_response_class, get_command_class
from jdwpy.commands.vm import IDSizesResponse


class JdwpPacketSender:
    """Handles writing and flushing JdwpPacket objects to a stream writer."""

    _writer: asyncio.StreamWriter

    def __init__(self, writer: asyncio.StreamWriter) -> None:
        self._writer = writer

    async def send_packet(self, packet: JdwpPacket) -> None:
        """Writes and flushes a JdwpPacket to the underlying socket stream."""
        packet.serialize(self._writer)
        await self._writer.drain()

    async def close(self) -> None:
        """Closes the stream writer."""
        self._writer.close()
        await self._writer.wait_closed()


class JdwpPacketReceiver:
    """Asynchronously reads JdwpPacket objects from a stream reader in a background loop."""

    _reader: asyncio.StreamReader
    _read_task: asyncio.Task | None

    def __init__(self, reader: asyncio.StreamReader) -> None:
        self._reader = reader
        self._read_task = None

    def start(
        self,
        on_packet: Callable[[JdwpPacket], Awaitable[None]],
        on_exception: Callable[[Exception], Awaitable[None]],
    ) -> None:
        """Starts the background reading task."""
        self._read_task = asyncio.create_task(self._read_loop(on_packet, on_exception))

    async def _read_loop(
        self,
        on_packet: Callable[[JdwpPacket], Awaitable[None]],
        on_exception: Callable[[Exception], Awaitable[None]],
    ) -> None:
        try:
            while True:
                packet = await JdwpPacket.deserialize(self._reader)
                await on_packet(packet)
        except asyncio.IncompleteReadError as e:
            await on_exception(e)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            await on_exception(e)

    def close(self) -> None:
        """Cancels the background reading task."""
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()


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

    return JdwpPacketSender(writer), JdwpPacketReceiver(reader)


class JdwpPacketConnection:
    """Coordinates JdwpPacketSender and JdwpPacketReceiver for client request-reply mapping."""

    sender: JdwpPacketSender
    receiver: JdwpPacketReceiver
    _pending_replies: dict[int, asyncio.Future[JdwpReplyPacket]]
    event_queue: asyncio.Queue[JdwpCommandPacket]

    def __init__(self, sender: JdwpPacketSender, receiver: JdwpPacketReceiver) -> None:
        self.sender = sender
        self.receiver = receiver
        self._pending_replies = {}
        self.event_queue = asyncio.Queue()

    def start(self) -> None:
        """Starts the background reading task."""
        self.receiver.start(
            on_packet=self._handle_packet, on_exception=self._handle_exception
        )

    @classmethod
    async def connect(cls, host: str, port: int) -> Self:
        """Establishes TCP connection and runs JDWP handshake prior to starting read loop."""
        sender, receiver = await establish_jdwp_connection(host, port)
        conn = cls(sender, receiver)
        conn.start()
        return conn

    async def _handle_packet(self, packet: JdwpPacket) -> None:
        if isinstance(packet, JdwpReplyPacket):
            future = self._pending_replies.pop(packet.id, None)
            if future and not future.done():
                future.set_result(packet)
        elif isinstance(packet, JdwpCommandPacket):
            await self.event_queue.put(packet)

    async def _handle_exception(self, exc: Exception) -> None:
        for fut in list(self._pending_replies.values()):
            if not fut.done():
                fut.set_exception(exc)
        self._pending_replies.clear()

    async def send_command_packet(self, packet: JdwpCommandPacket) -> JdwpReplyPacket:
        """Sends a JdwpCommandPacket and awaits the corresponding JdwpReplyPacket."""
        future = asyncio.get_running_loop().create_future()
        self._pending_replies[packet.id] = future
        await self.sender.send_packet(packet)
        return await future

    async def close(self) -> None:
        """Gracefully closes sender and receiver loops."""
        self.receiver.close()
        await self.sender.close()


class JdwpConnection:
    """Higher-level connection abstraction that operates on JdwpCommand and JdwpResponse classes."""

    _packet_conn: JdwpPacketConnection
    spec: IdSizesSpec
    _next_packet_id: int

    def __init__(
        self, packet_conn: JdwpPacketConnection, spec: IdSizesSpec | None = None
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
    async def connect(cls, host: str, port: int) -> Self:
        """Establishes connection to JDWP agent, wrapping the JdwpPacketConnection."""
        packet_conn = await JdwpPacketConnection.connect(host, port)
        return cls(packet_conn)

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
            await self._packet_conn.sender.send_packet(packet)
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

    async def read_command(self) -> JdwpCommand[Any]:
        """Awaits and parses the next command packet received from the VM."""
        packet = await self._packet_conn.event_queue.get()
        cmd_cls = get_command_class(packet.command_set, packet.command)
        if cmd_cls is None:
            raise RuntimeError(
                f"Unknown command received from VM: Set {packet.command_set}, Command {packet.command}"
            )
        cmd = cmd_cls.from_bytes(packet.data, self.spec)
        return cmd

    async def close(self) -> None:
        """Closes the underlying packet connection."""
        await self._packet_conn.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
