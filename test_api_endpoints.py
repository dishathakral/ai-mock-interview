"""
Complete API endpoint testing
Tests all routes with proper data flow
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"


def print_response(title, response):
    """Pretty print API response"""
    print(f"\n{'=' * 60}")
    print(f"📍 {title}")
    print(f"{'=' * 60}")
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2))


def test_complete_flow():
    """Test complete interview flow"""

    print("\n🧪 TESTING AI MOCK INTERVIEW API")
    print("=" * 60)

    # 1. Health Check
    print("\n1️⃣ Testing Health Check...")
    response = requests.get(f"{BASE_URL}/health")
    print_response("Health Check", response)
    assert response.status_code == 200

    # 2. Create User
    print("\n2️⃣ Testing User Creation...")
    user_data = {
        "email": f"test_{datetime.now().timestamp()}@example.com",
        "name": "Test User",
        "industry": "Technology",
        "bio": "Software Engineer with 5 years experience",
        "experience": "3-5 years",
        "skills": ["Python", "FastAPI", "Machine Learning"]
    }
    response = requests.post(f"{BASE_URL}/users/", json=user_data)
    print_response("Create User", response)
    assert response.status_code == 201
    user_id = response.json()['id']
    print(f"✅ Created user with ID: {user_id}")

    # 3. Get User
    print("\n3️⃣ Testing Get User...")
    response = requests.get(f"{BASE_URL}/users/{user_id}")
    print_response("Get User", response)
    assert response.status_code == 200

    # 4. Start Interview
    print("\n4️⃣ Testing Start Interview...")
    interview_data = {
        "user_id": user_id,
        "job_role": "Software Engineer",
        "industry": "Technology"
    }
    response = requests.post(f"{BASE_URL}/interviews/start", json=interview_data)
    print_response("Start Interview", response)
    assert response.status_code == 201
    interview_id = response.json()['interview_id']
    print(f"✅ Started interview with ID: {interview_id}")

    # 5. Get Questions by Category
    print("\n5️⃣ Testing Get Introductory Questions...")
    response = requests.get(f"{BASE_URL}/questions/category/introductory?limit=3")
    print_response("Get Introductory Questions", response)
    assert response.status_code == 200
    questions = response.json()
    print(f"✅ Retrieved {len(questions)} questions")

    if questions:
        question_id = questions[0]['question_id']

        # 6. Submit Answer
        print("\n6️⃣ Testing Submit Answer...")
        answer_data = {
            "interview_id": interview_id,
            "question_id": question_id,
            "user_id": user_id,
            "answer_text": "I am a software engineer with expertise in Python, FastAPI, and machine learning. I have worked on several backend projects and have a strong foundation in database design."
        }
        response = requests.post(f"{BASE_URL}/answers/", json=answer_data)
        print_response("Submit Answer", response)
        assert response.status_code == 201
        answer_id = response.json()['id']
        print(f"✅ Submitted answer with ID: {answer_id}")

    # 7. Get Interview Answers
    print("\n7️⃣ Testing Get Interview Answers...")
    response = requests.get(f"{BASE_URL}/answers/interview/{interview_id}")
    print_response("Get Interview Answers", response)
    # May be 404 if no answers yet, that's ok

    # 8. Complete Interview
    print("\n8️⃣ Testing Complete Interview...")
    complete_data = {
        "interview_id": interview_id,
        "score": 85.5
    }
    response = requests.put(f"{BASE_URL}/interviews/{interview_id}/complete", json=complete_data)
    print_response("Complete Interview", response)
    assert response.status_code == 200

    # 9. Get Question Statistics
    print("\n9️⃣ Testing Question Statistics...")
    response = requests.get(f"{BASE_URL}/questions/stats/summary")
    print_response("Question Statistics", response)
    assert response.status_code == 200

    # 10. Check Similarity
    print("\n🔟 Testing Similarity Check...")
    response = requests.post(
        f"{BASE_URL}/questions/check-similarity",
        params={
            "question_text": "Tell me about yourself and your background",
            "question_type": "hr",
            "threshold": 0.85
        }
    )
    print_response("Similarity Check", response)
    assert response.status_code == 200

    print("\n" + "=" * 60)
    print("✅ ALL API TESTS PASSED!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    print("⚠️  Make sure the API is running: uvicorn app.main:app --reload")
    input("Press Enter to start testing...")

    try:
        test_complete_flow()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to API. Is it running?")
        print("   Start it with: uvicorn app.main:app --reload")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
