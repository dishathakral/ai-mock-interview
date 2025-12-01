#!/usr/bin/env python3
"""🎯 PHASE 3 INTERACTIVE TEST - Using /start first question then sequential next-question calls"""
import requests
import logging

logging.basicConfig(level=logging.INFO)
BASE_URL = "http://localhost:8000/api/v1"

def interactive_interview_test():
    print("🚀 PHASE 3: INTERACTIVE INTERVIEW TEST")
    USER_ID = 2
    total_target = 12

    # 1. CREATE INTERVIEW
    print("\n1️⃣ Creating interview...")
    resp = requests.post(f"{BASE_URL}/interviews/", json={"user_id": USER_ID})
    if resp.status_code != 200:
        print(f"❌ Error: {resp.text}")
        return

    INTERVIEW_ID = resp.json()["interview_id"]
    print(f"✅ Interview created: ID={INTERVIEW_ID}")

    # 2. START INTERVIEW - get FIRST question from /start response
    print("\n2️⃣ Starting interview and retrieving FIRST question...")
    resp = requests.post(f"{BASE_URL}/interviews/{INTERVIEW_ID}/start")
    if resp.status_code != 200:
        print(f"❌ Start failed: {resp.text}")
        return

    start_data = resp.json()
    first_question = start_data["first_question"]
    print(f"✅ First question loaded from /start!")

    question_count = 1
    print(f"\n{'=' * 60}")
    print(f"📝 QUESTION {question_count}/{total_target}")
    print(f"🆔 InterviewQuestion ID: {first_question['interview_question_id']}")
    print(f"🔤 Type: {first_question['question_type'].upper()}")
    print(f"💬 {first_question['question_text']}")
    print(f"{'=' * 60}")

    while True:
        answer = input("💭 Your answer (or 'skip' or 'quit'): ").strip()
        if answer.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
        elif answer.lower() == 'skip':
            answer = f"[SKIPPED] Question {question_count}"

        # Submit answer for current question
        resp = requests.post(
            f"{BASE_URL}/interviews/{INTERVIEW_ID}/questions/{first_question['interview_question_id']}/answer",
            json={"answer_text": answer}
        )
        if resp.status_code == 200:
            print("✅ Answer saved!")
            progress_data = resp.json()
            print(f"📊 Progress: {progress_data.get('answered', question_count)}/{total_target}")
        else:
            print(f"❌ Answer failed: {resp.text}")

        # Check if complete before fetching next
        status_resp = requests.get(f"{BASE_URL}/interviews/{INTERVIEW_ID}/status")
        if status_resp.status_code == 200:
            status = status_resp.json()
            print(f"📈 Status: {status.get('asked_count', question_count)} asked, {status.get('answered_count', 0)} answered")
            if status.get('asked_count', 0) >= total_target:
                print("\n🎉🎉 INTERVIEW COMPLETE! 🎉🎉")
                break
        else:
            print(f"❌ Could not get status: {status_resp.text}")

        question_count += 1
        if question_count > total_target:
            print("\n🎉🎉 INTERVIEW COMPLETE! 🎉🎉")
            break

        # Get NEXT question
        resp = requests.post(f"{BASE_URL}/interviews/{INTERVIEW_ID}/next-question")
        if resp.status_code != 200:
            print(f"❌ Next question failed: {resp.text}")
            break

        first_question = resp.json()  # Next question info

        print(f"\n{'=' * 60}")
        print(f"📝 QUESTION {question_count}/{total_target}")
        print(f"🆔 InterviewQuestion ID: {first_question['interview_question_id']}")
        print(f"🔤 Type: {first_question['question_type'].upper()}")
        print(f"💬 {first_question['question_text']}")
        print(f"{'=' * 60}")

if __name__ == "__main__":
    interactive_interview_test()
