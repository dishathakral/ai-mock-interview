
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status,Body
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.postgres_db import get_db
from app.database.models import User, Interview, InterviewQuestion, UserAnswer, GlobalQuestion
from app.services.question_service import QuestionService
from app.services.question_generation_service import QuestionGenerationService
from app.services.user_service import UserService
from app.services.interview_orchestrator import InterviewOrchestrator
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

# @router.post("/interviews/start", response_model=schemas.InterviewResponse, status_code=status.HTTP_201_CREATED)
# def start_interview(interview_data: schemas.InterviewStart, db: Session = Depends(get_db)):
#     """
#     Step 1: Start interview
#     Creates interview session in 'in_progress' status
#     """
#     user = db.query(User).filter(User.id == interview_data.user_id).first()
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#
#     interview = Interview(
#         user_id=interview_data.user_id,
#         status="in_progress",
#         industry=interview_data.industry,
#         job_role=interview_data.job_role,
#         total_questions=0
#     )
#     db.add(interview)
#     db.commit()
#     db.refresh(interview)
#
#     logger.info(f"Interview {interview.interview_id} started for user {user.id}")
#     return interview


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
        threshold: float = 0.6
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


#
# @router.post("/questions/generate/hr", response_model=schemas.QuestionResponse)
# def generate_hr_question(
#         user_id: int = Body(..., embed=True),
#         job_role: str = Body(..., embed=True),
#         industry: str = Body(..., embed=True),
#         db: Session = Depends(get_db)
# ):
#     """
#     Generate or retrieve similar HR question for given job_role and industry
#     """
#     try:
#         question = QuestionGenerationService.generate_and_store_hr_question(db, job_role, industry)
#         return question
#     except Exception as e:
#         logger.error(f"Error generating HR question: {e}")
#         raise HTTPException(status_code=500, detail=str(e))
#
#
# @router.post("/questions/generate/technical", response_model=schemas.QuestionResponse)
# def generate_technical_question(
#         user_id: int = Body(..., embed=True),
#         job_role: str = Body(..., embed=True),
#         skills: str = Body(default="", embed=True),
#         db: Session = Depends(get_db)
# ):
#     """
#     Generate or retrieve similar technical question for given job_role and skills
#     """
#     try:
#         question = QuestionGenerationService.generate_and_store_technical_question(db, job_role, skills)
#         return question
#     except Exception as e:
#         logger.error(f"Error generating technical question: {e}")
#         raise HTTPException(status_code=500, detail=str(e))


# @router.post("/questions/generate/experience", response_model=schemas.QuestionResponse)
# def generate_experience_question(
#         user_id: int = Body(..., embed=True),
#         db: Session = Depends(get_db)
# ):
#     """
#     Generate personalized experience question based on user profile
#     """
#     try:
#         # Fetch user profile from DB (simplified; extend with projects in future)
#         # user = user_service.get_user_by_id(db, user_id)
#         user=UserService.get_user_by_id(db, user_id)
#         if not user:
#             raise HTTPException(status_code=404, detail="User not found")
#
#         # Prepare user profile string for Gemini prompt
#         user_profile = f"Name: {user.name}. Industry: {user.industry}. Bio: {user.bio or ''}. Skills: {', '.join(user.skills) if user.skills else ''}."
#
#         question = QuestionGenerationService.generate_personalized_experience_question(db, user_profile)
#         return question
#     except Exception as e:
#         logger.error(f"Error generating experience question: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

@router.post("/questions/generate/experience", response_model=schemas.QuestionResponse)
def generate_experience_question(
        user_id: int = Body(..., embed=True),
        db: Session = Depends(get_db)
):
    """
    Generate personalized experience question based on user profile.
    Includes experience details and projects.
    """
    try:
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        projects_str = ""
        if user.projects:
            projects_str = " Projects: " + ", ".join([p.get("title", "") for p in user.projects])

        skills_str = ", ".join(user.skills) if user.skills else ""

        user_profile = (
            f"Name: {user.name}. Industry: {user.industry}.job role:{user.job_role}"
            f" Bio: {user.bio or ''}."
            f" Experience: {user.experience or ''}."
            f" Details: {user.experience_details or ''}."
            f"{projects_str}"
            f" Skills: {skills_str}."
        )

        question = QuestionGenerationService.generate_personalized_experience_question(db, user_profile)
        return question
    except Exception as e:
        logger.error(f"Error generating experience question: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/questions/generate/hr", response_model=schemas.QuestionResponse)
def generate_hr_question(
        user_id: int = Body(..., embed=True),
        db: Session = Depends(get_db)
):
    """
    Generate or retrieve similar HR question based on user profile.
    Since job_role is not in user table, we omit it and use available fields.
    """
    try:
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        industry = user.industry or "general"
        # Compose user profile text including bio, experience, skills, etc.
        user_profile = (
            f"Industry: {industry}. "
            f"job_role: {user.job_role}. "
            f"Bio: {user.bio or ''}. "
            f"Experience: {user.experience or ''}. "
            f"Details: {user.experience_details or ''}. "
            f"Skills: {', '.join(user.skills) if user.skills else ''}. "
            f"Projects: {', '.join([p.get('title', '') for p in user.projects]) if user.projects else ''}."
        )

        # Use the user_profile as the prompt basis in your question generation service,
        # or alternatively, just pass industry for HR questions as a fallback
        question = QuestionGenerationService.generate_and_store_hr_question(db, job_role=industry, industry=industry)
        return question
    except Exception as e:
        logger.error(f"Error generating HR question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# @router.post("/questions/generate/technical", response_model=schemas.QuestionResponse)
# def generate_technical_question(
#         user_id: int = Body(..., embed=True),
#         db: Session = Depends(get_db)
# ):
#     """
#     Generate or retrieve similar technical question based on user profile fields.
#     """
#     try:
#         user = UserService.get_user_by_id(db, user_id)
#         if not user:
#             raise HTTPException(status_code=404, detail="User not found")
#
#         skills = ", ".join(user.skills) if user.skills else ""
#         industry = user.industry or "general"
#
#         # In absence of job_role, we use industry or generic role placeholder
#         question = QuestionGenerationService.generate_and_store_technical_question(db, job_role=industry, skills=skills)
#         return question
#     except Exception as e:
#         logger.error(f"Error generating technical question: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

@router.post("/questions/generate/technical", response_model=schemas.QuestionResponse)
def generate_technical_question(
        user_id: int = Body(..., embed=True),
        db: Session = Depends(get_db)
):
    """
    Generate or retrieve similar technical question based on user profile fields.
    """
    try:
        user = UserService.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # ✅ NEW: Use job_role column, fallback to industry
        job_role = getattr(user, 'job_role', user.industry or 'Software Engineer')
        skills = ", ".join(user.skills) if user.skills else ""
        industry = user.industry or "general"

        logger.info(f"🔍 Technical Q for user={user_id}, role={job_role}, skills={skills[:50]}...")

        # Keep your existing Phase 2 service call
        question = QuestionGenerationService.generate_and_store_technical_question(
            db,
            job_role=job_role,  # ✅ Now uses real job_role
            skills=skills
        )
        return question

    except Exception as e:
        logger.error(f"Error generating technical question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 🔥 ADD THESE 4 ENDPOINTS (append to existing router)
@router.post("/interviews/", response_model=dict)
async def create_interview(request: schemas.CreateInterviewRequest, db: Session = Depends(get_db)):
    """🎯 PHASE 3: Create new interview"""
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    # Create interview record
    interview = Interview(
        user_id=request.user_id,
        status="active",
        started_at=datetime.utcnow()
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    logger.info(f"✅ Created interview {interview.interview_id} for user {user.id}")
    return {"interview_id": interview.interview_id, "status": interview.status}


@router.post("/interviews/{interview_id}/start")
async def start_interview(interview_id: int, db: Session = Depends(get_db)):
    """🎯 PHASE 3: Mark interview as started (no pre-loading)"""
    interview = db.query(Interview).filter(Interview.interview_id == interview_id).first()
    if not interview:
        raise HTTPException(404, "Interview not found")

    # Just mark as started - NO question pre-loading!
    interview.status = "in_progress"
    db.commit()

    orchestrator = InterviewOrchestrator(db)

    # Return FIRST question immediately (user can answer it)
    first_question = orchestrator.get_next_question(interview_id)

    logger.info(f"Interview {interview_id} started - first question served")

    return {
        "interview_id": interview_id,
        "first_question": first_question,  # Single question object
        "message": "Interview started - answer first question to continue",
        "next_action": "POST /interviews/{interview_id}/next-question"
    }


@router.post("/interviews/{interview_id}/next-question")
async def next_question(interview_id: int, db: Session = Depends(get_db)):
    """🎯 PHASE 3: SINGLE ENDPOINT - Smart next question"""
    orchestrator = InterviewOrchestrator(db)
    result = orchestrator.get_next_question(interview_id)
    return result


@router.post("/interviews/{interview_id}/questions/{interview_question_id}/answer")
async def submit_answer(
        interview_id: int,
        interview_question_id: int,
        answer: schemas.AnswerRequest,
        db: Session = Depends(get_db)
):
    """🎯 PHASE 3: Store answer + prepare next"""
    orchestrator = InterviewOrchestrator(db)
    result = orchestrator.submit_answer(interview_question_id, answer.answer_text)
    return result

@router.get("/interviews/{interview_id}/status")
async def get_interview_status(interview_id: int, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter(
        Interview.interview_id == interview_id
    ).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # ✅ count answers from UserAnswer
    answered_count = (
        db.query(func.count(UserAnswer.id))
        .filter(UserAnswer.interview_id == interview_id)
        .scalar()
        or 0
    )

    total_target = 12  # or derive from config
    return {
        "interview_id": interview_id,
        "user_id": interview.user_id,
        "progress": f"{answered_count}/{total_target}",
        "percentage": round(answered_count / total_target * 100, 1),
        "status": "complete" if answered_count >= total_target else "active",
    }