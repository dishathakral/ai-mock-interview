from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, JSON,Boolean
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User table for storing user profiles"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(100), index=True)
    industry_insight = Column(Text)
    bio = Column(Text)
    experience = Column(String(50))  # e.g., "0-2 years", "3-5 years"
    skills = Column(JSON)  # Store as JSON array
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Interview(Base):
    """Interview sessions table"""
    __tablename__ = "interviews"

    interview_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    score = Column(Float, nullable=True)
    status = Column(String(50), default="in_progress")  # in_progress, completed, abandoned
    industry = Column(String(100), index=True)
    job_role = Column(String(100), index=True)
    total_questions = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GlobalQuestion(Base):
    """Global question bank shared across all users"""
    __tablename__ = "global_questions"

    question_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False, index=True)  # hr, technical, behavioral
    subcategory = Column(String(100), index=True)  # introductory, behavioral, personality
    tags = Column(JSON)  # Store as JSON array
    industry = Column(String(100), index=True, default="general")
    job_role = Column(String(100), index=True, default="general")
    difficulty = Column(String(20), index=True)  # easy, medium, hard
    expected_answer = Column(Text, nullable=True)
    usage_count = Column(Integer, default=0)
    is_static = Column(Integer, default=0)  # 1 for static questions, 0 for generated
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_mandatory = Column(
        Boolean,
        nullable=True,
        server_default=None  # NULL means optional
    )

class InterviewQuestion(Base):
    """Questions asked in specific interview sessions"""
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    interview_id = Column(Integer, ForeignKey("interviews.interview_id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("global_questions.question_id"), nullable=True)
    question_text = Column(Text, nullable=False)  # Denormalized for easy retrieval
    question_type = Column(String(50), nullable=False)
    asked_at = Column(DateTime(timezone=True), server_default=func.now())
    order_number = Column(Integer, nullable=False)  # Sequence in interview


class UserAnswer(Base):
    """User responses to interview questions"""
    __tablename__ = "user_answers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    interview_id = Column(Integer, ForeignKey("interviews.interview_id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("interview_questions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    answer_text = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    score = Column(Float, nullable=True)  # Individual question score
