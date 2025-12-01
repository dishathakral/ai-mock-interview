from sqlalchemy.orm import Session
from app.database.models import Interview, InterviewQuestion, UserAnswer, GlobalQuestion
from app.services.question_service import QuestionService
from app.services.gemini_service import GeminiService
from app.database.chroma_db import chroma_db
from sentence_transformers import SentenceTransformer
import logging
from sqlalchemy import func
import numpy as np

logger = logging.getLogger(__name__)


class InterviewOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.question_service = QuestionService()
        self.gemini_service = GeminiService()
        self.chroma = chroma_db
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

    def get_next_question(self, interview_id: int) -> dict:
        """Core orchestrator with hybrid DB/AI + Chroma personalization"""
        interview = (
            self.db.query(Interview)
            .filter(Interview.interview_id == interview_id)
            .first()
        )
        if not interview:
            raise ValueError(f"Interview {interview_id} not found")

        # Count how many answers exist for this interview
        total_asked_count = (
                self.db.query(func.count(InterviewQuestion.id))
                .filter(InterviewQuestion.interview_id == interview_id)
                .scalar() or 0
        )
        answered_count = (
                self.db.query(func.count(UserAnswer.id))
                .filter(UserAnswer.interview_id == interview_id)
                .scalar() or 0
        )

        total_target = 12
        logger.info(f"interview_id={interview_id} answered={answered_count}/{total_target}")

        if total_asked_count >= total_target:
            return {"status": "complete", "message": "Interview finished"}

        next_order = total_asked_count+ 1
        question_type = self._get_question_type(next_order)

        # Embed user profile for Chroma matching
        user_profile_embedding = self._get_user_profile_embedding(interview.user_id)

        question = self._get_personalized_question(
            interview.user_id, question_type, next_order, user_profile_embedding
        )

        # Create InterviewQuestion row
        interview_question = InterviewQuestion(
            interview_id=interview_id,
            question_id=question.question_id,  # ✅ correct FK
            order_index=next_order ,  # 0-based index
            question_type=question_type,
            subcategory=question.subcategory if hasattr(question, "subcategory") else None,
        )
        self.db.add(interview_question)
        self.db.commit()
        self.db.refresh(interview_question)

        logger.info(
            f"interview_id={interview_id} order={next_order} "
            f"type={question_type} qid={question.question_id}"
        )
        return {
            "interview_question_id": interview_question.id,  # PK in interview_questions
            "global_question_id": question.question_id,  # FK to global_questions
            "question_text": question.question_text,
            "question_type": question_type,
            "order_number": next_order,
            "difficulty": getattr(question, "difficulty", "medium"),
            "from_db": getattr(question, "is_static", True),
        }
    # def get_next_question(self, interview_id: int) -> dict:
    #     """Core orchestrator with hybrid DB/AI + Chroma personalization"""
    #     interview = (
    #         self.db.query(Interview)
    #         .filter(Interview.interview_id == interview_id)
    #         .first()
    #     )
    #     if not interview:
    #         raise ValueError(f"Interview {interview_id} not found")
    #
    #     # ✅ CORRECT: Count TOTAL questions asked (for sequencing)
    #     total_asked_count = (
    #             self.db.query(func.count(InterviewQuestion.id))
    #             .filter(InterviewQuestion.interview_id == interview_id)
    #             .scalar() or 0
    #     )
    #
    #     # ✅ CORRECT: Count answers separately (for completion check)
    #     answered_count = (
    #             self.db.query(func.count(UserAnswer.id))
    #             .filter(UserAnswer.interview_id == interview_id)
    #             .scalar() or 0
    #     )
    #
    #     total_target = 12
    #     logger.info(f"interview_id={interview_id} asked={total_asked_count} answered={answered_count}/{total_target}")
    #
    #     # ✅ CORRECT: Stop when we've asked 12 questions (not answered)
    #     if total_asked_count >= total_target:
    #         return {"status": "complete", "message": "Interview finished"}
    #
    #     # ✅ CORRECT: Use total_asked_count for sequential order
    #     next_order = total_asked_count + 1
    #     question_type = self._get_question_type(next_order)
    #
    #     # Embed user profile for Chroma matching
    #     user_profile_embedding = self._get_user_profile_embedding(interview.user_id)
    #
    #     question = self._get_personalized_question(
    #         interview.user_id, question_type, next_order, user_profile_embedding
    #     )
    #
    #     # Create InterviewQuestion row
    #     interview_question = InterviewQuestion(
    #         interview_id=interview_id,
    #         question_id=question.question_id,  # ✅ correct FK
    #         order_index=total_asked_count,  # ✅ 0-based: 0,1,2,3,4...
    #         question_type=question_type,
    #         subcategory=getattr(question, "subcategory", None),
    #     )
    #     self.db.add(interview_question)
    #     self.db.commit()
    #     self.db.refresh(interview_question)
    #
    #     logger.info(
    #         f"interview_id={interview_id} order={next_order} "
    #         f"type={question_type} qid={question.question_id} "
    #         f"is_static={getattr(question, 'is_static', True)} "
    #         f"job_role={getattr(question, 'job_role', 'unknown')}"
    #     )
    #     return {
    #         "interview_question_id": interview_question.id,  # PK in interview_questions
    #         "global_question_id": question.question_id,  # FK to global_questions
    #         "question_text": question.question_text,
    #         "question_type": question_type,
    #         "order_number": next_order,
    #         "difficulty": getattr(question, "difficulty", "medium"),
    #         "from_db": getattr(question, "is_static", True),
    #         "job_role": getattr(question, "job_role", "general"),
    #     }

    def _get_question_type(self, order_number: int) -> str:
        """Phase progression"""
        if order_number <= 3:
            return "introductory"
        elif order_number <= 6:
            return "hr"
        elif order_number <= 9:
            return "technical"
        else:
            return "experience"

    def _get_user_profile_embedding(self, user_id: int) -> np.ndarray:
        """EMBED USER PROFILE for Chroma matching"""
        user = self.question_service.get_user_profile(self.db,user_id)

        # Combine profile fields for semantic matching
        profile_text = f"{user.industry} {user.bio or ''} {user.job_role or ''} {' '.join(user.skills or [])}"

        logger.info(f"🔍 Profile for user {user_id}: '{profile_text[:100]}...'")

        if not profile_text.strip():
            profile_text = f"{user.industry} software engineer"  # Fallback

        embedding = self.embedder.encode(profile_text)
        logger.info(f"user_id={user_id} profile_embedding created: {len(embedding)}-dim")
        return embedding

    def _get_personalized_question(self, user_id: int, qtype: str, order_num: int,
                                   user_embedding: np.ndarray) -> GlobalQuestion:
        """🎯 CORRECTED: Chroma-first → Job_role thresholds → Smart storage"""

        if qtype == "introductory":
            return self.question_service.get_mandatory_questions(self.db)[(order_num - 1) ]

        user = self.question_service.get_user_profile(self.db,user_id)
        job_role = getattr(user, 'job_role', 'Software Engineer')  # From user profile

        # 1. ✅ PRIORITY: CHROMA - Semantic profile matching (ALWAYS FIRST)
        chroma_questions = self.chroma.query_similar_questions(
            user_embedding.tolist(
            ),
            question_type=qtype,
            job_role=job_role,  # Filter by job_role too
            limit=3,
            threshold=0.75
        )

        if chroma_questions:
            logger.info(f"✅ Chroma hit: {len(chroma_questions)} {qtype} for {job_role}")
            return chroma_questions[0].payload

        # 2. ✅ DYNAMIC THRESHOLDS: Job_role specific counts
        job_role_count = self.question_service.get_question_count_by_type_jobrole(self.db,qtype, job_role)

        logger.info(f"📊 {qtype} questions for '{job_role}': {job_role_count}")

        # 🎯 YOUR EXACT STRATEGY:
        if job_role_count < 20:
            ai_ratio = 0.7  # 70% AI
        elif job_role_count <= 50:
            ai_ratio = 0.4  # 40% AI
        else:
            ai_ratio = 0.2  # 20% AI

        if np.random.random() < ai_ratio:
            # 3. ✅ SMART AI GENERATION + SELECTIVE STORAGE
            question_text = self.gemini_service.generate_question_for_type(qtype, user)

            # 🚀 STORE IN CHROMA ONLY FOR REUSABLE TYPES
            if qtype in ["hr", "technical"]:
                # Reusable across interviews → Store permanently
                new_question = self.question_service.store_question(
                    self.db,
                    question_text, qtype, user.industry,
                    job_role=job_role,  # Tag with job_role
                    is_reusable=True
                )
                logger.info(f"💾 Stored reusable {qtype} question for {job_role}")
                return new_question
            else:  # experience/project - personalized, no storage
                # Create temp question (not stored in Chroma)
                temp_question = self.question_service.create_temp_question(
                    self.db,question_text, qtype, user_id
                )
                logger.info(f"🌪️ Temp {qtype} question (not stored)")
                return temp_question
        else:
            # 4. FALLBACK: Chroma with lower threshold (not random DB!)
            fallback_questions = self.chroma.query_similar_questions(
                user_embedding,
                question_type=qtype,
                job_role=job_role,
                limit=1,
                threshold=0.6  # Lower threshold for fallback
            )
            if fallback_questions:
                logger.info(f"🔄 Chroma fallback hit for {job_role}")
                return fallback_questions[0].payload
            else:
                # Last resort: Generate (will be stored if reusable)
                return self._get_personalized_question(user_id, qtype, order_num, user_embedding)  # Retry

    def _calculate_ai_percentage(self, qtype: str, db_count: int) -> float:
        """Dynamic AI generation based on DB size"""
        if qtype == "experience":
            return 1.0  # Always fresh

        if db_count >= 100:
            return 0.0  # All from DB
        elif db_count >= 50:
            return 0.2  # 20% AI
        elif db_count >= 20:
            return 0.4  # 40% AI
        else:
            return 0.7  # 70% AI when DB is small

    def submit_answer(self, interview_question_id: int, answer_text: str):
        """Store answer"""
        iq = (
            self.db.query(InterviewQuestion)
            .filter(InterviewQuestion.id == interview_question_id)
            .first()
        )
        if not iq:
            raise ValueError("InterviewQuestion not found")

        interview = (
            self.db.query(Interview)
            .filter(Interview.interview_id == iq.interview_id)
            .first()
        )
        if not interview:
            raise ValueError("Interview not found for this question")

        user_answer = UserAnswer(
            interview_id=iq.interview_id,
            question_id=iq.id,  # ✅ FK to interview_questions.id
            user_id=interview.user_id,
            answer_text=answer_text,
        )
        self.db.add(user_answer)
        self.db.commit()
        logger.info(f"✅ Answer stored for interview_question_id={interview_question_id}")
        return {"status": "success"}

