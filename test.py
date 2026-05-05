import asyncio
from meshcore import MeshCore, EventType
from ai.clients import XAIClient

SERIAL_PORT = "/dev/ttyUSB0"
ROOM_CONTACT_NAME = "Maplewood Room"

# Character limit for messages - Leave room for split message numbering (e.g [1/5])
# Saw bug for messages longer than 120 failed to repeat in scoped channels. Watch and if still present, reduce to 110.
MAX_MSG_CHARS = 120

# Use xAi client for now TODO: ping for network heartbeat at (k) interval and add ollama fallback if fail
agent_client = XAIClient()
agent_system_instructions = "You are a helpful AI assistant named Juliet. You operate on a private MeshCore mesh network based out of Franklin, TN. Your network has very limited bandwidth and message length. Your responses must be short, concise and honest at all times."


def split_response(text: str, sender: str, max_chars: int = MAX_MSG_CHARS) -> list[str]:
    """
    Split a long response into numbered MeshCore-length-compliant messages.
    """
    prefix = f"@[{sender}] "
    # Reserve space for the numbering: " [1/5] " (reserve 10?)
    available_chars = max_chars - len(prefix) - 10

    if not text or len(text.strip()) <= available_chars:
        return [prefix + text.strip()]

    words = text.split()
    parts = []           # List of text parts (without prefix or numbering yet)
    current = []

    for word in words:
        test_line = " ".join(current + [word])
        if len(test_line) > available_chars:
            if current:
                parts.append(" ".join(current))
            current = [word]
        else:
            current.append(word)

    if current:
        parts.append(" ".join(current))

    total = len(parts)
    numbered_messages = []

    for i, part_text in enumerate(parts, 1):
        numbering = f"[ {i}/{total} ] "
        final_message = prefix + numbering + part_text
        numbered_messages.append(final_message)

    return numbered_messages

# def dep_split_response(text: str, sender: str, max_chars: int = MAX_MSG_CHARS) -> list[str]:
#     """Split a long response into multiple numbered MeshCore-safe messages."""
#     prefix = f"@[{sender}] "
#     available = max_chars - len(prefix) - 8

#     if not text or len(text) <= available:
#         return [prefix + text.strip()]

#     parts = []
#     words = text.split()
#     current = []
#     part_num = 1
#     total_parts = 1

#     for word in words:
#         test_line = " ".join(current + [word])
#         if len(test_line) > available:
#             # Save current part
#             part_text = f"[ {part_num}/{total_parts} ] " + " ".join(current)
#             parts.append(prefix + part_text)
#             current = [word]
#             part_num += 1
#         else:
#             current.append(word)

#     if current:
#         part_text = f"[ {part_num}/{total_parts} ] " + " ".join(current)
#         parts.append(prefix + part_text)

#     # TODO: this is crap, need to redo. Probably need to pre-split everything and return completed list..
#     total_parts = len(parts)
#     fixed_parts = []
#     for i, msg in enumerate(parts, 1):
#         fixed = msg.replace(f"/{total_parts} ", f"/{total_parts} ", 1)
#         fixed_parts.append(msg.replace(f"[ {i}/", f"[ {i}/", 1))

#     return fixed_parts


async def main():
    """Main Agent Loop"""
    # TODO: add emojis to serial prints for visibility
    meshcore = await MeshCore.create_serial(SERIAL_PORT, debug=True)
    print(f"✅ Connected on {SERIAL_PORT}")
    await meshcore.start_auto_message_fetching()

    # Contact caching & room resolution
    contacts = {}
    short_to_name = {}

    result = await meshcore.commands.get_contacts()
    if result.type != EventType.ERROR and result.payload:
        contacts = result.payload
        print(f"Cached {len(contacts)} contacts")

        for full_key, contact in contacts.items():
            name = contact.get("adv_name")
            if name:
                short_to_name[full_key[:12]] = name
                short_to_name[full_key[:8]] = name

    room_contact = None
    for key, contact in contacts.items():
        if ROOM_CONTACT_NAME.lower() in contact.get("adv_name", "").lower():
            room_contact = contact
            print(f"✅ Found room contact: {contact.get('adv_name')} ({key})")
            break

    if not room_contact:
        print("❌ Room contact not found!")
        return

    async def handle_message(event):
        if event.type not in (EventType.CONTACT_MSG_RECV, EventType.CHANNEL_MSG_RECV):
            return

        msg = event.payload
        raw_text = msg.get("text", "").strip()
        pubkey_prefix = msg.get("pubkey_prefix")
        signature = msg.get("signature")

        # Sender resolution
        sender = "unknown"
        if signature and signature in short_to_name:
            sender = short_to_name[signature]
        elif pubkey_prefix and pubkey_prefix in short_to_name:
            sender = short_to_name[pubkey_prefix]

        print(f"📥 [{event.type}] from {sender}: {raw_text}")

        # Trigger with @! to save message characters
        if "@!" not in raw_text.lower():
            return

        user_prompt = raw_text
        print(f"🤖 Prompt received: {user_prompt}")

        ### Get AI response
        messages = [
            {"role": "system", "content": agent_system_instructions},
            {"role": "user", "content": user_prompt},
        ]

        try:
            agent_response = agent_client.get_response(
                model="grok-4-1-fast-non-reasoning",
                messages=messages
            )
            full_reply = agent_response.strip()
            print(f"\n🤖 Juliet Response:\n{full_reply}\n")
        except Exception as e:
            print(f"AI Error: {e}")
            full_reply = "Sorry, I had trouble reaching my brain."

        ### Split and send. TODO: add a small delay between parts to avoid loss
        messages_to_send = split_response(full_reply, sender, MAX_MSG_CHARS)

        print(f"📤 Sending {len(messages_to_send)} part(s) to room...")

        for part in messages_to_send:
            result = await meshcore.commands.send_msg(room_contact, part)
            if result.type == EventType.ERROR:
                print(f"❌ Send failed: {result.payload}")
            else:
                print(f"✅ Sent: {part[:80]}...")
            ### Delay Timing - too short and some messages skip
            await asyncio.sleep(1.5)

    meshcore.subscribe(EventType.CONTACT_MSG_RECV, handle_message)
    meshcore.subscribe(EventType.CHANNEL_MSG_RECV, handle_message)

    try:
        print(f"👂 Juliet is listening for '@!' in '{ROOM_CONTACT_NAME}'...")
        await asyncio.sleep(float('inf'))
    except (asyncio.CancelledError, KeyboardInterrupt):
        print("\n🛑 Shutting down...")
    finally:
        print("Cleaning up...")
        await meshcore.stop_auto_message_fetching()
        await meshcore.disconnect()
        print("✅ Disconnected.")

asyncio.run(main())