from __future__ import annotations
import asyncio
import argparse
import sys
import logging
from dataclasses import dataclass
from typing import Self, Callable
from jdwpy.packet import JdwpPacket, JdwpCommandPacket, JdwpReplyPacket
from jdwpy.spec import IdSizesSpec
from jdwpy.constants import JdwpErrorCode, HANDSHAKE
from jdwpy.commands.registry import get_command_class, get_response_class
from jdwpy.commands.vm import IDSizesResponse
from jdwpy.connection import (
    JdwpPacketSender,
    JdwpPacketReceiver,
    establish_jdwp_connection,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JdwpDirection:
    label: str
    arrow: str
    color: str
    reset: str = "\033[0m"


DBG_TO_VM = JdwpDirection(label="Debugger -> VM", arrow=">>>", color="\033[92m")
VM_TO_DBG = JdwpDirection(label="VM -> Debugger", arrow="<<<", color="\033[94m")


def format_hexdump(data: bytes, prefix: str = "    ") -> str:
    """Formats bytes into a standard hex dump string (like hexdump -C)."""
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i : i + 16]
        hex_part = " ".join(f"{b:02X}" for b in chunk)
        # Add extra spacing between 8-byte groups
        if len(chunk) > 8:
            hex_part = hex_part[:23] + "  " + hex_part[23:]
        hex_part = hex_part.ljust(49)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{prefix}{i:04X}  {hex_part}  |{ascii_part}|")
    return "\n".join(lines)


class JdwpProxySession:
    """Manages a single bi-directional debugger-to-JVM proxy session using composition."""

    dbg_sender: JdwpPacketSender
    dbg_receiver: JdwpPacketReceiver
    vm_sender: JdwpPacketSender
    vm_receiver: JdwpPacketReceiver
    spec: IdSizesSpec
    idsizes_cmd_ids: set[int]
    outstanding_commands: dict[int, tuple[int, int]]
    close_event: asyncio.Event

    on_packet_log: Callable[[JdwpPacket, JdwpDirection, str], None] | None

    def __init__(
        self,
        dbg_sender: JdwpPacketSender,
        dbg_receiver: JdwpPacketReceiver,
        vm_sender: JdwpPacketSender,
        vm_receiver: JdwpPacketReceiver,
        on_packet_log: Callable[[JdwpPacket, JdwpDirection, str], None] | None = None,
    ) -> None:
        self.dbg_sender = dbg_sender
        self.dbg_receiver = dbg_receiver
        self.vm_sender = vm_sender
        self.vm_receiver = vm_receiver
        self.spec = IdSizesSpec.create()  # Default standard 8-byte ID spec
        self.idsizes_cmd_ids = set()
        self.outstanding_commands = {}
        self.close_event = asyncio.Event()
        self.on_packet_log = on_packet_log

    @classmethod
    async def create(
        cls,
        dbg_reader: asyncio.StreamReader,
        dbg_writer: asyncio.StreamWriter,
        target_host: str,
        target_port: int,
        on_packet_log: Callable[[JdwpPacket, JdwpDirection, str], None] | None = None,
    ) -> Self:
        """Factory method that establishes JVM connections and runs bi-directional handshakes."""
        # 1. Connect to JVM JDWP agent and run handshake
        vm_sender, vm_receiver = await establish_jdwp_connection(
            target_host, target_port
        )
        logger.info(f"Connected to target JVM at {target_host}:{target_port}")

        # 2. Negotiate debugger client handshake
        dbg_handshake = await dbg_reader.readexactly(len(HANDSHAKE))
        if dbg_handshake != HANDSHAKE:
            raise RuntimeError(
                f"Debugger client sent invalid handshake signature: {dbg_handshake!r}"
            )
        dbg_writer.write(HANDSHAKE)
        await dbg_writer.drain()
        logger.info("Bi-directional JDWP Handshake completed successfully!")

        # 3. Initialize wrapper objects
        dbg_sender = JdwpPacketSender(dbg_writer)
        dbg_receiver = JdwpPacketReceiver(dbg_reader)

        return cls(
            dbg_sender,
            dbg_receiver,
            vm_sender,
            vm_receiver,
            on_packet_log=on_packet_log,
        )

    async def _handle_debugger_packet(self, packet: JdwpPacket) -> None:
        """Processes and logs command packets sent from Debugger to VM."""
        if isinstance(packet, JdwpCommandPacket):
            self.outstanding_commands[packet.id] = (packet.command_set, packet.command)
            if packet.command_set == 1 and packet.command == 7:
                self.idsizes_cmd_ids.add(packet.id)

        await self.vm_sender.send_packet(packet)
        self._log_packet(packet, DBG_TO_VM)

    async def _handle_vm_packet(self, packet: JdwpPacket) -> None:
        """Processes, logs, and intercepts IDSizes responses sent from VM to Debugger."""
        if isinstance(packet, JdwpReplyPacket):
            if packet.id in self.idsizes_cmd_ids:
                self.idsizes_cmd_ids.remove(packet.id)
                if packet.error_code == 0:
                    resp = IDSizesResponse.from_bytes(packet.data, self.spec)
                    self.spec = IdSizesSpec.from_response(resp)
                    logger.info(
                        "Proxy intercepted IDSizes Reply - Dynamically updated Spec:\n"
                        f"    field={resp.field_id_size} method={resp.method_id_size} "
                        f"object={resp.object_id_size} refType={resp.reference_type_id_size} "
                        f"frame={resp.frame_id_size}"
                    )

        await self.dbg_sender.send_packet(packet)
        self._log_packet(packet, VM_TO_DBG)
        if isinstance(packet, JdwpReplyPacket):
            self.outstanding_commands.pop(packet.id, None)

    async def _handle_debugger_exception(self, exc: Exception) -> None:
        """Handles debugger socket read failure by logging and triggering shutdown."""
        if isinstance(exc, asyncio.IncompleteReadError):
            logger.info("Debugger client closed connection.")
        else:
            logger.error(f"Debugger client connection error: {exc}")
        self.close_event.set()

    async def _handle_vm_exception(self, exc: Exception) -> None:
        """Handles VM socket read failure by logging and triggering shutdown."""
        if isinstance(exc, asyncio.IncompleteReadError):
            logger.info("Target JVM closed connection.")
        else:
            logger.error(f"Target JVM connection error: {exc}")
        self.close_event.set()

    async def run(self) -> None:
        """Orchestrates connection negotiation, packet routing, and graceful cleanup."""
        try:
            # 1. Start proxy receiver loops
            self.dbg_receiver.start(
                self._handle_debugger_packet, self._handle_debugger_exception
            )
            self.vm_receiver.start(self._handle_vm_packet, self._handle_vm_exception)

            # 2. Wait for termination and close resources cleanly
            await self.close_event.wait()
        finally:
            self.dbg_receiver.close()
            self.vm_receiver.close()
            await self.dbg_sender.close()
            await self.vm_sender.close()

    def _log_packet(self, packet: JdwpPacket, direction: JdwpDirection) -> None:
        raw_str = ""
        parsed_str = ""
        if isinstance(packet, JdwpCommandPacket):
            raw_str = self._format_raw_command(packet, direction)
            parsed_str = self._format_parsed_command(packet)
        elif isinstance(packet, JdwpReplyPacket):
            raw_str = self._format_raw_reply(packet, direction)
            parsed_str = self._format_parsed_reply(packet)

        # Build packet log message block
        raw_bytes = packet.to_bytes()
        hexdump_str = format_hexdump(raw_bytes, prefix="      ")

        log_lines = [raw_str, hexdump_str]
        if parsed_str:
            log_lines.append(parsed_str)
        log_msg = "\n".join(log_lines)

        if self.on_packet_log:
            self.on_packet_log(packet, direction, log_msg)
        else:
            logger.debug(log_msg)

    def _format_raw_command(
        self, packet: JdwpCommandPacket, direction: JdwpDirection
    ) -> str:
        cmd_cls = get_command_class(packet.command_set, packet.command)
        cmd_name = (
            cmd_cls.__name__
            if cmd_cls
            else f"UnknownCmd({packet.command_set}:{packet.command})"
        )
        return (
            f"{direction.color}{direction.arrow} [Command]{direction.reset} "
            f"ID: {packet.id:<4} | {cmd_name:<18} | Set: {packet.command_set:<2} Cmd: {packet.command:<2} | "
            f"Payload: {len(packet.data):<3} bytes"
        )

    def _format_parsed_command(self, packet: JdwpCommandPacket) -> str:
        cmd_cls = get_command_class(packet.command_set, packet.command)
        if cmd_cls and len(packet.data) > 0:
            try:
                cmd_obj = cmd_cls.from_bytes(packet.data, self.spec)
                return f"      Parsed: {cmd_obj}"
            except Exception as e:
                return f"      [Parse Error: {e}]"
        return ""

    def _format_raw_reply(
        self, packet: JdwpReplyPacket, direction: JdwpDirection
    ) -> str:
        err_val = packet.error_code
        err_enum = (
            JdwpErrorCode(err_val)
            if err_val in JdwpErrorCode.__members__.values()
            else None
        )
        err_name = err_enum.name if err_enum else f"Unknown({err_val})"
        return (
            f"{direction.color}{direction.arrow} [Reply  ]{direction.reset} "
            f"ID: {packet.id:<4} | Error: {err_name:<18} | Code: {err_val:<4} | "
            f"Payload: {len(packet.data):<3} bytes"
        )

    def _format_parsed_reply(self, packet: JdwpReplyPacket) -> str:
        err_val = packet.error_code
        # Match reply back to its original command
        cmd_info = self.outstanding_commands.get(packet.id)
        if cmd_info and err_val == JdwpErrorCode.NONE and len(packet.data) > 0:
            cmd_set, cmd_cmd = cmd_info
            cmd_cls = get_command_class(cmd_set, cmd_cmd)
            if cmd_cls:
                resp_cls = get_response_class(cmd_cls)
                if resp_cls:
                    try:
                        resp_obj = resp_cls.from_bytes(packet.data, self.spec)
                        return f"      Parsed: {resp_obj}"
                    except Exception as e:
                        return f"      [Parse Error: {e}]"
        return ""


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Async JDWP Logging Proxy - bi-directionally traces debugger traffic."
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=5005,
        help="Port to listen for debugger client (default: 5005)",
    )
    parser.add_argument(
        "--target-host",
        type=str,
        default="127.0.0.1",
        help="Target JVM Host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--target-port",
        type=int,
        default=8700,
        help="Target JVM JDWP Port (default: 8700)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose packet-level logging (debug level)",
    )
    args = parser.parse_args()

    # Configure root logger with simple message format
    log_level = logging.DEBUG if args.verbose else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    logger.info(f"[*] Starting JDWP Logging Proxy on port {args.listen_port}...")
    logger.info(
        f"[*] Forwarding traffic to JVM JDWP agent at {args.target_host}:{args.target_port}"
    )

    async def client_connected(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        logger.info(f"[*] Accepted debugger client connection from {peer}")
        try:
            session = await JdwpProxySession.create(
                reader, writer, args.target_host, args.target_port
            )
            await session.run()
        except asyncio.IncompleteReadError as e:
            if e.partial:
                logger.error(
                    f"[-] Session error in {peer}: JDWP Handshake incomplete (read {len(e.partial)} of {e.expected} bytes)"
                )
            else:
                logger.info(f"[*] Client {peer} disconnected before JDWP handshake.")
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            logger.error(f"[-] Session error in {peer}: {e}")
            writer.close()
            await writer.wait_closed()
        finally:
            logger.info(f"[*] Session closed for client {peer}")

    server = await asyncio.start_server(client_connected, "127.0.0.1", args.listen_port)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Proxy server terminated by user.")
