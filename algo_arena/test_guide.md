# AlgoArena Backend - Testing Guide

## What You Built

A **real-time competitive coding platform** where:

- Players create/join rooms to compete 1v1
- Each room has a randomly selected coding problem
- Real-time updates via WebSockets when players join/leave
- REST API for room management and problem browsing

---

## Prerequisites

1. **Install dependencies:**

```bash
pip install fastapi uvicorn python-socketio aiohttp requests
```

2. **Ensure you have `problems.json`** in the same directory as your main file

---

## How to Run

1. **Start the server:**

```bash
# If your main file is named main.py
uvicorn main:socket_app --reload --port 8000

# Note: Use 'socket_app' not 'app' because of Socket.IO wrapper
```

2. **Verify it's running:**
   Open browser to: http://localhost:8000/health

Should see: `{"Status":"Ok","Service":"algoarena-backend"}`

---

## Manual Testing

### Option 1: REST API Tests (Automated)

```bash
python test_algoarena.py
```

This will test:

- ✅ Health check
- ✅ List problems
- ✅ Filter by difficulty
- ✅ Get problem details
- ✅ Create room
- ✅ Join room
- ✅ Error handling

### Option 2: Manual curl Commands

**1. Health Check:**

```bash
curl http://localhost:8000/health
```

**2. Get Problems:**

```bash
# All problems
curl http://localhost:8000/problems

# Easy problems only
curl "http://localhost:8000/problems?difficulty=easy&limit=3"
```

**3. Get Specific Problem:**

```bash
# Replace with actual problem ID from problems.json
curl http://localhost:8000/problems/two-sum
```

**4. Create Room:**

```bash
curl -X POST http://localhost:8000/rooms \
  -H "Content-Type: application/json" \
  -d '{
    "username": "Alice",
    "difficulty": "easy",
    "time_limit_sec": 600
  }'
```

**Save the `room_id` from response!**

**5. Join Room:**

```bash
# Replace ROOM_ID with actual room_id from step 4
curl -X POST http://localhost:8000/rooms/ROOM_ID/join \
  -H "Content-Type: application/json" \
  -d '{
    "username": "Bob"
  }'
```

**6. Check Room Status:**

```bash
curl http://localhost:8000/rooms/ROOM_ID
```

---

## Socket.IO Testing

### Option 1: Automated Socket Test

```bash
python test_sockets.py
```

Choose option 1 for simple test, option 2 for full flow.

### Option 2: Browser Testing

Create `test.html`:

```html
<!DOCTYPE html>
<html>
  <head>
    <title>AlgoArena Socket Test</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
  </head>
  <body>
    <h1>AlgoArena Socket.IO Test</h1>
    <div id="status"></div>
    <div id="log"></div>

    <script>
      const socket = io("http://localhost:8000");
      const log = document.getElementById("log");
      const status = document.getElementById("status");

      function addLog(msg) {
        const div = document.createElement("div");
        div.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
        log.appendChild(div);
      }

      socket.on("connect", () => {
        addLog("✅ Connected!");
        status.textContent = "Status: Connected";

        // Identify yourself
        socket.emit("identify", { username: "TestUser" });
      });

      socket.on("identified", (data) => {
        addLog(`✅ Identified as: ${data.username}`);

        // Try to join a room (replace with actual room_id)
        const roomId = prompt("Enter room ID to join:");
        if (roomId) {
          socket.emit("join_room", { room_id: roomId });
        }
      });

      socket.on("room_update", (data) => {
        addLog(`📢 Room Update: ${JSON.stringify(data)}`);
      });

      socket.on("error", (data) => {
        addLog(`❌ Error: ${data.detail}`);
      });

      socket.on("disconnect", () => {
        addLog("🔌 Disconnected");
        status.textContent = "Status: Disconnected";
      });
    </script>
  </body>
</html>
```

Open in browser and follow prompts.

---

## Expected Behaviors

### Room Lifecycle

1. **Player 1 creates room** → Status: `waiting`
2. **Player 2 joins** → Status: `active` (both players get `room_update`)
3. **Someone disconnects:**
   - If during `waiting`: Room stays `waiting`
   - If during `active`: Room becomes `abandoned`

### Socket Events Flow

```
Client connects → emit 'identify' → receive 'identified'
                                   ↓
                          emit 'join_room' → receive 'room_update'
                                   ↓
                          Other player joins → both receive 'room_update'
                                   ↓
                          Player leaves → remaining player gets 'room_update'
```

---

## Common Issues

**Issue:** `ModuleNotFoundError: No module named 'socketio'`
**Fix:** `pip install python-socketio`

**Issue:** `uvicorn: error: unrecognized arguments: socket_app`
**Fix:** Use `uvicorn main:socket_app` (not `uvicorn main:app`)

**Issue:** Room not found
**Fix:** Make sure you're using the exact `room_id` returned from create room

**Issue:** Socket won't connect
**Fix:** Check CORS settings and ensure server is running on correct port

---

## Next Phase Ideas

Based on your MVP, here are suggestions:

1. **Code Submission & Testing**
   - Add endpoint to submit code
   - Run code against test cases
   - Return pass/fail results

2. **Real-time Code Sync**
   - Socket event for code updates
   - Show opponent's progress

3. **Winner Determination**
   - Track who solves first
   - Calculate scores

4. **Persistence**
   - Use actual database (PostgreSQL/MongoDB)
   - Store game history
   - User authentication

5. **Room Management**
   - Auto-cleanup abandoned rooms
   - Reconnection logic
   - Spectator mode

---

## Architecture Summary

```
Client (Browser/App)
       │
       ├─── REST API ───────► FastAPI endpoints
       │                      └─► /problems, /rooms
       │
       └─── WebSocket ──────► Socket.IO
                              └─► Real-time room updates
```

**In-Memory Storage:**

- `problems_db`: All coding problems
- `rooms_db`: Active game rooms
- `online_users`: Connected socket users

---

Good luck with your next phase! 🚀
