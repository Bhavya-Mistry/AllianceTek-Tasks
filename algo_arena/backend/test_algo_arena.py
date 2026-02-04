"""
AlgoArena Manual Testing Script
Tests all REST endpoints and Socket.IO functionality
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"


def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_response(response):
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
    except:
        print(f"Response: {response.text}")
    print()


# =====================================================
# TEST 1: Health Check
# =====================================================
def test_health():
    print_section("TEST 1: Health Check")
    response = requests.get(f"{BASE_URL}/health")
    print_response(response)
    assert response.status_code == 200


# =====================================================
# TEST 2: Get All Problems
# =====================================================
def test_get_problems():
    print_section("TEST 2: Get All Problems (limit 5)")
    response = requests.get(f"{BASE_URL}/problems?limit=5")
    print_response(response)
    assert response.status_code == 200
    return response.json()


# =====================================================
# TEST 3: Filter Problems by Difficulty
# =====================================================
def test_filter_problems():
    print_section("TEST 3: Filter Problems - Easy")
    response = requests.get(f"{BASE_URL}/problems?difficulty=easy&limit=3")
    print_response(response)

    print_section("TEST 3b: Filter Problems - Medium")
    response = requests.get(f"{BASE_URL}/problems?difficulty=medium&limit=3")
    print_response(response)

    print_section("TEST 3c: Filter Problems - Hard")
    response = requests.get(f"{BASE_URL}/problems?difficulty=hard&limit=3")
    print_response(response)


# =====================================================
# TEST 4: Get Specific Problem Details
# =====================================================
def test_get_problem_details(problems_data):
    if problems_data["count"] > 0:
        problem_id = problems_data["items"][0]["id"]
        print_section(f"TEST 4: Get Problem Details (ID: {problem_id})")
        response = requests.get(f"{BASE_URL}/problems/{problem_id}")
        print_response(response)
        return response.json()
    else:
        print("No problems available to test")


# =====================================================
# TEST 5: Get Non-existent Problem
# =====================================================
def test_get_nonexistent_problem():
    print_section("TEST 5: Get Non-existent Problem (Should fail)")
    response = requests.get(f"{BASE_URL}/problems/fake-problem-id-999")
    print_response(response)
    assert response.status_code == 404


# =====================================================
# TEST 6: Create Room
# =====================================================
def test_create_room():
    print_section("TEST 6: Create Room")
    payload = {"username": "Alice", "difficulty": "easy", "time_limit_sec": 600}
    response = requests.post(f"{BASE_URL}/rooms", json=payload)
    print_response(response)
    assert response.status_code == 201
    return response.json()


# =====================================================
# TEST 7: Get Room Status
# =====================================================
def test_get_room_status(room_id):
    print_section(f"TEST 7: Get Room Status (ID: {room_id})")
    response = requests.get(f"{BASE_URL}/rooms/{room_id}")
    print_response(response)
    assert response.status_code == 200


# =====================================================
# TEST 8: Join Room
# =====================================================
def test_join_room(room_id):
    print_section(f"TEST 8: Join Room (ID: {room_id})")
    payload = {"username": "Bob"}
    response = requests.post(f"{BASE_URL}/rooms/{room_id}/join", json=payload)
    print_response(response)
    assert response.status_code == 200
    return response.json()


# =====================================================
# TEST 9: Try to Join Full Room
# =====================================================
def test_join_full_room(room_id):
    print_section(f"TEST 9: Try to Join Full Room (Should fail)")
    payload = {"username": "Charlie"}
    response = requests.post(f"{BASE_URL}/rooms/{room_id}/join", json=payload)
    print_response(response)
    assert response.status_code == 409


# =====================================================
# TEST 10: Try to Join Non-existent Room
# =====================================================
def test_join_nonexistent_room():
    print_section("TEST 10: Join Non-existent Room (Should fail)")
    payload = {"username": "Dave"}
    response = requests.post(f"{BASE_URL}/rooms/fake-room-id/join", json=payload)
    print_response(response)
    assert response.status_code == 404


# =====================================================
# RUN ALL TESTS
# =====================================================
def run_all_tests():
    print("\n🚀 Starting AlgoArena Backend Tests")
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now()}\n")

    try:
        # Basic tests
        test_health()
        problems_data = test_get_problems()
        test_filter_problems()
        test_get_problem_details(problems_data)
        test_get_nonexistent_problem()

        # Room workflow tests
        room_data = test_create_room()
        room_id = room_data["room_id"]

        test_get_room_status(room_id)
        test_join_room(room_id)
        test_join_full_room(room_id)
        test_join_nonexistent_room()

        print_section("✅ ALL TESTS PASSED!")

    except Exception as e:
        print_section(f"❌ TEST FAILED: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
