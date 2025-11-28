"""
Question Generation Service
Orchestrates use of Gemini AI + similarity check + DB storage
"""

import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.services.gemini_service import GeminiService
from app.services.question_service import QuestionService
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class QuestionGenerationService:

    @staticmethod
    def generate_and_store_hr_question(
            db: Session,
            job_role: str,
            industry: str,
            similarity_threshold: float = None
    ):
        similarity_threshold = similarity_threshold or settings.SIMILARITY_THRESHOLD

        logger.debug(f"Generating HR question for role={job_role}, industry={industry}")
        question_text = GeminiService.generate_hr_question(job_role, industry)
        logger.debug(f"Generated HR question: {question_text}")

        similar = QuestionService.check_question_similarity(
            question_text,
            question_type="hr",
            threshold=similarity_threshold
        )
        if similar:
            logger.info(f"Similar question found, reusing existing ID: {similar[0]['question_id']}")
            # Return existing question from DB (reuse)
            existing_question = QuestionService.get_question_by_id(db, int(similar[0]['question_id']))
            return existing_question

        logger.info("No similar question found, storing new HR question.")

        question_data = {
            "question_text": question_text,
            "question_type": "hr",
            "subcategory": "hr",
            "industry": industry,
            "job_role": job_role,
            "difficulty": "medium",
            "is_static": 0,
            "is_mandatory": False
        }
        new_question = QuestionService.create_question(db, question_data)
        return new_question

    @staticmethod
    def generate_and_store_technical_question(
            db: Session,
            job_role: str,
            skills: str,
            similarity_threshold: float = None
    ):
        similarity_threshold = similarity_threshold or settings.SIMILARITY_THRESHOLD

        logger.debug(f"Generating technical question for role={job_role}, skills={skills}")
        question_text = GeminiService.generate_technical_question(job_role, skills)
        logger.debug(f"Generated technical question: {question_text}")

        similar = QuestionService.check_question_similarity(
            question_text,
            question_type="technical",
            threshold=similarity_threshold
        )
        if similar:
            logger.info(f"Similar question found, reusing existing ID: {similar[0]['question_id']}")
            existing_question = QuestionService.get_question_by_id(db, int(similar[0]['question_id']))
            return existing_question

        logger.info("No similar question found, storing new technical question.")

        question_data = {
            "question_text": question_text,
            "question_type": "technical",
            "subcategory": "technical",
            "industry": "general",
            "job_role": job_role,
            "difficulty": "medium",
            "is_static": 0,
            "is_mandatory": False
        }
        new_question = QuestionService.create_question(db, question_data)
        return new_question

    @staticmethod
    def generate_personalized_experience_question(
            db: Session,
            user_profile: str
    ):
        logger.debug(f"Generating personalized experience question for user profile: {user_profile}")
        question_text = GeminiService.generate_experience_question(user_profile)
        logger.debug(f"Generated experience question: {question_text}")

        # No similarity check as personalized
        question_data = {
            "question_text": question_text,
            "question_type": "experience",
            "subcategory": "experience",
            "industry": "general",
            "job_role": "general",
            "difficulty": "medium",
            "is_static": 0,
            "is_mandatory": False
        }
        new_question = QuestionService.create_question(db, question_data)
        return new_question
