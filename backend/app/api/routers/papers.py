from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import or_, and_
from uuid import UUID
from typing import List, Optional
import re
import uuid

from app.core.database import get_db
from app.models.paper import QuestionPaper, QuestionPaperItem, PaperStatus
from app.models.question import Question
from app.models.workspace import Exam, Subject
from app.models.sharing import SharePermission
from app.schemas.paper import QuestionPaperSchema, ReorderItemRequest, SwapItemRequest, ApprovePaperRequest
from app.services.paper.schemas import PaperBlueprint
from app.services.paper.builder import build_question_paper
from app.services.export.docx_exporter import export_question_paper_docx
from app.services.export.question_paper_exporter_pdf import export_question_paper_pdf
from app.services.export.answer_key_exporter import export_answer_key_pdf
from app.api.deps import get_current_user
from app.core.authorization import require_view_access, require_edit_access, require_owner_access, get_entity_access
import io
import zipfile

router = APIRouter(prefix="/api/v1", tags=["papers"])

@router.post("/papers/build", response_model=QuestionPaperSchema)
async def build_paper(
    blueprint: PaperBlueprint, 
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    user_uuid = uuid.UUID(user_id)
    exam = await db.get(Exam, blueprint.exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if blueprint.subject_id:
        await require_edit_access(db, "subject", blueprint.subject_id, user_uuid)
    else:
        await require_edit_access(db, "exam", blueprint.exam_id, user_uuid)
        
    try:
        paper = await build_question_paper(db, blueprint)
        
        result = await db.execute(
            select(QuestionPaper)
            .options(selectinload(QuestionPaper.items))
            .where(QuestionPaper.id == paper.id)
        )
        loaded_paper = result.scalar_one()

        from app.core.logging import get_logger
        from app.core.request_context import set_paper_id
        set_paper_id(str(loaded_paper.id))
        logger = get_logger(__name__)
        logger.info("paper_created", exam_id=str(blueprint.exam_id), subject_id=str(blueprint.subject_id), items_count=len(loaded_paper.items) if loaded_paper.items else 0)
        
        return loaded_paper
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/papers", response_model=List[QuestionPaperSchema])
async def list_papers(
    exam_id: Optional[UUID] = None,
    subject_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    user_uuid = uuid.UUID(user_id)
    
    query = select(QuestionPaper).options(selectinload(QuestionPaper.items)).join(Exam, QuestionPaper.exam_id == Exam.id).join(Subject, QuestionPaper.subject_id == Subject.id).outerjoin(
        SharePermission, and_(
            SharePermission.entity_id == QuestionPaper.id,
            SharePermission.entity_type == "paper",
            SharePermission.shared_with_id == user_uuid
        )
    ).where(
        or_(
            Subject.created_by == user_uuid,
            SharePermission.id != None
        )
    ).order_by(QuestionPaper.created_at.desc())
    
    if exam_id:
        query = query.where(QuestionPaper.exam_id == exam_id)
    if subject_id:
        query = query.where(QuestionPaper.subject_id == subject_id)
    if status:
        query = query.where(QuestionPaper.status == status)
        
    result = await db.execute(query)
    papers = result.scalars().all()
    
    response = []
    for paper in papers:
        access = await get_entity_access(db, "paper", paper.id, user_uuid)
        p_dict = paper.__dict__.copy()
        p_dict['access'] = access
        response.append(p_dict)
        
    return response

@router.get("/papers/{paper_id}", response_model=QuestionPaperSchema)
async def get_paper(
    paper_id: UUID, 
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await require_view_access(db, "paper", paper_id, uuid.UUID(user_id))
    
    result = await db.execute(
        select(QuestionPaper)
        .options(selectinload(QuestionPaper.items))
        .where(QuestionPaper.id == paper_id)
    )
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
        
    access = await get_entity_access(db, "paper", paper_id, uuid.UUID(user_id))
    p_dict = paper.__dict__.copy()
    p_dict['access'] = access
    return p_dict

@router.put("/papers/{paper_id}/items/reorder", response_model=QuestionPaperSchema)
async def reorder_items(
    paper_id: UUID, 
    req: List[ReorderItemRequest], 
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await require_edit_access(db, "paper", paper_id, uuid.UUID(user_id))
    
    result = await db.execute(
        select(QuestionPaper)
        .options(selectinload(QuestionPaper.items))
        .where(QuestionPaper.id == paper_id)
    )
    paper = result.scalar_one_or_none()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    if paper.status != PaperStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only DRAFT papers can be modified")
        
    item_map = {item.id: item for item in paper.items}
    
    for r in req:
        if r.item_id in item_map:
            item_map[r.item_id].order_index = r.new_index
            
    paper.quality_report_stale = True
    await db.commit()
    
    result = await db.execute(
        select(QuestionPaper)
        .options(selectinload(QuestionPaper.items))
        .where(QuestionPaper.id == paper_id)
    )
    return result.scalar_one()

@router.put("/papers/{paper_id}/items/{item_id}/swap", response_model=QuestionPaperSchema)
async def swap_item(
    paper_id: UUID, 
    item_id: UUID, 
    req: SwapItemRequest, 
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await require_edit_access(db, "paper", paper_id, uuid.UUID(user_id))
    
    result = await db.execute(select(QuestionPaper).where(QuestionPaper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper or paper.status != PaperStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Paper not found or not in DRAFT status")
        
    result = await db.execute(select(QuestionPaperItem).where(QuestionPaperItem.id == item_id, QuestionPaperItem.paper_id == paper_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    result = await db.execute(select(Question).where(Question.id == req.new_question_id))
    new_q = result.scalar_one_or_none()
    if not new_q:
        raise HTTPException(status_code=404, detail="New question not found")
        
    item.question_id = new_q.id
    item.question_text_snapshot = new_q.question_text
    item.content_snapshot = new_q.content
    item.marks_snapshot = new_q.marks
    
    paper.quality_report_stale = True
    await db.commit()
    
    result = await db.execute(
        select(QuestionPaper)
        .options(selectinload(QuestionPaper.items))
        .where(QuestionPaper.id == paper_id)
    )
    return result.scalar_one()

@router.post("/papers/{paper_id}/items/{item_id}/auto-replace", response_model=QuestionPaperSchema)
async def auto_replace_item(
    paper_id: UUID, 
    item_id: UUID, 
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await require_edit_access(db, "paper", paper_id, uuid.UUID(user_id))
    
    from app.services.paper.builder import select_single_replacement
    import numpy as np
    
    result = await db.execute(
        select(QuestionPaper)
        .options(selectinload(QuestionPaper.items))
        .where(QuestionPaper.id == paper_id)
    )
    paper = result.scalar_one_or_none()
    if not paper or paper.status != PaperStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Paper not found or not in DRAFT status")
        
    target_item = None
    for item in paper.items:
        if item.id == item_id:
            target_item = item
            break
            
    if not target_item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    section_config = None
    for sec in paper.config.get("sections", []):
        if sec["name"] == target_item.section_name:
            section_config = sec
            break
            
    if not section_config:
        raise HTTPException(status_code=400, detail="Section configuration not found in blueprint")
        
    existing_question_ids = [i.question_id for i in paper.items if i.question_id is not None]
    
    filters = [
        Question.exam_id == paper.exam_id,
        Question.question_type == section_config["question_type"],
        Question.difficulty == section_config["difficulty"]
    ]
    if existing_question_ids:
        filters.append(Question.id.notin_(existing_question_ids))
    if paper.subject_id:
        filters.append(Question.subject_id == paper.subject_id)
        
    query = select(Question).where(and_(*filters))
    res = await db.execute(query)
    candidates = res.scalars().all()
    
    if not candidates:
        raise HTTPException(status_code=404, detail="No suitable replacement questions available in the bank.")
        
    existing_embeddings = []
    if existing_question_ids:
        eq_res = await db.execute(select(Question).where(Question.id.in_(existing_question_ids)))
        eqs = eq_res.scalars().all()
        for eq in eqs:
            if eq.embedding is not None:
                existing_embeddings.append(np.array(eq.embedding))
                
    best_candidate = select_single_replacement(candidates, existing_embeddings)
    
    if not best_candidate:
        raise HTTPException(status_code=404, detail="Could not select a replacement.")
        
    target_item.question_id = best_candidate.id
    target_item.question_text_snapshot = best_candidate.question_text
    target_item.content_snapshot = best_candidate.content
    target_item.marks_snapshot = best_candidate.marks
    
    paper.quality_report_stale = True
    await db.commit()
    
    result = await db.execute(
        select(QuestionPaper)
        .options(selectinload(QuestionPaper.items))
        .where(QuestionPaper.id == paper_id)
    )
    return result.scalar_one()

@router.post("/papers/{paper_id}/approve", response_model=QuestionPaperSchema)
async def approve_paper(
    paper_id: UUID, 
    req: ApprovePaperRequest, 
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await require_edit_access(db, "paper", paper_id, uuid.UUID(user_id))
    
    result = await db.execute(
        select(QuestionPaper)
        .options(selectinload(QuestionPaper.items))
        .where(QuestionPaper.id == paper_id)
    )
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
        
    if paper.status != PaperStatus.DRAFT:
        raise HTTPException(status_code=400, detail=f"Paper is already {paper.status}")
        
    from app.services.paper.validator import validate_structural_integrity
    structural_errors = validate_structural_integrity(paper)
    if structural_errors:
        raise HTTPException(status_code=400, detail={"message": "Structural validation failed", "errors": structural_errors})
        
    if paper.quality_report_stale:
        raise HTTPException(status_code=400, detail="AI Quality Check is stale. Please re-run the check before approving.")
        
    if paper.quality_status in ["WARNING", "FAIL"] and not req.override_ai_check:
        raise HTTPException(status_code=400, detail=f"AI Quality Check returned {paper.quality_status}. Explicit override required.")
        
    paper.status = PaperStatus.APPROVED
    await db.commit()
    
    from app.core.logging import get_logger
    from app.core.request_context import set_paper_id
    set_paper_id(str(paper_id))
    logger = get_logger(__name__)
    logger.info("paper_approved", quality_status=paper.quality_status, overriden=req.override_ai_check)
    
    result = await db.execute(
        select(QuestionPaper)
        .options(selectinload(QuestionPaper.items))
        .where(QuestionPaper.id == paper_id)
    )
    return result.scalar_one()

@router.post("/papers/{paper_id}/quality-check", response_model=QuestionPaperSchema)
async def quality_check_paper(
    paper_id: UUID, 
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await require_edit_access(db, "paper", paper_id, uuid.UUID(user_id))
    
    from app.services.paper.quality_checker import run_paper_quality_check
    from app.core.logging import get_logger
    from app.core.request_context import set_paper_id
    set_paper_id(str(paper_id))
    logger = get_logger(__name__)
    
    try:
        paper = await run_paper_quality_check(db, paper_id)
        logger.info("paper_quality_checked", quality_status=paper.quality_status)
        
        result = await db.execute(
            select(QuestionPaper)
            .options(selectinload(QuestionPaper.items))
            .where(QuestionPaper.id == paper_id)
        )
        return result.scalar_one()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")

def _get_export_filenames(paper) -> tuple[str, str, str]:
    exam_name = _sanitize_filename(paper.exam.name) if paper.exam else "Exam"
    subject_name = _sanitize_filename(paper.subject.name) if paper.subject else "Subject"
    date_str = paper.created_at.strftime("%d-%m")
    
    base_name = f"{exam_name}-{subject_name}-{date_str}"
    
    return (
        f"{base_name}.docx",
        f"{base_name}-key answer.docx",
        f"{base_name}-Package.zip"
    )


@router.get("/papers/{paper_id}/export/question_paper/pdf")
async def export_paper_question_paper_pdf(
    paper_id: UUID, 
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    paper = await _get_paper_for_export(db, paper_id, user_id)
    if paper.status != PaperStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Only APPROVED papers can be exported.")
        
    try:
        buffer = export_question_paper_pdf(paper)
        paper_filename, _, _ = _get_export_filenames(paper)
        
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{paper_filename}.pdf"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/papers/{paper_id}/export/docx")
async def export_paper_docx(
    paper_id: UUID, 
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await require_view_access(db, "paper", paper_id, uuid.UUID(user_id))
    
    result = await db.execute(
        select(QuestionPaper)
        .options(selectinload(QuestionPaper.items), selectinload(QuestionPaper.exam), selectinload(QuestionPaper.subject))
        .where(QuestionPaper.id == paper_id)
    )
    paper = result.scalar_one_or_none()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
        
    if paper.status != PaperStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Only APPROVED papers can be exported.")
        
    try:
        buffer = export_question_paper_docx(paper)
        paper_filename, _, _ = _get_export_filenames(paper)
        filename = paper_filename
        
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/papers/{paper_id}/export/answer_key/pdf")
async def export_paper_answer_key_pdf(
    paper_id: UUID, 
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await require_view_access(db, "paper", paper_id, uuid.UUID(user_id))
    
    result = await db.execute(
        select(QuestionPaper)
        .options(selectinload(QuestionPaper.items), selectinload(QuestionPaper.exam), selectinload(QuestionPaper.subject))
        .where(QuestionPaper.id == paper_id)
    )
    paper = result.scalar_one_or_none()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
        
    if paper.status != PaperStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Only APPROVED papers can be exported.")
        
    try:
        buffer = export_answer_key_pdf(paper)
        _, key_filename, _ = _get_export_filenames(paper)
        
        if key_filename.endswith('.docx'):
            key_filename = key_filename.replace('.docx', '.pdf')
            
        filename = key_filename
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/papers/{paper_id}/export/package/zip")
async def export_paper_package_zip(
    paper_id: UUID, 
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    await require_view_access(db, "paper", paper_id, uuid.UUID(user_id))
    
    result = await db.execute(
        select(QuestionPaper)
        .options(selectinload(QuestionPaper.items), selectinload(QuestionPaper.exam), selectinload(QuestionPaper.subject))
        .where(QuestionPaper.id == paper_id)
    )
    paper = result.scalar_one_or_none()
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
        
    if paper.status != PaperStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Only APPROVED papers can be exported.")
        
    try:
        paper_buffer = export_question_paper_docx(paper)
        answer_key_buffer = export_answer_key_pdf(paper)
        
        paper_filename, key_filename, zip_filename = _get_export_filenames(paper)
        if key_filename.endswith('.docx'):
            key_filename = key_filename.replace('.docx', '.pdf')
            
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(paper_filename, paper_buffer.getvalue())
            zip_file.writestr(key_filename, answer_key_buffer.getvalue())
            
        zip_buffer.seek(0)
        filename = zip_filename
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/papers/{paper_id}/quality-check/stream")
async def stream_quality_check_progress(
    paper_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await require_view_access(db, "paper", paper_id, uuid.UUID(user_id))
    from app.services.generation.events import event_stream
    return StreamingResponse(
        event_stream(paper_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
