#!/usr/bin/env python3
"""Example: Get JVM Version

To run this example:
1. Compile the target app:
   javac -g tests/testdata/SimpleApp.java -d classes

2. Start the JVM with JDWP agent suspended on port 8000:
   java -agentlib:jdwp=transport=dt_socket,server=y,suspend=y,address=127.0.0.1:8000 -cp classes SimpleApp

3. Run the example:
   uv run examples/get_version.py
"""

from __future__ import annotations
import asyncio
import sys
from jdwpy import JdwpConnection
from jdwpy.commands import vm


async def main() -> None:
    print("[*] Connecting to JDWP agent on 127.0.0.1:8000...")
    try:
        async with await JdwpConnection.connect("127.0.0.1", 8000) as conn:
            print("[+] Connected!")

            # 1. Consume the initial VMStartEvent (VM is suspended-on-start)
            print("[*] Waiting for VMStartEvent...")
            start_event = await conn.receive_command()
            print(start_event)

            # 2. Negotiate dynamic JDWP ID sizes
            print("[*] Configuring dynamic ID sizes...")
            id_sizes = await conn.send_command(vm.IDSizesCommand())
            print(id_sizes)

            # 3. Retrieve VM version information
            print("[*] Fetching VM version...")
            version = await conn.send_command(vm.VersionCommand())
            print(version)

            # 4. Retrieve VM capabilities
            print("[*] Fetching VM capabilities...")
            capabilities = await conn.send_command(vm.CapabilitiesCommand())
            print(capabilities)

            # 5. Resume the VM
            print("[*] Resuming JVM debuggee...")
            await conn.send_command(vm.ResumeCommand())
            print("[+] VM Resumed.")

    except Exception as e:
        print(f"[-] Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
