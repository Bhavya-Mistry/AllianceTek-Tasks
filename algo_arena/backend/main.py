from fastapi import FastAPI, Query, HTTPException
import json
from typing import Optional, List, Any, Dict
from pydantic import BaseModel
import uuid
import random
from datetime import datetime
import socketio

# =====================================================
# APP
# =====================================================
app = FastAPI()

# create socket IO server
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, app)

# =====================================================
# MODELS
# =====================================================


# What a problem summary looks like
class ProblemSummary(BaseModel):
    id: str
    title: str
    difficulty: str


# This is fancy code for a "Dictionary." It means the input will look like { "name": "value" }. The Any part just means the value could be a string, a number, or a list.
# This is the correct answer. It can be anything (a string, a number, a boolean).
class TestCase(BaseModel):
    input: Dict[str, Any]
    expected: Any


class Player(BaseModel):
    username: str


class ProblemShort(BaseModel):
    id: str
    title: str
    difficulty: str


class PlayerStatus(BaseModel):
    username: str
    joined_at: datetime


# =====================================================
# REQUEST MODELS
# =====================================================


class CreateRoomRequest(BaseModel):
    username: str
    difficulty: str
    time_limit_sec: int = 600


class JoinRoomRequest(BaseModel):
    username: str


# =====================================================
# RESPONSE MODELS
# =====================================================


# Define the structure of the final response
class ProblemResponse(BaseModel):
    items: List[ProblemSummary]
    count: int


class ProblemDetailsResponse(BaseModel):
    id: str
    title: str
    difficulty: str
    description: str
    starter_code: str
    public_tests: List[TestCase]


class RoomResponse(BaseModel):
    room_id: str
    status: str
    time_limit_sec: int
    problem: ProblemShort
    players: List[Player]


class RoomStatusResponse(BaseModel):
    room_id: str
    status: str
    created_at: datetime
    time_limit_sec: int
    problem: ProblemShort
    players: List[PlayerStatus]


# =====================================================
# DATA
# =====================================================
with open("problems.json", "r") as f:
    problems_db = json.load(f)


rooms_db = {}

online_users = {}


# =====================================================
# ENDPOINTS
# =====================================================
@app.get("/health")
def health():
    return {"Status": "Ok", "Service": "algoarena-backend"}


@app.get("/problems", response_model=ProblemResponse)
def get_problems(difficulty: Optional[str] = None, limit: int = 10):
    filtered_items = []

    for i in problems_db:
        # filtering logic
        if difficulty and i["difficulty"] != difficulty.lower():
            continue

        filtered_items.append(i)

        if len(filtered_items) >= limit:
            break

    return {"items": filtered_items, "count": len(filtered_items)}


@app.get("/problems/{problem_id}", response_model=ProblemDetailsResponse)
def get_problem_by_id(problem_id: str):
    # search for the problem in our database

    for i in problems_db:
        if i["id"] == problem_id:
            return i

    raise HTTPException(status_code=404, detail="Problem not found")


@app.post("/rooms", response_model=RoomStatusResponse, status_code=201)
def create_room(request: CreateRoomRequest):
    # pick a random problem matchin the difficulty
    matching_problems = [
        i for i in problems_db if i["difficulty"] == request.difficulty.lower()
    ]

    if not matching_problems:
        raise HTTPException(
            status_code=404, detail="No problems found for this difficuly"
        )

    selected_problem = random.choice(matching_problems)

    # generate room id
    room_id = str(uuid.uuid4())[:8]  # Short unique ID like 'a1b2c3d4'

    # create the room object
    new_room = {
        "room_id": room_id,
        "status": "waiting",
        "created_at": datetime.now(),
        "time_limit_sec": request.time_limit_sec,
        "problem": selected_problem,
        "players": [{"username": request.username, "joined_at": datetime.now()}],
    }

    rooms_db[room_id] = new_room

    return new_room


@app.post("/rooms/{room_id}/join", response_model=RoomStatusResponse)
def join_room(room_id: str, request: JoinRoomRequest):

    # check if room exits
    if room_id not in rooms_db:
        raise HTTPException(status_code=404, detail="Room not found")

    room = rooms_db[room_id]

    # check if full
    if len(room["players"]) >= 2:
        raise HTTPException(status_code=409, detail="Room full")

    # add second player
    room["players"].append({"username": request.username, "joined_at": datetime.now()})

    room["status"] = "active"

    return room


@app.get("/rooms/{room_id}", response_model=RoomStatusResponse)
def get_room_status(room_id: str):
    # look for room
    if room_id not in rooms_db:
        raise HTTPException(status_code=404, detail="Room not found")

    return rooms_db[room_id]


# =====================================================
# SOCKETS
# =====================================================


@sio.event
async def connect(sid, environ):
    print(f"New Connection attempt: {sid}")


@sio.event
async def identify(sid, data):
    username = data.get("username")

    if not username:
        return await sio.emit("error", {"detail": "Username is required"}, to=sid)

    # save username into socket's session (memory)
    await sio.save_session(sid, {"username": username})

    # track them globally for logging
    online_users[sid] = username

    print(f"[LOG] Socket {sid} identified as {username}")

    # respond back to the user
    await sio.emit("identified", {"ok": True, "username": username}, to=sid)


@sio.event
async def join_room(sid, data):
    room_id = data.get("room_id")
    session = await sio.get_session(sid)
    username = session.get("username")

    if not username:
        await sio.emit("error", {"detail": "You must identify first!"}, to=sid)
        return

    if room_id not in rooms_db:
        await sio.emit("error", {"detail": "Room not found"}, to=sid)
        return

    room = rooms_db[room_id]
    player_names = [p["username"] for p in room["players"]]

    if username not in player_names:
        if len(room["players"]) >= 2:
            await sio.emit("error", {"detail": "Room is full"}, to=sid)
            return
        room["players"].append({"username": username, "joined_at": datetime.now()})

    # IMPORTANT: Update the session to include room_id so disconnect works!
    await sio.save_session(sid, {"username": username, "room_id": room_id})

    sio.enter_room(sid, room_id)

    if len(room["players"]) == 2:
        room["status"] = "active"

    update_payload = {
        "room_id": room_id,
        "status": room["status"],
        "players": [p["username"] for p in room["players"]],
    }

    print(f"[LOG] {username} joined room {room_id}. Status: {room['status']}")
    await sio.emit("room_update", update_payload, room=room_id)


@sio.event
async def disconnect(sid):
    session = await sio.get_session(sid)
    username = session.get("username", "Unknown")
    room_id = session.get("room_id")

    print(f"[LOG] {username} disconnected from room {room_id}")

    if room_id and room_id in rooms_db:
        room = rooms_db[room_id]
        old_status = room["status"]  # Remember what it was

        # Remove the player
        room["players"] = [p for p in room["players"] if p["username"] != username]

        if len(room["players"]) == 0:
            room["status"] = "abandoned"
        else:
            # Logic Change:
            if old_status == "active":
                # If they were mid-game, don't let a new person join an old match
                room["status"] = "abandoned"
            else:
                # If they were just waiting in the lobby, stay in waiting mode
                room["status"] = "waiting"

        # Notify the survivor
        await sio.emit(
            "room_update",
            {
                "room_id": room_id,
                "status": room["status"],
                "players": [p["username"] for p in room["players"]],
                "message": f"Opponent {username} disconnected. Room is now {room['status']}.",
            },
            room=room_id,
        )
