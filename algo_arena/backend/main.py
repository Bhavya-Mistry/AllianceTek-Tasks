from fastapi import FastAPI, Query, HTTPException
import json
from typing import Optional, List, Any, Dict
from pydantic import BaseModel
import uuid
import random
from datetime import datetime
import socketio
import httpx
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware

# =====================================================
# APP
# =====================================================
app = FastAPI()
load_dotenv()


app = FastAPI()

# Add this block!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (POST, GET, etc.)
    allow_headers=["*"],  # Allows all headers
)


# =====================================================
# MODELS
# =====================================================
class TestResults(BaseModel):
    input: Any
    expected: Any
    actual: Any
    passed: bool


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
class SubmissionRequest(BaseModel):
    username: str
    code: str


class CreateRoomRequest(BaseModel):
    username: str
    difficulty: str
    time_limit_sec: int = 600


class JoinRoomRequest(BaseModel):
    username: str


# =====================================================
# RESPONSE MODELS
# =====================================================
class SubmissionResponse(BaseModel):
    submission_id: str
    username: str
    status: str
    total_passed: int
    total_tests: int
    execution_time_ms: int
    test_results: List[TestResults]


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
# HELPERS
# =====================================================


async def validate_submission(problem_id: str, user_code: str):
    # 1. Fetch full problem data (including hidden tests)
    problem = next((p for p in problems_db if p["id"] == problem_id), None)
    if not problem:
        return {"status": "error", "message": "Problem database mismatch"}

    # Combine public and hidden tests for the final judge
    all_tests = problem.get("public_tests", []) + problem.get("hidden_tests", [])

    test_results = []
    passed_count = 0

    # 2. Prepare the Wrapper Script
    # We wrap the user's code to execute each test case and print results in a parsable way
    # This example assumes Python.
    full_code = user_code + "\n\n"
    full_code += "import json\n"
    full_code += f"tests = {json.dumps(all_tests)}\n"
    full_code += "results = []\n"
    full_code += "for t in tests:\n"
    full_code += "    try:\n"
    full_code += "        # Dynamic call: assumes a function named 'solution'\n"
    full_code += "        res = solution(**t['input'])\n"
    full_code += "        print(json.dumps({'actual': res}))\n"
    full_code += "    except Exception as e:\n"
    full_code += "        print(json.dumps({'error': str(e)}))\n"

    # 3. Call Piston API
    PISTON_URL = os.getenv("PISTON_API_URL")
    payload = {
        "language": "python",
        "version": "3.10.0",
        "files": [{"content": full_code}],
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(PISTON_URL, json=payload, timeout=10.0)
            execution = response.json()
        except Exception as e:
            return {"status": "error", "message": f"Execution engine unreachable: {e}"}

    # 4. Parse Output
    run_data = execution.get("run", {})
    stdout_lines = run_data.get("stdout", "").strip().split("\n")
    stderr = run_data.get("stderr", "")

    if stderr:
        return {
            "status": "error",
            "message": stderr,
            "total_passed": 0,
            "total_tests": len(all_tests),
            "execution_time_ms": 0,
            "test_results": [],
        }

    # 5. Compare Actual vs Expected
    for i, test in enumerate(all_tests):
        try:
            actual_data = json.loads(stdout_lines[i])
            actual_val = actual_data.get("actual")

            is_passed = actual_val == test["expected"]
            if is_passed:
                passed_count += 1

            test_results.append(
                {
                    "input": test["input"],
                    "expected": test["expected"],
                    "actual": actual_val,
                    "passed": is_passed,
                }
            )
        except:
            test_results.append(
                {
                    "input": test["input"],
                    "expected": test["expected"],
                    "actual": "Execution Error",
                    "passed": False,
                }
            )

    return {
        "status": "passed" if passed_count == len(all_tests) else "failed",
        "total_passed": passed_count,
        "total_tests": len(all_tests),
        "execution_time_ms": 100,  # Piston doesn't always provide raw MS, can be estimated
        "test_results": test_results,
    }


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


@app.post("/rooms/{room_id}/submit", response_model=SubmissionResponse)
async def submit_code(room_id: str, request: SubmissionRequest):
    if room_id not in rooms_db:
        raise HTTPException(status_code=404, detail="Room not fount")

    room = rooms_db[room_id]
    # test
    if room["status"] != "active":
        raise HTTPException(status_code=400, detail="Room is not active")

    player_names = [p["username"] for p in room["players"]]

    if request.username not in player_names:
        raise HTTPException(
            status_code=403, detail="User is not a participant in this room"
        )

    result = await validate_submission(room["problem"]["id"], request.code)

    # MOCK RESULT FOR TESTING:
    # result = {
    #     "status": "passed",
    #     "total_passed": 5,
    #     "total_tests": 5,
    #     "execution_time_ms": 45,
    #     "test_results": [],
    # }

    submission_id = str(uuid.uuid4())
    submission_data = {
        "submission_id": submission_id,
        "username": request.username,
        "code": request.code,
        "submitted_at": datetime.now(),
        **result,
    }

    if "submissions" not in room:
        room["submissions"] = {}

    room["submissions"][request.username] = submission_data

    if len(room["submissions"]) == len(room["players"]):
        room["status"] = "finished"
        await sio.emit(
            "match_finished",
            {"room_id": room_id, "results": room["submissions"]},
            room=room_id,
        )

    return submission_data


# =====================================================
# SOCKETS
# =====================================================
# create socket IO server
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, app)


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

    await sio.enter_room(sid, room_id)

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


@sio.event
async def submit_code(sid, data):
    session = await sio.get_session(sid)
    username = session.get("username")
    room_id = data.get("room_id")
    user_code = data.get("code")

    if not username or not room_id:
        return await sio.emit(
            "error", {"detail": "Missing session or room data"}, to=sid
        )

    if room_id not in rooms_db:
        return await sio.emit("error", {"detail": "Room not found"}, to=sid)

    room = rooms_db[room_id]

    # 1. Logic Check
    if room["status"] != "active":
        return await sio.emit("error", {"detail": "Match is not active"}, to=sid)

    # 2. Validate Code
    # Note: Using the function we built in Task 2/3
    result = await validate_submission(room["problem"]["id"], user_code)

    # 3. Store Result
    if "submissions" not in room:
        room["submissions"] = {}

    submission_entry = {
        "username": username,
        "status": result["status"],
        "total_passed": result["total_passed"],
        "total_tests": result["total_tests"],
        "submitted_at": datetime.now().isoformat(),
    }
    room["submissions"][username] = submission_entry

    # 4. Event B: submission_update (Broadcast to room)
    both_submitted = len(room["submissions"]) == len(room["players"])

    update_payload = {
        "room_id": room_id,
        "submissions": room["submissions"],
        "both_submitted": both_submitted,
    }
    await sio.emit("submission_update", update_payload, room=room_id)

    # 5. Event C: match_ended (If both submitted)
    if both_submitted:
        room["status"] = "finished"

        # Determine winner logic
        players = list(room["submissions"].keys())
        p1, p2 = players[0], players[1]
        score1 = room["submissions"][p1]["total_passed"]
        score2 = room["submissions"][p2]["total_passed"]

        winner = None
        if score1 > score2:
            winner = p1
        elif score2 > score1:
            winner = p2
        else:
            winner = None  # Tie

        end_payload = {
            "room_id": room_id,
            "winner": winner,
            "reason": "both_submitted",
            "final_scores": room["submissions"],
        }
        await sio.emit("match_ended", end_payload, room=room_id)
