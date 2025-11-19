# """
# API Routes for AI Mock Interview System
# Complete endpoints supporting all basic operations
# """
#
# from fastapi import APIRouter, Depends, HTTPException, status, Query
# from sqlalchemy.orm import Session
# from app.database.postgres_db import get_db
# from app.database.models import GlobalQuestion, Interview, UserAnswer, InterviewQuestion
# from app.services.question_service import QuestionService
# from app.services.user_service import UserService
# from app import schemas
# from typing import List, Optional
# from datetime import datetime
# import logging
# from sqlalchemy import text
#
# logger = logging.getLogger(__name__)
# router = APIRouter()
#
#
# # ============================================================
# # USER ENDPOINTS
# # ============================================================
#
# @router.post("/users/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
# def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
#     """
#     Create a new user
#     - Checks for duplicate email
#     - Returns created user with ID
#     """
#     existing_user = UserService.get_user_by_email(db, user.email)
#     if existing_user:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"User with email {user.email} already exists"
#         )
#
#     user_data = user.model_dump()
#     new_user = UserService.create_user(db, user_data)
#     logger.info(f"Created user: {new_user.email}")
#     return new_user
#
#
# @router.get("/users/{user_id}", response_model=schemas.UserResponse)
# def get_user(user_id: int, db: Session = Depends(get_db)):
#     """Get user by ID"""
#     user = UserService.get_user_by_id(db, user_id)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"User with ID {user_id} not found"
#         )
#     return user
#
#
# @router.put("/users/{user_id}", response_model=schemas.UserResponse)
# def update_user(
#         user_id: int,
#         user_update: schemas.UserUpdate,
#         db: Session = Depends(get_db)
# ):
#     """Update user information"""
#     user = UserService.get_user_by_id(db, user_id)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"User with ID {user_id} not found"
#         )
#
#     update_data = user_update.model_dump(exclude_unset=True)
#     for field, value in update_data.items():
#         setattr(user, field, value)
#
#     db.commit()
#     db.refresh(user)
#     logger.info(f"Updated user {user_id}")
#     return user
#
#
# # ============================================================
# # INTERVIEW ENDPOINTS
# # ============================================================
#
# @router.post("/interviews/start", response_model=schemas.InterviewResponse, status_code=status.HTTP_201_CREATED)
# def start_interview(interview_data: schemas.InterviewStart, db: Session = Depends(get_db)):
#     """
#     Start a new interview session
#     - Validates user exists
#     - Creates interview record
#     - Returns interview ID and details
#     """
#     user = UserService.get_user_by_id(db, interview_data.user_id)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"User with ID {interview_data.user_id} not found"
#         )
#
#     interview = UserService.start_interview(
#         db,
#         interview_data.user_id,
#         interview_data.job_role,
#         interview_data.industry
#     )
#     logger.info(f"Started interview {interview.interview_id} for user {interview_data.user_id}")
#     return interview
#
#
# @router.get("/interviews/{interview_id}", response_model=schemas.InterviewResponse)
# def get_interview(interview_id: int, db: Session = Depends(get_db)):
#     """Get interview by ID"""
#     interview = UserService.get_interview(db, interview_id)
#     if not interview:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Interview with ID {interview_id} not found"
#         )
#     return interview
#
#
# @router.get("/interviews/user/{user_id}", response_model=List[schemas.InterviewResponse])
# def get_user_interviews(
#         user_id: int,
#         status_filter: Optional[str] = Query(None, description="Filter by status"),
#         limit: int = Query(10, ge=1, le=100),
#         db: Session = Depends(get_db)
# ):
#     """
#     Get all interviews for a user
#     - Optional status filter (in_progress, completed, abandoned)
#     - Pagination support
#     """
#     query = db.query(Interview).filter(Interview.user_id == user_id)
#
#     if status_filter:
#         query = query.filter(Interview.status == status_filter)
#
#     interviews = query.order_by(Interview.started_at.desc()).limit(limit).all()
#     return interviews
#
#
# @router.put("/interviews/{interview_id}/complete", response_model=schemas.InterviewResponse)
# def complete_interview(
#         interview_id: int,
#         completion_data: schemas.InterviewComplete,
#         db: Session = Depends(get_db)
# ):
#     """
#     Complete an interview
#     - Updates status to completed
#     - Sets completion timestamp
#     - Optional: Add final score
#     """
#     interview = db.query(Interview).filter(
#         Interview.interview_id == interview_id
#     ).first()
#
#     if not interview:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Interview with ID {interview_id} not found"
#         )
#
#     if interview.status == "completed":
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Interview is already completed"
#         )
#
#     interview.status = "completed"
#     interview.completed_at = datetime.now()
#     if completion_data.score is not None:
#         interview.score = completion_data.score
#
#     db.commit()
#     db.refresh(interview)
#     logger.info(f"Completed interview {interview_id}")
#     return interview
#
#
# # ============================================================
# # QUESTION ENDPOINTS
# # ============================================================
#
# @router.get("/questions/", response_model=List[schemas.QuestionSummary])
# def get_questions(
#         question_type: Optional[str] = Query(None, description="Filter by type"),
#         subcategory: Optional[str] = Query(None, description="Filter by subcategory"),
#         difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
#         industry: Optional[str] = Query(None, description="Filter by industry"),
#         job_role: Optional[str] = Query(None, description="Filter by job role"),
#         is_mandatory: Optional[bool] = Query(None, description="Filter by mandatory status"),
#         limit: int = Query(10, ge=1, le=100),
#         offset: int = Query(0, ge=0),
#         db: Session = Depends(get_db)
# ):
#     """
#     Get questions with flexible filtering
#     - Supports multiple filter options
#     - Pagination
#     - Works for any question category
#     """
#     query = db.query(GlobalQuestion)
#
#     if question_type:
#         query = query.filter(GlobalQuestion.question_type == question_type)
#
#     if subcategory:
#         query = query.filter(GlobalQuestion.subcategory == subcategory)
#
#     if difficulty:
#         query = query.filter(GlobalQuestion.difficulty == difficulty)
#
#     if industry:
#         query = query.filter(GlobalQuestion.industry == industry)
#
#     if job_role:
#         query = query.filter(GlobalQuestion.job_role == job_role)
#
#     if is_mandatory is not None:
#         query = query.filter(GlobalQuestion.is_mandatory == is_mandatory)
#
#     questions = query.offset(offset).limit(limit).all()
#     return questions
#
#
# @router.get("/questions/{question_id}", response_model=schemas.QuestionResponse)
# def get_question(question_id: int, db: Session = Depends(get_db)):
#     """Get specific question by ID"""
#     question = QuestionService.get_question_by_id(db, question_id)
#     if not question:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Question with ID {question_id} not found"
#         )
#     return question
#
#
# @router.get("/questions/category/{subcategory}", response_model=List[schemas.QuestionSummary])
# def get_questions_by_category(
#         subcategory: str,
#         limit: int = Query(10, ge=1, le=50),
#         mandatory_only: bool = Query(False),
#         db: Session = Depends(get_db)
# ):
#     """
#     Get questions by category (introductory, behavioral, etc.)
#     - Works for any category
#     - Optional: Filter only mandatory questions
#     """
#     questions = QuestionService.get_questions_by_category(
#         db,
#         subcategory,
#         limit,
#         mandatory_only=mandatory_only
#     )
#
#     if not questions:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"No questions found for category: {subcategory}"
#         )
#
#     return questions
#
#
# @router.get("/questions/mandatory/all", response_model=List[schemas.QuestionResponse])
# def get_all_mandatory_questions(
#         subcategory: Optional[str] = Query(None, description="Filter by subcategory"),
#         db: Session = Depends(get_db)
# ):
#     """Get all mandatory questions, optionally filtered by subcategory"""
#     questions = QuestionService.get_mandatory_questions(db, subcategory)
#     return questions
#
#
# @router.post("/questions/", response_model=schemas.QuestionResponse, status_code=status.HTTP_201_CREATED)
# def create_question(question: schemas.QuestionCreate, db: Session = Depends(get_db)):
#     """
#     Create a new question
#     - Generic questions (hr, technical, behavioral): Checked for similarity, added to ChromaDB
#     - Personalized questions (experience, project): No similarity check, PostgreSQL only
#     - Works for any question category
#     """
#     question_type = question.question_type.lower()
#
#     # Only check similarity for generic question types
#     if QuestionService.should_store_in_vector_db(question_type):
#         similar = QuestionService.check_question_similarity(
#             question.question_text,
#             question_type,
#             threshold=0.85
#         )
#
#         if similar:
#             raise HTTPException(
#                 status_code=status.HTTP_409_CONFLICT,
#                 detail=f"Similar question exists with {similar[0]['similarity']:.1%} similarity: {similar[0]['question_text'][:100]}..."
#             )
#
#     # Create question (adds to PostgreSQL + conditionally to ChromaDB)
#     question_data = question.model_dump()
#     new_question = QuestionService.create_question(db, question_data)
#
#     storage_info = "PostgreSQL + ChromaDB" if QuestionService.should_store_in_vector_db(
#         question_type) else "PostgreSQL only"
#     logger.info(f"Created question {new_question.question_id} ({storage_info}): {new_question.question_text[:50]}...")
#
#     return new_question
#
#
# @router.put("/questions/{question_id}", response_model=schemas.QuestionResponse)
# def update_question(
#         question_id: int,
#         question_update: schemas.QuestionUpdate,
#         db: Session = Depends(get_db)
# ):
#     """Update question - updates both PostgreSQL and ChromaDB if applicable"""
#     update_data = question_update.model_dump(exclude_unset=True)
#     updated_question = QuestionService.update_question(db, question_id, update_data)
#
#     if not updated_question:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Question with ID {question_id} not found"
#         )
#
#     return updated_question
#
#
# @router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
# def delete_question(question_id: int, db: Session = Depends(get_db)):
#     """Delete question from both PostgreSQL and ChromaDB"""
#     deleted = QuestionService.delete_question(db, question_id)
#
#     if not deleted:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Question with ID {question_id} not found"
#         )
#
#     return None
#
#
# @router.post("/questions/check-similarity", response_model=List[schemas.SimilarQuestionResponse])
# def check_similarity(
#         question_text: str = Query(..., min_length=10),
#         question_type: str = Query(..., description="Type of question"),
#         threshold: float = Query(0.85, ge=0.0, le=1.0),
# ):
#     """
#     Check if similar questions exist
#     - Uses vector similarity search for generic question types
#     - Returns empty list for personalized question types
#     - Returns questions above threshold
#     """
#     similar = QuestionService.check_question_similarity(
#         question_text,
#         question_type,
#         threshold
#     )
#     return similar
#
#
# @router.get("/questions/stats/summary", response_model=schemas.QuestionStatsResponse)
# def get_question_stats(db: Session = Depends(get_db)):
#     """
#     Get comprehensive question statistics
#     - Total count
#     - Mandatory vs optional
#     - Breakdown by subcategory
#     """
#     stats = QuestionService.get_question_stats(db)
#     return stats
#
#
# @router.get("/questions/role/{job_role}/count")
# def get_role_question_count(
#         job_role: str,
#         industry: str = Query("general"),
#         db: Session = Depends(get_db)
# ):
#     """Get question count for specific job role"""
#     counts = QuestionService.get_question_count_by_role(db, job_role, industry)
#     return {
#         "job_role": job_role,
#         "industry": industry,
#         "counts": counts,
#         "total": sum(counts.values())
#     }
#
#
# # ============================================================
# # ANSWER ENDPOINTS
# # ============================================================
#
# @router.post("/answers/", response_model=schemas.AnswerResponse, status_code=status.HTTP_201_CREATED)
# def submit_answer(answer: schemas.AnswerSubmit, db: Session = Depends(get_db)):
#     """
#     Submit an answer to a question
#     - Validates interview is in progress
#     - Increments question usage count
#     - Updates interview question count
#     """
#     interview = db.query(Interview).filter(
#         Interview.interview_id == answer.interview_id
#     ).first()
#
#     if not interview:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Interview with ID {answer.interview_id} not found"
#         )
#
#     if interview.status != "in_progress":
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Interview is not in progress (status: {interview.status})"
#         )
#
#     # Create answer
#     new_answer = UserAnswer(
#         interview_id=answer.interview_id,
#         question_id=answer.question_id,
#         user_id=answer.user_id,
#         answer_text=answer.answer_text,
#         expected_answer=answer.expected_answer
#     )
#
#     db.add(new_answer)
#
#     # Update stats
#     QuestionService.increment_usage_count(db, answer.question_id)
#     interview.total_questions += 1
#
#     db.commit()
#     db.refresh(new_answer)
#
#     logger.info(f"Answer submitted for question {answer.question_id} in interview {answer.interview_id}")
#     return new_answer
#
#
# @router.get("/answers/{answer_id}", response_model=schemas.AnswerResponse)
# def get_answer(answer_id: int, db: Session = Depends(get_db)):
#     """Get specific answer by ID"""
#     answer = db.query(UserAnswer).filter(UserAnswer.id == answer_id).first()
#
#     if not answer:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Answer with ID {answer_id} not found"
#         )
#
#     return answer
#
#
# @router.get("/answers/interview/{interview_id}", response_model=List[schemas.AnswerResponse])
# def get_interview_answers(interview_id: int, db: Session = Depends(get_db)):
#     """
#     Get all answers for an interview
#     - Ordered by submission time
#     - Includes scores if available
#     """
#     answers = db.query(UserAnswer).filter(
#         UserAnswer.interview_id == interview_id
#     ).order_by(UserAnswer.submitted_at).all()
#
#     if not answers:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"No answers found for interview {interview_id}"
#         )
#
#     return answers
#
#
# @router.get("/answers/interview/{interview_id}/detailed", response_model=List[schemas.AnswerDetailedResponse])
# def get_interview_answers_detailed(interview_id: int, db: Session = Depends(get_db)):
#     """
#     Get detailed answers with question context
#     - Includes question text and type
#     - Useful for generating reports
#     """
#     results = db.query(
#         UserAnswer,
#         InterviewQuestion.question_text,
#         InterviewQuestion.question_type
#     ).join(
#         InterviewQuestion,
#         UserAnswer.question_id == InterviewQuestion.id
#     ).filter(
#         UserAnswer.interview_id == interview_id
#     ).all()
#
#     if not results:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"No answers found for interview {interview_id}"
#         )
#
#     detailed_answers = []
#     for answer, question_text, question_type in results:
#         answer_dict = {
#             "id": answer.id,
#             "interview_id": answer.interview_id,
#             "question_id": answer.question_id,
#             "user_id": answer.user_id,
#             "answer_text": answer.answer_text,
#             "expected_answer": answer.expected_answer,
#             "submitted_at": answer.submitted_at,
#             "score": answer.score,
#             "question_text": question_text,
#             "question_type": question_type
#         }
#         detailed_answers.append(schemas.AnswerDetailedResponse(**answer_dict))
#
#     return detailed_answers
#
#
# @router.put("/answers/{answer_id}", response_model=schemas.AnswerResponse)
# def update_answer(
#         answer_id: int,
#         answer_update: schemas.AnswerUpdate,
#         db: Session = Depends(get_db)
# ):
#     """Update answer (edit text or add score)"""
#     answer = db.query(UserAnswer).filter(UserAnswer.id == answer_id).first()
#
#     if not answer:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Answer with ID {answer_id} not found"
#         )
#
#     update_data = answer_update.model_dump(exclude_unset=True)
#     for field, value in update_data.items():
#         setattr(answer, field, value)
#
#     db.commit()
#     db.refresh(answer)
#     logger.info(f"Updated answer {answer_id}")
#     return answer
#
#
# # ============================================================
# # UTILITY ENDPOINTS
# # ============================================================
#
# @router.get("/health", response_model=schemas.HealthCheckResponse)
# def health_check(db: Session = Depends(get_db)):
#     """
#     Health check endpoint
#     - Checks database connection
#     - Checks vector database
#     - Returns system status
#     """
#     from app.database.chroma_db import chroma_db
#
#     try:
#         db.execute(text("SELECT 1"))
#         db_status = "connected"
#     except Exception as e:
#         logger.error(f"Database health check failed: {e}")
#         db_status = "disconnected"
#
#     try:
#         vector_count = chroma_db.get_collection_count()
#         vector_status = f"connected ({vector_count} questions)"
#     except Exception as e:
#         logger.error(f"Vector DB health check failed: {e}")
#         vector_status = "disconnected"
#
#     return schemas.HealthCheckResponse(
#         status="healthy" if db_status == "connected" else "unhealthy",
#         service="AI Mock Interview API",
#         version="1.0.0",
#         database=db_status,
#         vector_db=vector_status
#     )
#
#
# @router.post("/load-static-questions", response_model=schemas.SuccessResponse)
# def load_static_questions(
#         bulk_load: schemas.BulkQuestionLoad,
#         db: Session = Depends(get_db)
# ):
#     """
#     Load static questions from JSON file
#     - Batch import questions
#     - All static questions loaded into both PostgreSQL and ChromaDB
#     - Checks for duplicates
#     """
#     try:
#         count = QuestionService.load_static_questions(db, bulk_load.file_path)
#         return schemas.SuccessResponse(
#             message=f"Successfully loaded {count} questions",
#             data={
#                 "count": count,
#                 "file_path": bulk_load.file_path,
#                 "note": "All static questions added to both PostgreSQL and ChromaDB"
#             }
#         )
#     except FileNotFoundError:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"File not found: {bulk_load.file_path}"
#         )
#     except Exception as e:
#         logger.error(f"Error loading questions: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error loading questions: {str(e)}"
#         )
#
#
# @router.get("/")
# def root():
#     """Root endpoint"""
#     return {
#         "message": "AI Mock Interview API",
#         "version": "1.0.0",
#         "docs": "/docs",
#         "health": "/api/v1/health"
#     }
#
# #Complete Interview Workflow
# app/api/routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.postgres_db import get_db
from app.database.models import User, Interview, InterviewQuestion, UserAnswer, GlobalQuestion
from app.services.question_service import QuestionService
from app import schemas
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


# ==========================================
# HEALTH CHECK
# ==========================================

@router.get("/health")
def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "service": "ai-mock-interview-api",
        "version": "1.0.0"
    }


# ==========================================
# USER MANAGEMENT
# ==========================================

@router.post("/users/", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(**user.model_dump())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"User created: {new_user.id} - {new_user.email}")
    return new_user


@router.get("/users/{user_id}", response_model=schemas.UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/users/{user_id}/interviews")
def get_user_interviews(
        user_id: int,
        db: Session = Depends(get_db)
):
    """Get all interviews for a specific user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    interviews = db.query(Interview).filter(
        Interview.user_id == user_id
    ).order_by(Interview.started_at.desc()).all()

    return {
        "user_id": user_id,
        "user_name": user.name,
        "total_interviews": len(interviews),
        "interviews": [
            {
                "interview_id": i.interview_id,
                "status": i.status,
                "industry": i.industry,
                "job_role": i.job_role,
                "started_at": i.started_at,
                "completed_at": i.completed_at,
                "total_questions": i.total_questions,
                "score": i.score
            }
            for i in interviews
        ]
    }


# ==========================================
# INTERVIEW FLOW
# ==========================================

@router.post("/interviews/start", response_model=schemas.InterviewResponse, status_code=status.HTTP_201_CREATED)
def start_interview(interview_data: schemas.InterviewStart, db: Session = Depends(get_db)):
    """
    Step 1: Start interview
    Creates interview session in 'in_progress' status
    """
    user = db.query(User).filter(User.id == interview_data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    interview = Interview(
        user_id=interview_data.user_id,
        status="in_progress",
        industry=interview_data.industry,
        job_role=interview_data.job_role,
        total_questions=0
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    logger.info(f"Interview {interview.interview_id} started for user {user.id}")
    return interview


@router.get("/interviews/{interview_id}/fetch-next-question")
def fetch_next_question(
        interview_id: int,
        use_ai: bool = False,  # Phase 2/3 feature flag
        db: Session = Depends(get_db)
):
    """
    Step 2: FETCH next question (doesn't ask it yet)

    THIS IS WHERE ALL COMPLEX LOGIC GOES (Phase 2/3):
    - Analyze user profile
    - Check interview progress
    - Query Vector DB for semantic matching
    - Call Gemini API to generate personalized questions
    - Apply similarity checks
    - Determine difficulty progression

    Current (Phase 1): Simple static question fetching
    Future (Phase 2): Will use InterviewOrchestrator + ChromaDB
    Future (Phase 3): Will integrate Gemini API for generation

    Returns:
    - Question data (NOT yet added to interview)
    - Frontend can preview before asking
    """
    # Verify interview
    interview = db.query(Interview).filter(
        Interview.interview_id == interview_id,
        Interview.status == "in_progress"
    ).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Active interview not found")

    # Get already asked questions
    asked_questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview_id
    ).all()

    asked_count = len(asked_questions)
    asked_question_ids = [q.question_id for q in asked_questions if q.question_id]

    # ============================================
    # PHASE 1: SIMPLE LOGIC (Current)
    # ============================================

    # Determine category based on progress
    if asked_count < 3:
        category = "introductory"
    elif asked_count < 8:
        category = "behavioral"
    elif asked_count < 11:
        category = "personality"
    elif asked_count < 13:
        category = "closing"
    else:
        return {
            "interview_complete": True,
            "message": "All questions completed. Call /complete to finish."
        }

    # Fetch question from database
    next_question = db.query(GlobalQuestion).filter(
        GlobalQuestion.subcategory == category,
        GlobalQuestion.is_static == 1,
        ~GlobalQuestion.question_id.in_(asked_question_ids) if asked_question_ids else True
    ).first()

    if not next_question:
        raise HTTPException(
            status_code=404,
            detail=f"No more {category} questions available"
        )

    logger.info(f"Fetched {category} question {next_question.question_id} for interview {interview_id}")

    return {
        "global_question_id": next_question.question_id,
        "question_text": next_question.question_text,
        "question_type": next_question.question_type,
        "subcategory": category,
        "difficulty": next_question.difficulty,
        "expected_answer": next_question.expected_answer,
        "next_order_number": asked_count + 1,
        "total_asked": asked_count,
        "interview_complete": False,
        "message": "Call /ask-question to add this question to the interview"
    }

    # ============================================
    # PHASE 2/3: ADVANCED LOGIC (Future)
    # ============================================
    # if use_ai:
    #     # Use InterviewOrchestrator to decide next question
    #     result = InterviewOrchestrator.get_next_question(
    #         db=db,
    #         interview_id=interview_id,
    #         user_profile=user,
    #         previous_answers=get_previous_answers(interview_id),
    #         use_gemini=True
    #     )
    #
    #     # May call:
    #     # - ChromaDB for semantic search
    #     # - Gemini API for generation
    #     # - Similarity checker
    #
    #     return result


@router.post("/interviews/{interview_id}/ask-question", status_code=status.HTTP_201_CREATED)
def ask_question(
        interview_id: int,
        question_request: schemas.AskQuestionRequest,
        db: Session = Depends(get_db)
):
    """
    Step 3: ASK the question (add to interview)

    Takes a question (from fetch-next-question or manual selection)
    and adds it to the interview as an InterviewQuestion record.

    Only after this can the user answer the question.
    """
    # Verify interview
    interview = db.query(Interview).filter(
        Interview.interview_id == interview_id,
        Interview.status == "in_progress"
    ).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Active interview not found")

    # Get the global question
    global_question = db.query(GlobalQuestion).filter(
        GlobalQuestion.question_id == question_request.global_question_id
    ).first()

    if not global_question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Check if already asked in this interview
    existing = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview_id,
        InterviewQuestion.question_id == question_request.global_question_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Question already asked in this interview"
        )

    # Count existing questions for order number
    question_count = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview_id
    ).count()

    # Create interview question
    interview_question = InterviewQuestion(
        interview_id=interview_id,
        user_id=interview.user_id,
        question_id=global_question.question_id,
        question_text=global_question.question_text,
        question_type=global_question.question_type,
        order_number=question_count + 1
    )

    db.add(interview_question)
    db.commit()
    db.refresh(interview_question)

    logger.info(f"Question {interview_question.id} asked in interview {interview_id}")

    return {
        "interview_question_id": interview_question.id,
        "question_text": interview_question.question_text,
        "question_type": interview_question.question_type,
        "order_number": interview_question.order_number,
        "message": "Question added to interview. User can now answer it."
    }


@router.post("/interviews/{interview_id}/questions/{interview_question_id}/answer", status_code=status.HTTP_201_CREATED)
def submit_answer(
        interview_id: int,
        interview_question_id: int,
        answer_data: schemas.AnswerSubmit,
        db: Session = Depends(get_db)
):
    """
    Step 4: ANSWER the question
    """
    # Verify interview
    interview = db.query(Interview).filter(
        Interview.interview_id == interview_id
    ).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    if interview.status != "in_progress":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot answer questions in {interview.status} interview"
        )

    # Verify question exists in THIS interview
    interview_question = db.query(InterviewQuestion).filter(
        InterviewQuestion.id == interview_question_id,
        InterviewQuestion.interview_id == interview_id
    ).first()

    if not interview_question:
        raise HTTPException(
            status_code=404,
            detail="Question not found in this interview. Must call /ask-question first."
        )

    # Check if already answered
    existing_answer = db.query(UserAnswer).filter(
        UserAnswer.question_id == interview_question_id,
        UserAnswer.interview_id == interview_id
    ).first()

    if existing_answer:
        raise HTTPException(
            status_code=400,
            detail="Answer already submitted for this question"
        )

    # Create answer
    user_answer = UserAnswer(
        interview_id=interview_id,
        question_id=interview_question_id,
        user_id=interview.user_id,
        answer_text=answer_data.answer_text,
        expected_answer=None,
        score=None  # Will be evaluated in Phase 3
    )

    db.add(user_answer)

    # Increment usage count
    if interview_question.question_id:
        global_q = db.query(GlobalQuestion).filter(
            GlobalQuestion.question_id == interview_question.question_id
        ).first()
        if global_q:
            global_q.usage_count += 1

    db.commit()
    db.refresh(user_answer)

    logger.info(f"Answer submitted for question {interview_question_id}")

    return {
        "answer_id": user_answer.id,
        "interview_id": interview_id,
        "question_id": interview_question_id,
        "status": "submitted",
        "message": "Answer recorded. Call /fetch-next-question to continue."
    }


@router.put("/interviews/{interview_id}/complete", response_model=schemas.InterviewResponse)
def complete_interview(
        interview_id: int,
        db: Session = Depends(get_db)
):
    """
    Step 5: Complete interview
    Marks interview as completed and calculates statistics
    """
    interview = db.query(Interview).filter(
        Interview.interview_id == interview_id
    ).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    if interview.status == "completed":
        raise HTTPException(status_code=400, detail="Interview already completed")

    answer_count = db.query(UserAnswer).filter(
        UserAnswer.interview_id == interview_id
    ).count()

    interview.status = "completed"
    interview.total_questions = answer_count
    interview.completed_at = func.now()

    db.commit()
    db.refresh(interview)

    logger.info(f"Interview {interview_id} completed with {answer_count} answers")
    return interview


@router.get("/interviews/{interview_id}")
def get_interview_details(
        interview_id: int,
        db: Session = Depends(get_db)
):
    """Get basic interview details"""
    interview = db.query(Interview).filter(
        Interview.interview_id == interview_id
    ).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Count questions and answers
    question_count = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview_id
    ).count()

    answer_count = db.query(UserAnswer).filter(
        UserAnswer.interview_id == interview_id
    ).count()

    return {
        "interview_id": interview.interview_id,
        "user_id": interview.user_id,
        "status": interview.status,
        "industry": interview.industry,
        "job_role": interview.job_role,
        "started_at": interview.started_at,
        "completed_at": interview.completed_at,
        "questions_asked": question_count,
        "questions_answered": answer_count,
        "score": interview.score
    }


@router.get("/interviews/{interview_id}/questions")
def get_interview_questions(
        interview_id: int,
        db: Session = Depends(get_db)
):
    """Get all questions asked in this interview"""
    interview = db.query(Interview).filter(
        Interview.interview_id == interview_id
    ).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview_id
    ).order_by(InterviewQuestion.order_number).all()

    result = []
    for q in questions:
        answer = db.query(UserAnswer).filter(
            UserAnswer.question_id == q.id
        ).first()

        result.append({
            "interview_question_id": q.id,
            "order_number": q.order_number,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "answered": answer is not None,
            "answer_text": answer.answer_text if answer else None,
            "score": answer.score if answer else None
        })

    return {
        "interview_id": interview_id,
        "total_questions": len(questions),
        "questions": result
    }


@router.get("/interviews/{interview_id}/summary")
def get_interview_summary(
        interview_id: int,
        db: Session = Depends(get_db)
):
    """
    Get complete summary of the interview
    Shows all questions, answers, and statistics
    """
    interview = db.query(Interview).filter(
        Interview.interview_id == interview_id
    ).first()

    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Get user info
    user = db.query(User).filter(User.id == interview.user_id).first()

    # Get all questions
    questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview_id
    ).order_by(InterviewQuestion.order_number).all()

    # Get all answers
    answers = db.query(UserAnswer).filter(
        UserAnswer.interview_id == interview_id
    ).all()

    # Build answer map
    answer_map = {a.question_id: a for a in answers}

    # Build question list
    question_list = []
    for q in questions:
        answer = answer_map.get(q.id)
        question_list.append({
            "order": q.order_number,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "answer_text": answer.answer_text if answer else None,
            "answered": answer is not None,
            "score": answer.score if answer else None,
            "submitted_at": answer.submitted_at if answer else None
        })

    return {
        "interview_id": interview.interview_id,
        "user": {
            "user_id": user.id,
            "name": user.name,
            "email": user.email
        } if user else None,
        "status": interview.status,
        "industry": interview.industry,
        "job_role": interview.job_role,
        "started_at": interview.started_at,
        "completed_at": interview.completed_at,
        "total_questions": len(questions),
        "total_answers": len(answers),
        "overall_score": interview.score,
        "questions": question_list
    }


# ==========================================
# QUESTION MANAGEMENT
# ==========================================

@router.post("/questions/", response_model=schemas.QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(question: schemas.QuestionCreate, db: Session = Depends(get_db)):
    """
    Create a new question
    - Generic questions (hr, technical, behavioral): Checked for similarity, added to ChromaDB
    - Personalized questions (experience, project): No similarity check, PostgreSQL only
    """
    question_type = question.question_type.lower()

    # Only check similarity for generic question types
    if QuestionService.should_store_in_vector_db(question_type):
        similar = QuestionService.check_question_similarity(
            question.question_text,
            threshold=0.85
        )

        if similar:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Similar question exists with {similar[0]['similarity']:.1%} similarity: {similar[0]['question_text'][:100]}..."
            )

    # Create question
    question_data = question.model_dump()
    new_question = QuestionService.create_question(db, question_data)

    storage_info = "PostgreSQL + ChromaDB" if QuestionService.should_store_in_vector_db(
        question_type) else "PostgreSQL only"
    logger.info(f"Created question {new_question.question_id} ({storage_info}): {new_question.question_text[:50]}...")

    return new_question


@router.get("/questions/category/{subcategory}")
def get_questions_by_category(
        subcategory: str,
        limit: int = 10,
        db: Session = Depends(get_db)
):
    """
    Get questions by subcategory
    Useful for previewing available questions
    """
    questions = QuestionService.get_questions_by_category(
        db=db,
        subcategory=subcategory,
        limit=limit
    )

    if not questions:
        raise HTTPException(
            status_code=404,
            detail=f"No questions found for subcategory: {subcategory}"
        )

    return {
        "subcategory": subcategory,
        "count": len(questions),
        "questions": questions
    }


@router.get("/questions/{question_id}", response_model=schemas.QuestionResponse)
def get_question_by_id(question_id: int, db: Session = Depends(get_db)):
    """Get specific question by ID"""
    question = QuestionService.get_question_by_id(db, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.get("/questions/stats/summary")
def get_question_statistics(db: Session = Depends(get_db)):
    """Get statistics about questions in database"""
    stats = QuestionService.get_question_stats(db)
    return stats


@router.post("/questions/check-similarity")
def check_similarity(
        question_text: str,
        question_type: str = "hr",
        threshold: float = 0.85
):
    """
    Check if similar question exists in ChromaDB
    Useful for testing and validation
    """
    similar = QuestionService.check_question_similarity(
        question_text=question_text,
        question_type=question_type ,
        threshold=threshold
    )

    if similar:
        return {
            "has_similar": True,
            "count": len(similar),
            "similar_questions": similar
        }

    return {
        "has_similar": False,
        "message": "No similar questions found"
    }
