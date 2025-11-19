# app/scripts/generate_static_questions_simple.py

from google import genai
from pydantic import BaseModel, Field
from typing import List, Optional
import json
import logging
import time  # ADD THIS
from pathlib import Path
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


class Question(BaseModel):
    """Single question structure"""
    question_text: str
    question_type: str
    subcategory: str
    tags: List[str]
    industry: str
    job_role: str
    difficulty: str
    expected_answer: Optional[str] = None
    is_mandatory: Optional[bool] = False


class QuestionCategory(BaseModel):
    """Questions for one category"""
    questions: List[Question]


def generate_questions_batch(category: str, count: int, subcategory: str, difficulty: str, description: str) -> List[
    Question]:
    """Generate questions in batches"""

    logger.info(f"Generating {count} {category} questions...")
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    prompt = f"""
    Generate exactly {count} {category} interview questions.

    {description}

    REQUIREMENTS:
    - All questions must have: question_type="hr", subcategory="{subcategory}", 
      industry="general", job_role="general", difficulty="{difficulty}"
    - Make every question unique and professional
    - Provide brief expected_answer (1-2 sentences)
    - Use proper interview language
    - Keep questions open-ended
    - For subcategory="introductory", set is_mandatory=true for the first 3 questions only

    Return ONLY valid JSON matching the schema.
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": QuestionCategory.model_json_schema(),
            }
        )

        category_data = QuestionCategory.model_validate_json(response.text)
        logger.info(f"✅ Generated {len(category_data.questions)} {category} questions")
        return category_data.questions

    except Exception as e:
        logger.error(f"❌ Error generating {category} questions: {e}")
        with open(f"debug_{category}_response.txt", "w") as f:
            f.write(response.text if 'response' in locals() else "No response")
        raise


def generate_static_questions_json():
    """Generate questions in proper categories WITH DELAYS"""

    all_questions = {
        "introductory": [],
        "behavioral": [],
        "personality": [],
        "closing": []
    }

    # Category 1: Introductory
    intro_desc = """
    ONLY questions asked at the ABSOLUTE START of interviews (first 5 minutes).
    These MUST be about the candidate introducing themselves and their background.

    EXAMPLES: "Tell me about yourself", "Walk me through your resume", 
    "Describe your professional background", "How did you get into this field?"

    DO NOT INCLUDE: Hobbies, salary, personality traits, work style

    Mark the first 3 questions with is_mandatory=true.
    Tags: ["background", "education", "career-path", "professional-journey"]
    """

    intro_questions = generate_questions_batch(
        category="introductory",
        count=12,
        subcategory="introductory",
        difficulty="easy",
        description=intro_desc
    )
    all_questions["introductory"] = [q.model_dump() for q in intro_questions]

    logger.info("⏳ Waiting 30 seconds before next batch...")
    time.sleep(30)

    # Category 2: Behavioral
    behavioral_desc = """
    STAR format questions about PAST EXPERIENCES.
    Cover: teamwork, conflict resolution, leadership, problem-solving, failure, success,
    time management, adaptability, decision-making, ethics, innovation, customer service.
    Examples: "Tell me about a time you...", "Describe a situation when..."
    Tags should match competency: ["teamwork", "leadership", "problem-solving"]
    """

    behavioral_questions = generate_questions_batch(
        category="behavioral",
        count=45,
        subcategory="behavioral",
        difficulty="medium",
        description=behavioral_desc
    )
    all_questions["behavioral"] = [q.model_dump() for q in behavioral_questions]

    logger.info("⏳ Waiting 30 seconds before next batch...")
    time.sleep(30)

    # Category 3: Personality
    personality_desc = """
    Questions about traits, goals, values, work style, and motivation.
    Cover: strengths/weaknesses, career goals, stress management, company/role motivation, values.
    Examples: "What are your strengths?", "Where do you see yourself in 5 years?"
    Mix difficulty: 15 easy, 20 medium.
    Tags: ["self-awareness", "motivation", "culture-fit", "goals", "values"]
    """

    personality_questions = generate_questions_batch(
        category="personality",
        count=35,
        subcategory="personality",
        difficulty="medium",
        description=personality_desc
    )
    all_questions["personality"] = [q.model_dump() for q in personality_questions]

    logger.info("⏳ Waiting 30 seconds before next batch...")
    time.sleep(30)

    # Category 4: Closing
    closing_desc = """
    Questions asked at the END of interviews - lighter, conversational.
    EXAMPLES: "What are your salary expectations?", "What are your hobbies?",
    "Tell me about volunteer work", "Who do you look up to?", "Do you have questions for us?"
    All should have: question_type="hr", subcategory="closing", difficulty="easy"
    Tags: ["conversation", "culture-fit", "personal", "wrap-up", "casual"]
    """

    closing_questions = generate_questions_batch(
        category="closing",
        count=23,
        subcategory="closing",
        difficulty="easy",
        description=closing_desc
    )
    all_questions["closing"] = [q.model_dump() for q in closing_questions]

    return all_questions


def save_to_json(data: dict,
                 filepath: str = "/Users/disha/PycharmProjects/ai-mock-interview/data/static_questions.json"):
    """Save questions to JSON file"""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"💾 Questions saved to {filepath}")


def main():
    """Main execution"""
    try:
        logger.info("=" * 70)
        logger.info("STATIC QUESTION GENERATION - WITH RATE LIMIT PROTECTION")
        logger.info("=" * 70)
        logger.info("⚠️  This will take ~2-3 minutes due to delays between batches")

        logger.info("\n[Step 1/2] Generating questions with delays...")
        questions_data = generate_static_questions_json()

        intro_count = len(questions_data["introductory"])
        behavioral_count = len(questions_data["behavioral"])
        personality_count = len(questions_data["personality"])
        closing_count = len(questions_data["closing"])
        total = intro_count + behavioral_count + personality_count + closing_count

        logger.info(f"\n📊 Generation Summary:")
        logger.info(f"  • Introductory (opening): {intro_count} questions")
        logger.info(f"  • Behavioral (mid-interview): {behavioral_count} questions")
        logger.info(f"  • Personality (mid-interview): {personality_count} questions")
        logger.info(f"  • Closing (wrap-up): {closing_count} questions")
        logger.info(f"  • Total: {total} questions")

        logger.info("\n[Step 2/2] Saving to JSON file...")
        save_to_json(questions_data)

        logger.info("\n" + "=" * 70)
        logger.info("✅ GENERATION COMPLETE!")
        logger.info("📁 File: /Users/disha/PycharmProjects/ai-mock-interview/data/static_questions.json")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        raise


if __name__ == "__main__":
    main()
