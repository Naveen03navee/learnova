from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from typing import Optional
from uuid import UUID

from app.models.generation import GenerationSession, GeneratedQuestion, ApprovalStatus
from app.models.question import Question
from app.models.paper import QuestionPaper, PaperStatus
from app.models.workspace import Exam
from app.api.deps import get_current_user

router = APIRouter(prefix="/api/v1", tags=["metrics"])

@router.get("/metrics")
async def get_metrics(
    exam_id: Optional[UUID] = None,
    subject_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Returns application-level operational metrics in a machine-readable JSON format.
    """
    import uuid
    user_uuid = uuid.UUID(user_id)
    
    if exam_id:
        exam_result = await db.execute(select(Exam).where(Exam.id == exam_id))
        exam = exam_result.scalar_one_or_none()
        if not exam or (exam.created_by is not None and exam.created_by != user_uuid):
            raise HTTPException(status_code=403, detail="Not authorized to access this exam context")

    metrics = {
        "generation": {},
        "question_bank": {},
        "papers": {}
    }

    # Generation Metrics
    gen_query = select(
        GenerationSession.status,
        func.count(GenerationSession.id),
        func.sum(GenerationSession.llm_call_count),
        func.sum(GenerationSession.duplicate_count),
        func.sum(GenerationSession.invalid_count),
        func.sum(GenerationSession.repair_count)
    )
    if exam_id:
        gen_query = gen_query.where(GenerationSession.exam_id == exam_id)
    if subject_id:
        gen_query = gen_query.where(GenerationSession.subject_id == subject_id)
        
    gen_stats = await db.execute(gen_query.group_by(GenerationSession.status))
    
    gen_total = 0
    gen_success = 0
    gen_failed = 0
    llm_calls = 0
    duplicates = 0
    invalid = 0
    repairs = 0

    for row in gen_stats:
        status, count, calls, dups, invs, reps = row
        gen_total += count
        if status.value == "COMPLETED":
            gen_success += count
        elif status.value == "FAILED":
            gen_failed += count
            
        llm_calls += (calls or 0)
        duplicates += (dups or 0)
        invalid += (invs or 0)
        repairs += (reps or 0)

    metrics["generation"] = {
        "requests_total": gen_total,
        "success_total": gen_success,
        "failed_total": gen_failed,
        "llm_calls_total": llm_calls,
        "duplicate_count_total": duplicates,
        "validation_failure_total": invalid,
        "repair_count_total": repairs
    }

    # Question Bank Metrics
    q_query = select(GeneratedQuestion.approval_status, func.count(GeneratedQuestion.id))
    if exam_id or subject_id:
        q_query = q_query.join(GenerationSession, GeneratedQuestion.session_id == GenerationSession.id)
        if exam_id:
            q_query = q_query.where(GenerationSession.exam_id == exam_id)
        if subject_id:
            q_query = q_query.where(GenerationSession.subject_id == subject_id)

    q_stats = await db.execute(q_query.group_by(GeneratedQuestion.approval_status))
    
    q_approved = 0
    q_rejected = 0
    q_pending = 0
    for status, count in q_stats:
        if status == ApprovalStatus.APPROVED:
            q_approved = count
        elif status == ApprovalStatus.REJECTED:
            q_rejected = count
        elif status == ApprovalStatus.PENDING:
            q_pending = count

    metrics["question_bank"] = {
        "generated_total": q_approved + q_rejected + q_pending,
        "approved_total": q_approved,
        "rejected_total": q_rejected,
        "pending_total": q_pending,
        "approval_rate": round(q_approved / max(1, (q_approved + q_rejected)), 2)
    }

    # Papers Metrics
    p_query = select(QuestionPaper.status, func.count(QuestionPaper.id))
    if exam_id:
        p_query = p_query.where(QuestionPaper.exam_id == exam_id)
    if subject_id:
        p_query = p_query.where(QuestionPaper.subject_id == subject_id)
        
    p_stats = await db.execute(p_query.group_by(QuestionPaper.status))
    
    p_draft = 0
    p_approved = 0
    p_published = 0
    for status, count in p_stats:
        if status == PaperStatus.DRAFT:
            p_draft = count
        elif status == PaperStatus.APPROVED:
            p_approved = count
        elif status == PaperStatus.PUBLISHED:
            p_published = count

    metrics["papers"] = {
        "created_total": p_draft + p_approved + p_published,
        "approved_total": p_approved,
        "published_total": p_published
    }

    return metrics


@router.get("/metrics/activity")
async def get_activity(
    exam_id: Optional[UUID] = None,
    subject_id: Optional[UUID] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    import uuid
    user_uuid = uuid.UUID(user_id)
    
    if exam_id:
        exam_result = await db.execute(select(Exam).where(Exam.id == exam_id))
        exam = exam_result.scalar_one_or_none()
        if not exam or (exam.created_by is not None and exam.created_by != user_uuid):
            raise HTTPException(status_code=403, detail="Not authorized to access this exam context")
            
    activities = []
    
    # 1. Fetch recent generation sessions
    gen_q = select(GenerationSession).order_by(GenerationSession.created_at.desc()).limit(limit)
    if exam_id:
        gen_q = gen_q.where(GenerationSession.exam_id == exam_id)
    if subject_id:
        gen_q = gen_q.where(GenerationSession.subject_id == subject_id)
        
    gen_res = await db.execute(gen_q)
    sessions = gen_res.scalars().all()
    
    for s in sessions:
        activities.append({
            "id": str(s.id),
            "type": "generation",
            "title": f"Generated {s.requested_count} {s.question_type} questions on {s.topic}",
            "status": s.status.value,
            "created_at": s.created_at.isoformat(),
        })
        
    # 2. Fetch recent papers
    pap_q = select(QuestionPaper).order_by(QuestionPaper.created_at.desc()).limit(limit)
    if exam_id:
        pap_q = pap_q.where(QuestionPaper.exam_id == exam_id)
    if subject_id:
        pap_q = pap_q.where(QuestionPaper.subject_id == subject_id)
        
    pap_res = await db.execute(pap_q)
    papers = pap_res.scalars().all()
    
    for p in papers:
        activities.append({
            "id": str(p.id),
            "type": "paper",
            "title": f"Created Question Paper '{p.title}'",
            "status": p.status.value,
            "created_at": p.created_at.isoformat(),
        })
        
    # Sort descending
    activities.sort(key=lambda x: x["created_at"], reverse=True)
    return activities[:limit]
