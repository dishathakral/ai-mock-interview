# test_phase1_complete.py

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"


def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_response(endpoint, response):
    print(f"\n📍 {endpoint}")
    print(f"Status: {response.status_code}")
    if response.status_code < 400:
        print(f"✅ Success")
        print(json.dumps(response.json(), indent=2)[:500])  # Truncate long responses
    else:
        print(f"❌ Failed")
        print(response.json())


def test_phase1_complete():
    """Comprehensive Phase 1 testing"""

    print_section("PHASE 1 - COMPLETE API TESTING")

    # =========================================
    # 1. HEALTH CHECK
    # =========================================
    print_section("1. Health Check")
    response = requests.get(f"{BASE_URL}/health")
    print_response("GET /health", response)
    assert response.status_code == 200, "Health check failed"

    # =========================================
    # 2. USER MANAGEMENT
    # =========================================
    print_section("2. User Management")

    # Create user
    user_data = {
        "email": f"test_{datetime.now().timestamp()}@example.com",
        "name": "Test User",
        "industry": "Technology",
        "bio": "Software Engineer with 5 years experience",
        "experience": "5+ years",
        "skills": ["Python", "FastAPI", "Machine Learning"]
    }
    response = requests.post(f"{BASE_URL}/users/", json=user_data)
    print_response("POST /users/", response)
    assert response.status_code == 201, "User creation failed"
    user_id = response.json()['id']
    print(f"\n✅ Created user ID: {user_id}")

    # Get user
    response = requests.get(f"{BASE_URL}/users/{user_id}")
    print_response(f"GET /users/{user_id}", response)
    assert response.status_code == 200, "Get user failed"

    # =========================================
    # 3. QUESTION MANAGEMENT
    # =========================================
    print_section("3. Question Management")

    # Get questions by category
    response = requests.get(f"{BASE_URL}/questions/category/introductory?limit=5")
    print_response("GET /questions/category/introductory", response)
    assert response.status_code == 200, "Get questions by category failed"

    # Get question stats
    response = requests.get(f"{BASE_URL}/questions/stats/summary")
    print_response("GET /questions/stats/summary", response)
    assert response.status_code == 200, "Get stats failed"
    stats = response.json()
    print(f"\n📊 Database Stats:")
    print(f"   Total questions: {stats['total']}")
    print(f"   Mandatory: {stats['mandatory']}")
    print(f"   By subcategory: {stats['by_subcategory']}")

    # Check similarity
    response = requests.post(
        f"{BASE_URL}/questions/check-similarity",
        params={
            "question_text": "Tell me about yourself and your background",
            "question_type": "hr",
            "threshold": 0.85
        }
    )
    print_response("POST /questions/check-similarity", response)
    assert response.status_code == 200, "Similarity check failed"

    # =========================================
    # 4. INTERVIEW FLOW - COMPLETE
    # =========================================
    print_section("4. Interview Flow - Complete Workflow")

    # Start interview
    interview_data = {
        "user_id": user_id,
        "industry": "Technology",
        "job_role": "Software Engineer"
    }
    response = requests.post(f"{BASE_URL}/interviews/start", json=interview_data)
    print_response("POST /interviews/start", response)
    assert response.status_code == 201, "Start interview failed"
    interview_id = response.json()['interview_id']
    print(f"\n✅ Started interview ID: {interview_id}")

    # Get interview details
    response = requests.get(f"{BASE_URL}/interviews/{interview_id}")
    print_response(f"GET /interviews/{interview_id}", response)
    assert response.status_code == 200, "Get interview details failed"

    # =========================================
    # 5. QUESTION LOOP (Ask 5 questions)
    # =========================================
    print_section("5. Question Loop - Fetch → Ask → Answer")

    for i in range(5):
        print(f"\n--- Question {i + 1} ---")

        # Step A: Fetch next question
        response = requests.get(
            f"{BASE_URL}/interviews/{interview_id}/fetch-next-question",
            params={"use_ai": False}
        )
        print_response("GET /fetch-next-question", response)
        assert response.status_code == 200, f"Fetch question {i + 1} failed"

        fetch_data = response.json()
        if fetch_data.get("interview_complete"):
            print("✅ Interview complete (should not happen at question 5)")
            break

        global_question_id = fetch_data['global_question_id']
        question_text = fetch_data['question_text']
        print(f"\n📥 Fetched Q{i + 1}: {question_text[:60]}...")

        # Step B: Ask question (add to interview)
        response = requests.post(
            f"{BASE_URL}/interviews/{interview_id}/ask-question",
            json={"global_question_id": global_question_id}
        )
        print_response("POST /ask-question", response)
        assert response.status_code == 201, f"Ask question {i + 1} failed"

        interview_question_id = response.json()['interview_question_id']
        print(f"❓ Asked question ID: {interview_question_id}")

        # Step C: Submit answer (FIXED URL)
        answer_text = f"This is my answer to question {i + 1}. I have extensive experience in this area and have worked on multiple projects..."
        response = requests.post(
            f"{BASE_URL}/interviews/{interview_id}/questions/{interview_question_id}/answer",
            json={"answer_text": answer_text}
        )
        print_response(f"POST /interviews/{interview_id}/questions/{interview_question_id}/answer", response)
        assert response.status_code == 201, f"Answer question {i + 1} failed"
        print(f"✅ Answer submitted")

    # =========================================
    # 6. INTERVIEW QUESTIONS LIST
    # =========================================
    print_section("6. Get Interview Questions")

    response = requests.get(f"{BASE_URL}/interviews/{interview_id}/questions")
    print_response(f"GET /interviews/{interview_id}/questions", response)
    assert response.status_code == 200, "Get interview questions failed"
    questions_list = response.json()
    print(f"\n📋 Total questions in interview: {len(questions_list['questions'])}")

    # =========================================
    # 7. COMPLETE INTERVIEW
    # =========================================
    print_section("7. Complete Interview")

    response = requests.put(f"{BASE_URL}/interviews/{interview_id}/complete")
    print_response("PUT /complete", response)
    assert response.status_code == 200, "Complete interview failed"
    print(f"✅ Interview completed")

    # =========================================
    # 8. INTERVIEW SUMMARY
    # =========================================
    print_section("8. Interview Summary")

    response = requests.get(f"{BASE_URL}/interviews/{interview_id}/summary")
    print_response(f"GET /interviews/{interview_id}/summary", response)
    assert response.status_code == 200, "Get summary failed"
    summary = response.json()
    print(f"\n📊 Summary:")
    print(f"   Status: {summary['status']}")
    print(f"   Questions: {summary['total_questions']}")
    print(f"   Answers: {summary['total_answers']}")

    # =========================================
    # 9. USER'S INTERVIEW HISTORY
    # =========================================
    print_section("9. User Interview History")

    response = requests.get(f"{BASE_URL}/users/{user_id}/interviews")
    print_response(f"GET /users/{user_id}/interviews", response)
    assert response.status_code == 200, "Get user interviews failed"
    history = response.json()
    print(f"\n📚 User has {history['total_interviews']} interview(s)")

    # =========================================
    # 10. ERROR HANDLING TESTS
    # =========================================
    print_section("10. Error Handling Tests")

    # Test: Answer already submitted
    print("\nTest: Duplicate answer")
    response = requests.post(
        f"{BASE_URL}/interviews/{interview_id}/questions/1/answer",
        json={"answer_text": "Duplicate"}
    )
    print(f"Expected 400: Got {response.status_code}")
    assert response.status_code == 400, "Should reject duplicate answer"
    print("✅ Correctly rejected duplicate answer")

    # Test: Invalid interview ID
    print("\nTest: Invalid interview ID")
    response = requests.get(f"{BASE_URL}/interviews/99999")
    print(f"Expected 404: Got {response.status_code}")
    assert response.status_code == 404, "Should return 404 for invalid ID"
    print("✅ Correctly returned 404")

    # Test: Answer after interview completed
    print("\nTest: Answer after completion")
    response = requests.post(
        f"{BASE_URL}/interviews/{interview_id}/questions/2/answer",
        json={"answer_text": "Too late"}
    )
    print(f"Expected 400: Got {response.status_code}")
    assert response.status_code == 400, "Should reject answer after completion"
    print("✅ Correctly rejected answer after completion")

    # =========================================
    # FINAL SUMMARY
    # =========================================
    print_section("✅ ALL PHASE 1 TESTS PASSED!")
    print("\n🎉 Your API is ready for Phase 2!")
    print("\nNext steps:")
    print("  1. ✅ Phase 1 Complete - Basic CRUD operations work")
    print("  2. 🚀 Ready for Phase 2 - InterviewOrchestrator + ChromaDB")
    print("  3. 🤖 Ready for Phase 3 - Gemini API integration")


if __name__ == "__main__":
    print("\n⚠️  Make sure API is running: uvicorn app.main:app --reload")
    input("Press Enter to start testing...")

    try:
        test_phase1_complete()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to API. Is it running?")
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
