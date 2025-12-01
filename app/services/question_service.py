"""
Question Service - Business logic for question management
Handles conditional ChromaDB storage based on question type
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_
from app.database.models import GlobalQuestion, InterviewQuestion
from app.database.chroma_db import chroma_db
from app.config import get_settings
from typing import List, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

# Question types that should be stored in ChromaDB (for similarity checking)
VECTOR_DB_QUESTION_TYPES = ['hr', 'technical', 'behavioral', 'situational', 'coding', 'system_design']

# Question types that are personalized (no vector storage needed)
PERSONALIZED_QUESTION_TYPES = ['experience', 'project', 'personalized']


class QuestionService:
    """Service layer for question management"""

    @staticmethod
    def should_store_in_vector_db(question_type: str) -> bool:
        """
        Determine if question should be stored in ChromaDB
        Returns True for generic questions (hr, technical, behavioral)
        Returns False for personalized questions (experience, project)
        """
        return question_type.lower() in [q.lower() for q in VECTOR_DB_QUESTION_TYPES]

    @staticmethod
    def is_personalized_question(question_type: str) -> bool:
        """
        Check if question is personalized
        Personalized questions are user-specific and don't need similarity checking
        """
        return question_type.lower() in [q.lower() for q in PERSONALIZED_QUESTION_TYPES]

    @staticmethod
    def load_static_questions(db: Session, json_file_path: str) -> int:
        """
        Load static questions from JSON file into database
        Static questions are ALWAYS loaded into both PostgreSQL and ChromaDB
        because they only contain generic types (hr, behavioral, situational)

        Returns:
            int: Number of questions loaded
        """
        try:
            with open(json_file_path, 'r') as f:
                questions_data = json.load(f)

            count = 0
            vector_db_count = 0

            for category, questions in questions_data.items():
                logger.info(f"Processing category: {category}")

                for q_data in questions:
                    # Check if question already exists
                    existing = db.query(GlobalQuestion).filter(
                        GlobalQuestion.question_text == q_data['question_text']
                    ).first()

                    if not existing:
                        # Create new question in PostgreSQL (ALL static questions)
                        question = GlobalQuestion(
                            question_text=q_data['question_text'],
                            question_type=q_data['question_type'],
                            subcategory=q_data['subcategory'],
                            tags=q_data['tags'],
                            industry=q_data['industry'],
                            job_role=q_data['job_role'],
                            difficulty=q_data['difficulty'],
                            expected_answer=q_data.get('expected_answer'),
                            is_static=1,
                            is_mandatory=q_data.get('is_mandatory', False)
                        )
                        db.add(question)
                        db.flush()  # Get the generated question_id

                        # Add to ChromaDB with INDIVIDUAL PARAMETERS
                        chroma_db.add_question(
                            question_id=question.question_id,
                            question_text=question.question_text,
                            question_type=question.question_type,
                            industry=question.industry,
                            job_role=question.job_role,
                            difficulty=question.difficulty,
                            tags=q_data.get('tags', []),
                            subcategory=question.subcategory,
                            is_static=1
                        )

                        vector_db_count += 1
                        logger.debug(f"✓ Added to PostgreSQL + ChromaDB: {q_data['question_text'][:50]}...")
                        count += 1
                    else:
                        logger.debug(f"→ Already exists: {q_data['question_text'][:50]}...")

            db.commit()
            logger.info(f"✓ Loaded {count} static questions into PostgreSQL")
            logger.info(f"✓ Added {vector_db_count} static questions to ChromaDB")
            return count

        except FileNotFoundError:
            logger.error(f"File not found: {json_file_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error loading static questions: {e}")
            raise

    @staticmethod
    def get_questions_by_category(
            db: Session,
            subcategory: str,
            limit: int = 10,
            mandatory_only: bool = False
    ) -> List[GlobalQuestion]:
        """
        Retrieve questions by subcategory

        Args:
            db: Database session
            subcategory: Question subcategory (e.g., 'introductory', 'behavioral')
            limit: Maximum number of questions to return
            mandatory_only: If True, return only mandatory questions
        """
        query = db.query(GlobalQuestion).filter(
            GlobalQuestion.subcategory == subcategory,
            GlobalQuestion.is_static == 1
        )

        if mandatory_only:
            query = query.filter(GlobalQuestion.is_mandatory == True)

        return query.limit(limit).all()

    @staticmethod
    def get_mandatory_questions(
            db: Session,
            subcategory: Optional[str] = None
    ) -> List[GlobalQuestion]:
        """Get all mandatory questions, optionally filtered by subcategory"""
        query = db.query(GlobalQuestion).filter(
            GlobalQuestion.is_mandatory == True,
            GlobalQuestion.is_static == 1
        ).order_by(GlobalQuestion.question_id.asc())

        if subcategory:
            query = query.filter(GlobalQuestion.subcategory == subcategory)

        return query.all()

    @staticmethod
    def get_question_by_id(db: Session, question_id: int) -> Optional[GlobalQuestion]:
        """Get specific question by ID"""
        return db.query(GlobalQuestion).filter(
            GlobalQuestion.question_id == question_id
        ).first()

    @staticmethod
    def check_question_similarity(
            question_text: str,
            question_type: str,
            threshold: Optional[float] = None
    ) -> List[Dict]:
        """
        Check if similar question exists in vector database
        ONLY checks for generic question types
        Personalized questions skip similarity check

        Args:
            question_text: The question text to check
            question_type: Type of question (hr, technical, experience, etc.)
            threshold: Similarity threshold (uses config default if not provided)

        Returns:
            List of similar questions above threshold (empty for personalized questions)
        """
        # Skip similarity check for personalized questions
        if not QuestionService.should_store_in_vector_db(question_type):
            logger.info(f"Skipping similarity check for personalized question type: {question_type}")
            return []

        # Use config threshold if not provided
        if threshold is None:
            threshold = settings.SIMILARITY_THRESHOLD

        return chroma_db.find_similar_questions(question_text, n_results=5, threshold=threshold)

    # @staticmethod
    # def create_question(db: Session, question_data: Dict) -> GlobalQuestion:
    #     """
    #     Create new question in database
    #     Conditionally adds to ChromaDB based on question type
    #
    #     Args:
    #         db: Database session
    #         question_data: Dictionary with question fields
    #
    #     Returns:
    #         Created GlobalQuestion object
    #     """
    #     try:
    #         question = GlobalQuestion(**question_data)
    #         db.add(question)
    #         db.flush()
    #
    #         question_type = question_data.get('question_type', '')
    #
    #         # Add to ChromaDB ONLY for generic question types
    #         if QuestionService.should_store_in_vector_db(question_type):
    #             metadata = {
    #                 'question_type': question_type,
    #                 'subcategory': question_data.get('subcategory'),
    #                 'industry': question_data.get('industry', 'general'),
    #                 'job_role': question_data.get('job_role', 'general'),
    #                 'difficulty': question_data.get('difficulty', 'medium'),
    #                 'is_mandatory': str(question_data.get('is_mandatory', 'null'))
    #             }
    #             chroma_db.add_question(
    #                 question.question_id,
    #                 question.question_text,
    #                 metadata
    #             )
    #             logger.info(f"Created question {question.question_id} in PostgreSQL + ChromaDB")
    #         else:
    #             logger.info(f"Created question {question.question_id} in PostgreSQL only (personalized)")
    #
    #         db.commit()
    #         return question
    #
    #     except Exception as e:
    #         db.rollback()
    #         logger.error(f"Error creating question: {e}")
    #         raise
    @staticmethod
    def create_question(db: Session, question_data: Dict) -> GlobalQuestion:
        """
        Create new question in database
        Conditionally adds to ChromaDB based on question type

        Args:
            db: Database session
            question_data: Dictionary with question fields

        Returns:
            Created GlobalQuestion object
        """
        try:
            question = GlobalQuestion(**question_data)
            db.add(question)
            db.flush()

            question_type = question_data.get('question_type', '')

            # Add to ChromaDB ONLY for generic question types
            if QuestionService.should_store_in_vector_db(question_type):
                # Pass individual fields separately instead of metadata dict
                chroma_db.add_question(
                    question_id=question.question_id,
                    question_text=question.question_text,
                    question_type=question_type,
                    subcategory=question_data.get('subcategory'),
                    industry=question_data.get('industry', 'general'),
                    job_role=question_data.get('job_role', 'general'),
                    difficulty=question_data.get('difficulty', 'medium'),
                    tags=question_data.get('tags', []),
                    is_static=question_data.get('is_static', 0)
                )
                logger.info(f"Created question {question.question_id} in PostgreSQL + ChromaDB")
            else:
                logger.info(f"Created question {question.question_id} in PostgreSQL only (personalized)")

            db.commit()
            return question

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating question: {e}")
            raise

    @staticmethod
    def update_question(db: Session, question_id: int, update_data: Dict) -> Optional[GlobalQuestion]:
        """
        Update existing question
        Updates ChromaDB if question type uses vector storage
        """
        try:
            question = db.query(GlobalQuestion).filter(
                GlobalQuestion.question_id == question_id
            ).first()

            if not question:
                return None

            # Update fields
            for field, value in update_data.items():
                if hasattr(question, field) and value is not None:
                    setattr(question, field, value)

            # Update ChromaDB if it's a generic question type
            if QuestionService.should_store_in_vector_db(question.question_type):
                # Delete old entry
                chroma_db.delete_question(question_id)

                # Add updated entry
                metadata = {
                    'question_type': question.question_type,
                    'subcategory': question.subcategory,
                    'industry': question.industry,
                    'job_role': question.job_role,
                    'difficulty': question.difficulty,
                    'is_mandatory': str(question.is_mandatory)
                }
                chroma_db.add_question(
                    question.question_id,
                    question.question_text,
                    metadata
                )
                logger.info(f"Updated question {question_id} in PostgreSQL + ChromaDB")
            else:
                logger.info(f"Updated question {question_id} in PostgreSQL only")

            db.commit()
            db.refresh(question)
            return question

        except Exception as e:
            db.rollback()
            logger.error(f"Error updating question: {e}")
            raise

    @staticmethod
    def delete_question(db: Session, question_id: int) -> bool:
        """
        Delete question from both databases
        """
        try:
            question = db.query(GlobalQuestion).filter(
                GlobalQuestion.question_id == question_id
            ).first()

            if not question:
                return False

            # Delete from ChromaDB if it's stored there
            if QuestionService.should_store_in_vector_db(question.question_type):
                chroma_db.delete_question(question_id)
                logger.info(f"Deleted question {question_id} from ChromaDB")

            # Delete from PostgreSQL
            db.delete(question)
            db.commit()
            logger.info(f"Deleted question {question_id} from PostgreSQL")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting question: {e}")
            raise

    @staticmethod
    def get_question_count_by_role(
            db: Session,
            job_role: str,
            industry: str = "general"
    ) -> Dict[str, int]:
        """Get count of questions by type for specific job role"""
        all_types = VECTOR_DB_QUESTION_TYPES + PERSONALIZED_QUESTION_TYPES
        counts = {}

        for q_type in all_types:
            count = db.query(func.count(GlobalQuestion.question_id)).filter(
                and_(
                    GlobalQuestion.job_role == job_role,
                    GlobalQuestion.industry == industry,
                    GlobalQuestion.question_type == q_type
                )
            ).scalar()
            counts[q_type] = count

        return counts

    @staticmethod
    def get_question_stats(db: Session) -> Dict[str, any]:
        """Get comprehensive question statistics"""
        total_questions = db.query(func.count(GlobalQuestion.question_id)).scalar()
        mandatory_questions = db.query(func.count(GlobalQuestion.question_id)).filter(
            GlobalQuestion.is_mandatory == True
        ).scalar()
        optional_questions = db.query(func.count(GlobalQuestion.question_id)).filter(
            or_(
                GlobalQuestion.is_mandatory == False,
                GlobalQuestion.is_mandatory == None
            )
        ).scalar()

        # Count by subcategory
        subcategory_counts = db.query(
            GlobalQuestion.subcategory,
            func.count(GlobalQuestion.question_id)
        ).group_by(GlobalQuestion.subcategory).all()

        # Count by question type
        type_counts = db.query(
            GlobalQuestion.question_type,
            func.count(GlobalQuestion.question_id)
        ).group_by(GlobalQuestion.question_type).all()

        # Count questions in vector DB vs personalized
        vector_db_count = 0
        personalized_count = 0
        for q_type, count in type_counts:
            if QuestionService.should_store_in_vector_db(q_type):
                vector_db_count += count
            else:
                personalized_count += count

        return {
            'total': total_questions,
            'mandatory': mandatory_questions,
            'optional': optional_questions,
            'by_subcategory': {cat: count for cat, count in subcategory_counts},
            'by_type': {q_type: count for q_type, count in type_counts},
            'in_vector_db': vector_db_count,
            'personalized': personalized_count
        }

    @staticmethod
    def increment_usage_count(db: Session, question_id: int):
        """Increment usage counter when question is asked"""
        question = db.query(GlobalQuestion).filter(
            GlobalQuestion.question_id == question_id
        ).first()

        if question:
            question.usage_count += 1
            db.commit()
            logger.debug(f"Incremented usage count for question {question_id}")

    # 🔥 ADD THESE 3 METHODS (copy-paste exactly)

    @staticmethod
    def get_user_profile(db: Session, user_id: int):
        """Get user profile for personalization"""
        from app.database.models import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        return user

    @staticmethod
    def get_question_count_by_type_jobrole(db: Session, question_type: str, job_role: str) -> int:
        """Count questions by type + job_role (YOUR threshold logic)"""
        from sqlalchemy import func
        count = db.query(func.count(GlobalQuestion.question_id)).filter(
            and_(
                GlobalQuestion.question_type == question_type,
                GlobalQuestion.job_role == job_role
            )
        ).scalar() or 0
        return count

    @staticmethod
    def store_question(db: Session, question_text: str, question_type: str, industry: str,
                       job_role: str = None, is_reusable: bool = True) -> GlobalQuestion:
        """Store reusable question (uses your existing create_question)"""
        question_data = {
            'question_text': question_text,
            'question_type': question_type,
            'industry': industry,
            'job_role': job_role,
            'is_static': 0,
            'is_mandatory': False,
            'difficulty': 'medium'
        }
        return QuestionService.create_question(db, question_data)

    @staticmethod
    def create_temp_question(db: Session, question_text: str, question_type: str, user_id: int) -> GlobalQuestion:
        """Temp question for experience (no Chroma)"""
        question_data = {
            'question_text': question_text,
            'question_type': question_type,
            'is_static': 0,
            'is_mandatory': False
        }
        return QuestionService.create_question(db, question_data)

