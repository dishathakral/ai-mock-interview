from sqlalchemy.orm import Session
from app.database.models import User, Interview
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class UserService:
    """Service layer for user management"""

    @staticmethod
    def create_user(db: Session, user_data: Dict) -> User:
        """Create new user"""
        try:
            user = User(**user_data)
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Created user with ID: {user.id}")
            return user
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating user: {e}")
            raise

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def start_interview(db: Session, user_id: int, job_role: str, industry: str) -> Interview:
        """Start new interview session"""
        try:
            interview = Interview(
                user_id=user_id,
                job_role=job_role,
                industry=industry,
                status="in_progress"
            )
            db.add(interview)
            db.commit()
            db.refresh(interview)
            logger.info(f"Started interview {interview.interview_id} for user {user_id}")
            return interview
        except Exception as e:
            db.rollback()
            logger.error(f"Error starting interview: {e}")
            raise

    @staticmethod
    def get_interview(db: Session, interview_id: int) -> Optional[Interview]:
        """Get interview by ID"""
        return db.query(Interview).filter(
            Interview.interview_id == interview_id
        ).first()
