import asyncio
import json
from meshcore import MeshCore, EventType

SERIAL_PORT = "/dev/ttyUSB0"

async def main():
    meshcore = await MeshCore.create_serial(SERIAL_PORT, debug=True)
    print(f"Connected on {SERIAL_PORT}")
    await meshcore.start_auto_message_fetching()

    contacts = {}
    short_to_name = {}

    result = await meshcore.commands.get_contacts()
    if result.type != EventType.ERROR and result.payload:
        contacts = result.payload
        print(f"Cached {len(contacts)} contacts")

        for full_key, contact in contacts.items():
            name = contact.get("adv_name")
            if name:
                short = full_key[:12]
                short_to_name[short] = name
                short_to_name[full_key[:8]] = name

    async def debug_handler(event):
        print(f"\n{'='*80}")
        print(f"EVENT: {event.type}")
        print(f"{'='*80}")

        payload = event.payload or {}
        print("RAW PAYLOAD:")
        print(json.dumps(payload, indent=2, default=str))

        text = payload.get("text", "").strip()
        pubkey_prefix = payload.get("pubkey_prefix")
        signature = payload.get("signature")

        print(f"\nMESSAGE TEXT: {text}")

        sender = "unknown"
        if signature and signature in short_to_name:
            sender = short_to_name[signature]
        elif pubkey_prefix and pubkey_prefix in short_to_name:
            sender = short_to_name[pubkey_prefix]

        print(f"RESOLVED SENDER: {sender}")
        print(f"PUBKEY PREFIX : {pubkey_prefix}")
        print(f"SIGNATURE     : {signature}")

        if "@bot" in text.lower():
            print(">>> @bot TRIGGERED <<<")

        print(f"{'='*80}\n")

    meshcore.subscribe(EventType.CONTACT_MSG_RECV, debug_handler)
    meshcore.subscribe(EventType.CHANNEL_MSG_RECV, debug_handler)

    try:
        print("Debug listener running...")
        await asyncio.sleep(float('inf'))
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        await meshcore.stop_auto_message_fetching()
        await meshcore.disconnect()

asyncio.run(main())