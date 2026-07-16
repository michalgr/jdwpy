from __future__ import annotations
import asyncio
import argparse
import sys
from typing import Self
from jdwpy.packet import JdwpPacket, JdwpCommandPacket, JdwpReplyPacket
from jdwpy.spec import IdSizesSpec
from jdwpy.constants import JdwpErrorCode, HANDSHAKE
from jdwpy.commands.registry import get_command_class
from jdwpy.commands.vm import IDSizesResponse
from jdwpy.connection import (
    JdwpPacketSender,
    JdwpPacketReceiver,
    establish_jdwp_connection,
)


class JdwpProxySession:
    """Manages a single bi-directional debugger-to-JVM proxy session using composition."""

    dbg_sender: JdwpPacketSender
    dbg_receiver: JdwpPacketReceiver
    vm_sender: JdwpPacketSender
    vm_receiver: JdwpPacketReceiver
    spec: IdSizesSpec
    idsizes_cmd_ids: set[int]
    close_event: asyncio.Event

    def __init__(
        self,
        dbg_sender: JdwpPacketSender,
        dbg_receiver: JdwpPacketReceiver,
        vm_sender: JdwpPacketSender,
        vm_receiver: JdwpPacketReceiver,
    ) -> None:
        self.dbg_sender = dbg_sender
        self.dbg_receiver = dbg_receiver
        self.vm_sender = vm_sender
        self.vm_receiver = vm_receiver
        self.spec = IdSizesSpec.create()  # Default standard 8-byte ID spec
        self.idsizes_cmd_ids = set()
        self.close_event = asyncio.Event()

    @classmethod
    async def create(
        cls,
        dbg_reader: asyncio.StreamReader,
        dbg_writer: asyncio.StreamWriter,
        target_host: str,
        target_port: int,
    ) -> Self:
        """Factory method that establishes JVM connections and runs bi-directional handshakes."""
        # 1. Connect to JVM JDWP agent and run handshake
        vm_sender, vm_receiver = await establish_jdwp_connection(
            target_host, target_port
        )
        print(f"[*] Connected to target JVM at {target_host}:{target_port}")

        # 2. Negotiate debugger client handshake
        dbg_handshake = await dbg_reader.readexactly(len(HANDSHAKE))
        if dbg_handshake != HANDSHAKE:
            raise RuntimeError(
                f"Debugger client sent invalid handshake signature: {dbg_handshake!r}"
            )
        dbg_writer.write(HANDSHAKE)
        await dbg_writer.drain()
        print("[*] Bi-directional JDWP Handshake completed successfully!")

        # 3. Initialize wrapper objects
        dbg_sender = JdwpPacketSender(dbg_writer)
        dbg_receiver = JdwpPacketReceiver(dbg_reader)

        return cls(dbg_sender, dbg_receiver, vm_sender, vm_receiver)

    async def _handle_debugger_packet(self, packet: JdwpPacket) -> None:
        """Processes and logs command packets sent from Debugger to VM."""
        if isinstance(packet, JdwpCommandPacket):
            if packet.command_set == 1 and packet.command == 7:
                self.idsizes_cmd_ids.add(packet.id)

        await self.vm_sender.send_packet(packet)
        self._log_packet(packet, "Debugger -> VM")

    async def _handle_vm_packet(self, packet: JdwpPacket) -> None:
        """Processes, logs, and intercepts IDSizes responses sent from VM to Debugger."""
        if isinstance(packet, JdwpReplyPacket):
            if packet.id in self.idsizes_cmd_ids:
                self.idsizes_cmd_ids.remove(packet.id)
                if packet.error_code == 0:
                    resp = IDSizesResponse.from_bytes(packet.data, self.spec)
                    self.spec = IdSizesSpec.from_response(resp)
                    print(
                        f"\033[93m[*] Proxy intercepted IDSizes Reply - Dynamically updated Spec:\n"
                        f"    field={resp.field_id_size} method={resp.method_id_size} "
                        f"object={resp.object_id_size} refType={resp.reference_type_id_size} "
                        f"frame={resp.frame_id_size}\033[0m"
                    )

        await self.dbg_sender.send_packet(packet)
        self._log_packet(packet, "VM -> Debugger")

    async def _handle_debugger_exception(self, exc: Exception) -> None:
        """Handles debugger socket read failure by logging and triggering shutdown."""
        if isinstance(exc, asyncio.IncompleteReadError):
            print("[*] Debugger client closed connection.")
        else:
            print(f"[-] Debugger client connection error: {exc}", file=sys.stderr)
        self.close_event.set()

    async def _handle_vm_exception(self, exc: Exception) -> None:
        """Handles VM socket read failure by logging and triggering shutdown."""
        if isinstance(exc, asyncio.IncompleteReadError):
            print("[*] Target JVM closed connection.")
        else:
            print(f"[-] Target JVM connection error: {exc}", file=sys.stderr)
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

    def _log_packet(self, packet: JdwpPacket, label: str) -> None:
        arrow = ">>>" if "Debugger" in label else "<<<"
        color_start = "\033[92m" if "Debugger" in label else "\033[94m"
        color_end = "\033[0m"

        if isinstance(packet, JdwpCommandPacket):
            cmd_cls = get_command_class(packet.command_set, packet.command)
            cmd_name = (
                cmd_cls.__name__
                if cmd_cls
                else f"UnknownCmd({packet.command_set}:{packet.command})"
            )
            print(
                f"{color_start}{arrow} [Command]{color_end} "
                f"ID: {packet.id:<4} | {cmd_name:<18} | Set: {packet.command_set:<2} Cmd: {packet.command:<2} | "
                f"Payload: {len(packet.data):<3} bytes"
            )
        elif isinstance(packet, JdwpReplyPacket):
            err_val = packet.error_code
            err_enum = (
                JdwpErrorCode(err_val)
                if err_val in JdwpErrorCode.__members__.values()
                else None
            )
            err_name = err_enum.name if err_enum else f"Unknown({err_val})"
            print(
                f"{color_start}{arrow} [Reply  ]{color_end} "
                f"ID: {packet.id:<4} | Error: {err_name:<18} | Code: {err_val:<4} | "
                f"Payload: {len(packet.data):<3} bytes"
            )


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
    args = parser.parse_args()

    print(f"[*] Starting JDWP Logging Proxy on port {args.listen_port}...")
    print(
        f"[*] Forwarding traffic to JVM JDWP agent at {args.target_host}:{args.target_port}"
    )

    async def client_connected(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        peer = writer.get_extra_info("peername")
        print(f"[*] Accepted debugger client connection from {peer}")
        try:
            session = await JdwpProxySession.create(
                reader, writer, args.target_host, args.target_port
            )
            await session.run()
        except Exception as e:
            print(f"[-] Session error in {peer}: {e}", file=sys.stderr)
            writer.close()
            await writer.wait_closed()
        finally:
            print(f"[*] Session closed for client {peer}")

    server = await asyncio.start_server(client_connected, "127.0.0.1", args.listen_port)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Proxy server terminated by user.")
