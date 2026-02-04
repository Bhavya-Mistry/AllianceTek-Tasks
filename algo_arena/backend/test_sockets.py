"""
AlgoArena Socket.IO Testing Script
Tests real-time multiplayer functionality
"""

import socketio
import asyncio
import time

BASE_URL = "http://localhost:8000"

# =====================================================
# TEST SOCKET FUNCTIONALITY
# =====================================================


async def test_socket_flow():
    print("\n" + "=" * 60)
    print("  SOCKET.IO REAL-TIME TESTS")
    print("=" * 60 + "\n")

    # Create two clients (two players)
    client1 = socketio.AsyncClient()
    client2 = socketio.AsyncClient()

    # Track events
    events_log = []

    # Event handlers for Client 1
    @client1.event
    async def connect():
        events_log.append("Client1: Connected")
        print("✅ Client 1 (Alice) connected")

    @client1.event
    async def identified(data):
        events_log.append(f"Client1: Identified as {data}")
        print(f"✅ Client 1 identified: {data}")

    @client1.event
    async def room_update(data):
        events_log.append(f"Client1: Room update - {data}")
        print(f"📢 Client 1 received room update: {data}")

    @client1.event
    async def error(data):
        events_log.append(f"Client1: Error - {data}")
        print(f"❌ Client 1 error: {data}")

    # Event handlers for Client 2
    @client2.event
    async def connect():
        events_log.append("Client2: Connected")
        print("✅ Client 2 (Bob) connected")

    @client2.event
    async def identified(data):
        events_log.append(f"Client2: Identified as {data}")
        print(f"✅ Client 2 identified: {data}")

    @client2.event
    async def room_update(data):
        events_log.append(f"Client2: Room update - {data}")
        print(f"📢 Client 2 received room update: {data}")

    @client2.event
    async def error(data):
        events_log.append(f"Client2: Error - {data}")
        print(f"❌ Client 2 error: {data}")

    try:
        # Step 1: Connect both clients
        print("\n[STEP 1] Connecting clients...")
        await client1.connect(BASE_URL)
        await client2.connect(BASE_URL)
        await asyncio.sleep(1)

        # Step 2: Identify users
        print("\n[STEP 2] Identifying users...")
        await client1.emit("identify", {"username": "Alice"})
        await client2.emit("identify", {"username": "Bob"})
        await asyncio.sleep(1)

        # Step 3: Create room via HTTP (you'd do this first)
        print("\n[STEP 3] Create a room via HTTP first (use test_algoarena.py)")
        print("Then enter the room_id here...")
        room_id = input("Enter room_id: ").strip()

        # Step 4: Alice joins room
        print(f"\n[STEP 4] Alice joining room {room_id}...")
        await client1.emit("join_room", {"room_id": room_id})
        await asyncio.sleep(1)

        # Step 5: Bob joins room
        print(f"\n[STEP 5] Bob joining room {room_id}...")
        await client2.emit("join_room", {"room_id": room_id})
        await asyncio.sleep(2)

        # Step 6: Simulate Alice disconnecting
        print("\n[STEP 6] Alice disconnecting...")
        await client1.disconnect()
        await asyncio.sleep(2)

        # Step 7: Bob should receive update
        print("\n[STEP 7] Bob should see room status change...")
        await asyncio.sleep(1)

        print("\n" + "=" * 60)
        print("  EVENT LOG")
        print("=" * 60)
        for event in events_log:
            print(event)

    except Exception as e:
        print(f"\n❌ Error during socket test: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        if client1.connected:
            await client1.disconnect()
        if client2.connected:
            await client2.disconnect()
        print("\n✅ Test complete")


# =====================================================
# SIMPLER MANUAL TEST
# =====================================================


async def simple_socket_test():
    """Simpler test - just connect and identify"""
    print("\n🔌 Simple Socket Test - Connect & Identify")

    client = socketio.AsyncClient()

    @client.event
    async def connect():
        print("✅ Connected to server")

    @client.event
    async def identified(data):
        print(f"✅ Identified: {data}")

    @client.event
    async def error(data):
        print(f"❌ Error: {data}")

    try:
        await client.connect(BASE_URL)
        await asyncio.sleep(1)

        await client.emit("identify", {"username": "TestUser"})
        await asyncio.sleep(2)

        await client.disconnect()

    except Exception as e:
        print(f"❌ Error: {e}")


# =====================================================
# RUN TESTS
# =====================================================

if __name__ == "__main__":
    print("Choose test:")
    print("1. Simple connection test")
    print("2. Full room flow test")
    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "1":
        asyncio.run(simple_socket_test())
    else:
        asyncio.run(test_socket_flow())
