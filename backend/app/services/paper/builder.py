import random
import numpy as np
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, func

from app.models.question import Question
from app.models.paper import QuestionPaper, QuestionPaperItem, PaperStatus
from app.services.paper.schemas import PaperBlueprint

def _cosine_distance(v1: np.ndarray, v2: np.ndarray) -> float:
    dot = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 1.0
    return 1.0 - (dot / (norm1 * norm2))

def select_diverse_questions(candidates: List[Question], count: int) -> List[Question]:
    """
    Selects `count` questions from `candidates` using a greedy Max-Min diversity approach
    to ensure the paper doesn't ask the same semantic concept multiple times.
    """
    if count >= len(candidates):
        return candidates
        
    # Convert embeddings to numpy arrays
    candidate_embeddings = []
    for q in candidates:
        # pgvector returns a list of floats
        candidate_embeddings.append(np.array(q.embedding))
        
    selected_indices = []
    
    # 1. Pick the first question randomly to ensure papers aren't identical every time
    first_idx = random.randint(0, len(candidates) - 1)
    selected_indices.append(first_idx)
    
    # 2. Iteratively pick the question that maximizes the minimum distance to already selected questions
    for _ in range(1, count):
        max_min_dist = -1.0
        best_idx = -1
        
        for i, emb in enumerate(candidate_embeddings):
            if i in selected_indices:
                continue
                
            # Find the minimum distance from this candidate to any already selected question
            min_dist_to_selected = min([_cosine_distance(emb, candidate_embeddings[sel_idx]) for sel_idx in selected_indices])
            
            # We want to maximize this minimum distance
            if min_dist_to_selected > max_min_dist:
                max_min_dist = min_dist_to_selected
                best_idx = i
                
        selected_indices.append(best_idx)
        
    return [candidates[i] for i in selected_indices]

def select_single_replacement(candidates: List[Question], existing_embeddings: List[np.ndarray]) -> Optional[Question]:
    """
    Selects a single question from candidates that maximizes the minimum distance to existing embeddings.
    """
    if not candidates:
        return None
        
    if not existing_embeddings:
        return random.choice(candidates)
        
    max_min_dist = -1.0
    best_candidate = None
    
    for q in candidates:
        emb = np.array(q.embedding)
        min_dist = min([_cosine_distance(emb, ex_emb) for ex_emb in existing_embeddings])
        if min_dist > max_min_dist:
            max_min_dist = min_dist
            best_candidate = q
            
    return best_candidate

async def build_question_paper(db: AsyncSession, blueprint: PaperBlueprint) -> QuestionPaper:
    """
    Builds a draft question paper based on the blueprint.
    Raises ValueError if there are insufficient questions to fulfill the blueprint.
    """
    
    # 1. Pre-flight validation: check availability for all sections
    section_candidates = {}
    
    for section in blueprint.sections:
        filters = [
            Question.exam_id == blueprint.exam_id,
            func.lower(Question.question_type) == section.question_type.lower(),
            func.lower(Question.difficulty) == section.difficulty.lower()
        ]
        if blueprint.subject_id:
            filters.append(Question.subject_id == blueprint.subject_id)
            
        query = select(Question).where(and_(*filters))
        result = await db.execute(query)
        candidates = result.scalars().all()
        
        if len(candidates) < section.count:
            raise ValueError(
                f"Insufficient questions for {section.name}. "
                f"Requested {section.count} {section.difficulty} {section.question_type}s, "
                f"but only {len(candidates)} approved questions are available."
            )
            
        section_candidates[section.name] = candidates

    # 2. Transactional Paper Creation
    try:
        paper = QuestionPaper(
            exam_id=blueprint.exam_id,
            subject_id=blueprint.subject_id,
            title=blueprint.title,
            status=PaperStatus.DRAFT,
            config=blueprint.model_dump(mode='json')
        )
        db.add(paper)
        
        # Flush to get paper.id
        await db.flush()
        
        # 3. Select diverse questions and create items
        order_index = 0
        
        # We also need to track globally selected questions across sections 
        # to prevent using the exact same question in two different sections if criteria overlap.
        used_question_ids = set()
        
        for section in blueprint.sections:
            candidates = section_candidates[section.name]
            
            # Filter out already used questions
            available_candidates = [c for c in candidates if c.id not in used_question_ids]
            
            if len(available_candidates) < section.count:
                 raise ValueError(
                    f"Insufficient unique questions for {section.name} after fulfilling previous sections. "
                    f"Needed {section.count}, got {len(available_candidates)}."
                 )
                 
            # Select diverse questions
            selected = select_diverse_questions(available_candidates, section.count)
            
            for q in selected:
                used_question_ids.add(q.id)
                
                item = QuestionPaperItem(
                    paper_id=paper.id,
                    question_id=q.id,
                    question_text_snapshot=q.question_text,
                    content_snapshot=q.content,
                    marks_snapshot=q.marks,
                    section_name=section.name,
                    order_index=order_index,
                    marks_override=section.marks_per_question if section.marks_per_question != q.marks else None
                )
                db.add(item)
                order_index += 1
                
        await db.commit()
        await db.refresh(paper)
        return paper
        
    except Exception as e:
        await db.rollback()
        raise e
