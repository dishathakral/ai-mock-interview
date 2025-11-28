# import requests
# import json
#
# BASE_URL = "http://localhost:8000/api/v1"
#
# def print_response(title, response):
#     print(f"\n{'='*60}")
#     print(f"TEST: {title}")
#     print(f"Status Code: {response.status_code}")
#     try:
#         print(json.dumps(response.json(), indent=2))
#     except Exception:
#         print(response.text)
#     print(f"{'='*60}\n")
#
# def test_generate_hr_question(user_id, job_role, industry):
#     print("Generating HR question...")
#     payload = {
#         "user_id": user_id,
#         "job_role": job_role,
#         "industry": industry
#     }
#     r = requests.post(f"{BASE_URL}/questions/generate/hr", json=payload)
#     print_response("HR Question Generation", r)
#     assert r.status_code == 200, "Failed to generate HR question"
#     return r.json()
#
# def test_generate_technical_question(user_id, job_role, skills="Python, SQL"):
#     print("Generating Technical question...")
#     payload = {
#         "user_id": user_id,
#         "job_role": job_role,
#         "skills": skills
#     }
#     r = requests.post(f"{BASE_URL}/questions/generate/technical", json=payload)
#     print_response("Technical Question Generation", r)
#     assert r.status_code == 200, "Failed to generate Technical question"
#     return r.json()
#
# def test_generate_experience_question(user_id):
#     print("Generating Personalized Experience question...")
#     payload = {
#         "user_id": user_id
#     }
#     r = requests.post(f"{BASE_URL}/questions/generate/experience", json=payload)
#     print_response("Experience Question Generation", r)
#     assert r.status_code == 200, "Failed to generate Experience question"
#     return r.json()
#
# def test_similarity_check(question_text, question_type="hr", threshold=0.85):
#     print(f"Checking similarity for question: '{question_text}'")
#     params = {
#         "question_text": question_text,
#         "question_type": question_type,
#         "threshold": threshold
#     }
#     r = requests.post(f"{BASE_URL}/questions/check-similarity", params=params)
#     print_response("Similarity Check", r)
#     assert r.status_code == 200, "Similarity check failed"
#     return r.json()
#
# if __name__ == "__main__":
#     USER_ID = 1          # Replace with a valid user from your DB
#     JOB_ROLE = "Software Engineer"
#     INDUSTRY = "Technology"
#     SKILLS = "Python, FastAPI, Postgres"
#
#     # Test HR question generation
#     hr_question = test_generate_hr_question(USER_ID, JOB_ROLE, INDUSTRY)
#
#     # Test Technical question generation
#     technical_question = test_generate_technical_question(USER_ID, JOB_ROLE, SKILLS)
#
#     # Test Experience question generation
#     experience_question = test_generate_experience_question(USER_ID)
#
#     # Test similarity check on a sample question text
#     sample_text = "Tell me about yourself and your background."
#     similar_questions = test_similarity_check(sample_text, question_type="hr")
#
#     print("Phase 2 testing completed successfully!")

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"


def print_response(title, response):
    print(f"\n{'=' * 60}")
    print(f"TEST: {title}")
    print(f"Status Code: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except Exception:
        print(response.text)
    print(f"{'=' * 60}\n")


def test_generate_hr_question(user_id):
    print("Generating HR question based on user profile...")
    payload = {"user_id": user_id}
    r = requests.post(f"{BASE_URL}/questions/generate/hr", json=payload)
    print_response("HR Question Generation", r)
    assert r.status_code == 200, "Failed to generate HR question"
    return r.json()


def test_generate_technical_question(user_id):
    print("Generating Technical question based on user profile...")
    payload = {"user_id": user_id}
    r = requests.post(f"{BASE_URL}/questions/generate/technical", json=payload)
    print_response("Technical Question Generation", r)
    assert r.status_code == 200, "Failed to generate Technical question"
    return r.json()


def test_generate_experience_question(user_id):
    print("Generating Personalized Experience question based on user profile...")
    payload = {"user_id": user_id}
    r = requests.post(f"{BASE_URL}/questions/generate/experience", json=payload)
    print_response("Experience Question Generation", r)
    assert r.status_code == 200, "Failed to generate Experience question"
    return r.json()


def test_similarity_check(question_text, question_type="hr", threshold=0.85):
    print(f"Checking similarity for question: '{question_text}'")
    params = {
        "question_text": question_text,
        "question_type": question_type,
        "threshold": threshold,
    }
    r = requests.post(f"{BASE_URL}/questions/check-similarity", params=params)
    print_response("Similarity Check", r)
    assert r.status_code == 200, "Similarity check failed"
    return r.json()


if __name__ == "__main__":
    USER_ID = 1  # Replace with a valid user ID in your database

    # # Test HR question generation
    # hr_question = test_generate_hr_question(USER_ID)
    #
    # # Test Technical question generation
    # technical_question = test_generate_technical_question(USER_ID)
    #
    # # Test Experience question generation
    # experience_question = test_generate_experience_question(USER_ID)

    # Test similarity check on a sample question text
    sample_text = "Tell me about yourself and what attracted you to this specific opportunity at our company"
    similar_questions = test_similarity_check(sample_text, question_type="hr")

    print("Phase 2 testing completed successfully!")
