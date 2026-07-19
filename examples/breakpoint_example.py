#!/usr/bin/env python3
"""Example: Setting a Breakpoint and Reading Local Variables

To run this example:
1. Compile the target app:
   javac -g tests/testdata/SimpleApp.java -d classes

2. Start the JVM with JDWP agent suspended on port 8000:
   java -agentlib:jdwp=transport=dt_socket,server=y,suspend=y,address=127.0.0.1:8000 -cp classes SimpleApp

3. Run the example:
   uv run examples/breakpoint_example.py
"""

from __future__ import annotations
import asyncio
import sys
from jdwpy import (
    JdwpConnection,
    JdwpEventKind,
    JdwpSuspendPolicy,
    JdwpTag,
    Location,
    ThreadID,
)
from jdwpy.commands import (
    vm,
    event_request,
    reference_type,
    method,
    stack_frame,
    thread_reference,
    event,
)


async def main() -> None:
    print("[*] Connecting to JDWP agent on 127.0.0.1:8000...")
    try:
        async with await JdwpConnection.connect("127.0.0.1", 8000) as conn:
            print("[+] Connected! Consuming startup events...")

            # 1. Read VMStartEvent and configure ID sizes
            await conn.receive_command()
            await conn.send_command(vm.IDSizesCommand())

            # 2. Register for ClassPrepare event of "SimpleApp"
            print("[*] Registering for ClassPrepare of 'SimpleApp'...")
            await conn.send_command(
                event_request.SetCommand(
                    event_kind=JdwpEventKind.CLASS_PREPARE,
                    suspend_policy=JdwpSuspendPolicy.ALL,
                    modifiers=[
                        event_request.ClassMatchModifier(class_pattern="SimpleApp")
                    ],
                )
            )

            # 3. Resume the VM so it can load classes
            print("[*] Resuming VM to allow class preparation...")
            await conn.send_command(vm.ResumeCommand())

            # 4. Wait for ClassPrepare event
            composite = await conn.receive_command()
            assert isinstance(composite, event.CompositeCommand)
            prep_event = composite.events[0]
            assert isinstance(prep_event, event.ClassPrepareEvent)
            class_id = prep_event.type_id
            print(f"[+] Class prepared: SimpleApp (Type ID: {class_id})")

            # 5. Find the method ID of "testMethod"
            print("[*] Querying class methods...")
            methods_resp = await conn.send_command(
                reference_type.MethodsCommand(ref_type=class_id)
            )
            test_method = next(
                m for m in methods_resp.methods if m.name == "testMethod"
            )
            print(
                f"[+] Method found: {test_method.name} (Method ID: {test_method.method_id})"
            )

            # 6. Locate local variable "iteration" in the method's variable table
            print("[*] Querying method variable table...")
            var_table_resp = await conn.send_command(
                method.VariableTableCommand(
                    ref_type=class_id, method=test_method.method_id
                )
            )
            iteration_var = next(
                v for v in var_table_resp.slots if v.name == "iteration"
            )
            print(f"[+] Variable slot found: iteration (Slot: {iteration_var.slot})")

            # 7. Set breakpoint at instruction index 0 of "testMethod"
            print("[*] Setting breakpoint at testMethod:0...")
            bp_loc = Location(
                type_tag=prep_event.ref_type_tag,
                class_id=class_id,
                method_id=test_method.method_id,
                index=0,
            )
            await conn.send_command(
                event_request.SetCommand(
                    event_kind=JdwpEventKind.BREAKPOINT,
                    suspend_policy=JdwpSuspendPolicy.ALL,
                    modifiers=[event_request.LocationOnlyModifier(loc=bp_loc)],
                )
            )

            # 8. Resume the VM and run until the breakpoint is hit
            print("[*] Resuming VM to trigger breakpoint...")
            await conn.send_command(vm.ResumeCommand())

            # 9. Wait for Breakpoint Event
            bp_composite = await conn.receive_command()
            assert isinstance(bp_composite, event.CompositeCommand)
            bp_event = bp_composite.events[0]
            assert isinstance(bp_event, event.BreakpointEvent)
            thread_id = ThreadID(bp_event.thread)
            print(f"[+] Breakpoint hit on thread: {thread_id}")

            # 10. Query thread call stack frames
            frames_resp = await conn.send_command(
                thread_reference.FramesCommand(
                    thread=thread_id, start_frame=0, length=1
                )
            )
            top_frame = frames_resp.frames[0]
            print(f"[+] Top stack frame: {top_frame.frame_id}")

            # 11. Read local variable value
            print("[*] Reading value of variable 'iteration'...")
            val_resp = await conn.send_command(
                stack_frame.GetValuesCommand(
                    thread=thread_id,
                    frame=top_frame.frame_id,
                    slots=[
                        stack_frame.GetValuesRequestSlot(
                            slot=iteration_var.slot,
                            sig_byte=JdwpTag.INT,
                        )
                    ],
                )
            )
            iteration_value = val_resp.values[0].value
            print(f"[+] Value of 'iteration': {iteration_value}")

            # 12. Resume the VM and exit
            print("[*] Cleaning up and resuming VM...")
            await conn.send_command(vm.ResumeCommand())
            print("[*] Done!")

    except Exception as e:
        print(f"[-] Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
