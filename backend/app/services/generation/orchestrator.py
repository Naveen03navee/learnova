import asyncio
from typing import Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import math
import numpy as np

from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.core.logging import get_logger
from app.core.request_context import set_session_id, set_batch_id
from app.models.generation import GenerationSession, GenerationStatus, GeneratedQuestion, ApprovalStatus
from app.models.workspace import Exam, Subject
from app.schemas.rag import RetrievalRequest
from app.schemas.generation import GenerationEvent, EventType
from app.services.rag.retriever import retrieve_chunks
from app.services.ai.context import build_bounded_context
from app.services.ai.manager import ai_manager
from app.services.ai.router import get_primary_provider_name
from app.services.ai.schemas import GenerationRequest
from app.services.generation.prompts import GENERATION_SYSTEM_PROMPT, build_generation_user_prompt
from app.services.generation.validators import GeneratedQuestionListSchema, validate_question_logic
from app.services.generation.deduplicator import check_duplicate, generate_question_embedding
from app.services.generation.events import event_bus

logger = get_logger(__name__)

class GenerationCancelledError(Exception):
    pass

_cancelled_sessions: set[UUID] = set()

def cancel_generation_session(session_id: UUID) -> None:
    _cancelled_sessions.add(session_id)

def is_generation_cancelled(session_id: UUID) -> bool:
    return session_id in _cancelled_sessions

def clear_generation_cancellation(session_id: UUID) -> None:
    _cancelled_sessions.discard(session_id)

async def _publish_event(session_id: UUID, status: GenerationStatus, message: str, progress: float, batch: int = None, total_batches: int = None, event_type: EventType = EventType.INFO):
    await event_bus.publish(GenerationEvent(
        session_id=session_id,
        status=status.value if isinstance(status, GenerationStatus) else status,
        message=message,
        progress=progress,
        batch=batch,
        total_batches=total_batches,
        event_type=event_type,
        operation="generation"
    ))

def _calculate_batches(requested: int, batch_size: int) -> List[int]:
    batches = []
    while requested > 0:
        if requested >= batch_size:
            batches.append(batch_size)
            requested -= batch_size
        else:
            batches.append(requested)
            requested = 0
    return batches

async def process_generation_session(session_id: UUID):
    """
    Background task to process a generation session using batched strategy.
    """
    set_session_id(str(session_id))
    
    async def _check_cancelled(session: GenerationSession):
        if is_generation_cancelled(session_id):
            raise GenerationCancelledError("Generation cancelled by you.")
    
    try:
        async with AsyncSessionLocal() as db:
            # Load the session with exam and subject
            result = await db.execute(
                select(GenerationSession, Exam.name, Subject.name)
                .join(Exam, GenerationSession.exam_id == Exam.id)
                .join(Subject, GenerationSession.subject_id == Subject.id)
                .where(GenerationSession.id == session_id)
            )
            row = result.first()
            if not row:
                logger.error(f"GenerationSession {session_id} not found.")
                return
                
            session, exam_name, subject_name = row

            try:
                await _check_cancelled(session)
                
                # 0. INITIALIZING Phase
                await _publish_event(session_id, GenerationStatus.PENDING, "Generation started", 0.01, event_type=EventType.GENERATION_STARTED)
                await _publish_event(session_id, GenerationStatus.PENDING, "Initializing generation session...", 0.02, event_type=EventType.INITIALIZING)

                await _check_cancelled(session)
                # Load embedder in background to not block SSE
                await _publish_event(session_id, GenerationStatus.PENDING, "Loading embedding model...", 0.03, event_type=EventType.LOADING_EMBEDDING_MODEL)
                from app.services.document_processor.embedder import embedder
                await asyncio.to_thread(embedder._load_model)
                device_status = embedder.get_device_status()
                await _publish_event(session_id, GenerationStatus.PENDING, f"Embedding model ready (Engine: {device_status})", 0.04, event_type=EventType.EMBEDDING_MODEL_READY)

                await _check_cancelled(session)
                # 1. RETRIEVING Phase
                session.status = GenerationStatus.RETRIEVING
                session.batch_size = settings.GENERATION_BATCH_SIZE
                await db.commit()
                await _publish_event(session_id, session.status, "Retrieving relevant knowledge...", 0.05, event_type=EventType.RETRIEVING_KNOWLEDGE)

                retrieval_request = RetrievalRequest(
                    query=session.topic if session.topic.strip() else f"Comprehensive {subject_name}",
                    exam_id=session.exam_id,
                    subject_id=session.subject_id,
                    folder_id=session.folder_id,
                    top_k=settings.RAG_MAX_RETRIEVAL_CHUNKS
                )
                
                try:
                    retrieval_response = await retrieve_chunks(db, retrieval_request)
                    chunks = retrieval_response.results
                except ValueError as e:
                    raise Exception(f"Knowledge Retrieval Failed: {e}")

                if not chunks:
                    raise Exception("No knowledge found for the requested topic. Cannot generate questions without source material.")
                
                await _publish_event(session_id, session.status, f"Retrieved {len(chunks)} relevant chunks", 0.07, event_type=EventType.KNOWLEDGE_RETRIEVED)

                await _check_cancelled(session)
                # 2. BOUNDED CONTEXT
                await _publish_event(session_id, session.status, "Building generation context...", 0.08, event_type=EventType.BUILDING_CONTEXT)
                bounded_context, provenance_map = build_bounded_context(chunks)
                if not bounded_context:
                    raise Exception("Failed to build a valid context from retrieved knowledge.")
                
                await _publish_event(session_id, session.status, "Knowledge context ready", 0.09, event_type=EventType.INFO)

                await _check_cancelled(session)
                # Load pattern if present
                pattern_data_str = None
                pattern_examples_str = None
                if session.pattern_id:
                    from app.models.pattern import ExamPattern
                    from app.services.rag.pattern_retriever import PatternRetriever
                    
                    # Retrieve Blueprint
                    pattern_result = await db.execute(select(ExamPattern).where(ExamPattern.id == session.pattern_id))
                    pattern = pattern_result.scalar_one_or_none()
                    if pattern and pattern.analysis_data:
                        import json
                        pattern_data_str = json.dumps(pattern.analysis_data, indent=2)
                    
                    # Retrieve Pattern Examples
                    pattern_chunks = await PatternRetriever.retrieve(
                        db, 
                        pattern_id=session.pattern_id, 
                        query=session.topic if session.topic.strip() else f"Comprehensive {subject_name}", 
                        top_k=5
                    )
                    if pattern_chunks:
                        # Format examples to pass to prompt
                        pattern_examples_str = "\n\n".join(
                            f"Example Question:\n{c.content}\n"
                            f"Metadata: Type={c.question_type}, Section={c.section}, Difficulty={c.difficulty}, Marks={c.marks}"
                            for c in pattern_chunks
                        )

                primary_provider = get_primary_provider_name(session.difficulty)
                session.provider_used = primary_provider
                
                # Batch Planning
                batch_plan = _calculate_batches(session.requested_count, settings.GENERATION_BATCH_SIZE)
                session.total_batches = len(batch_plan)
                await db.commit()

                await _publish_event(session_id, GenerationStatus.GENERATING, f"Knowledge retrieved. Generating {session.requested_count} questions in {session.total_batches} batches...", 0.1)
                
                accepted_questions_texts = []
                accepted_embeddings = [] # Track embedded questions inside the batching session
                
                total_llm_calls = 0
                
                async def _run_batch(batch_idx, batch_count, is_supplementary=False):
                    nonlocal total_llm_calls
                    await _check_cancelled(session)
                    if total_llm_calls >= settings.GENERATION_MAX_TOTAL_LLM_CALLS:
                        logger.warning("Global LLM call limit reached.")
                        return False
                        
                    session.current_batch = batch_idx
                    session.status = GenerationStatus.GENERATING
                    await db.commit()
                    
                    batch_label = f"Supplementary Batch {batch_idx}" if is_supplementary else f"Batch {batch_idx}/{session.total_batches}"
                    set_batch_id(str(batch_idx))
                    logger.info("generation_batch_started", batch_label=batch_label, batch_count=batch_count, current_attempt=1)
                    await _publish_event(session_id, session.status, f"Generating {batch_count} questions for {batch_label}...", 
                                         0.1 + (0.8 * (min(batch_idx, session.total_batches) / max(session.total_batches, 1))),
                                         batch=batch_idx, total_batches=session.total_batches, event_type=EventType.GENERATING_BATCH)
                    
                    # We will attempt up to GENERATION_MAX_REPAIR_ATTEMPTS for the deficit in this batch
                    target_for_batch = batch_count
                    valid_in_this_batch = 0
                    
                    current_attempt = 0
                    max_attempts = settings.GENERATION_MAX_REPAIR_ATTEMPTS + 1
                    
                    while current_attempt < max_attempts and valid_in_this_batch < target_for_batch and total_llm_calls < settings.GENERATION_MAX_TOTAL_LLM_CALLS:
                        await _check_cancelled(session)
                        current_attempt += 1
                        total_llm_calls += 1
                        session.llm_call_count = total_llm_calls
                        await db.commit()
                        
                        repair_count = target_for_batch - valid_in_this_batch
                        if current_attempt > 1:
                            await _publish_event(session_id, session.status, f"Repairing {repair_count} invalid questions (Attempt {current_attempt}/{max_attempts})...", 
                                                 0.1 + (0.8 * (min(batch_idx, session.total_batches) / max(session.total_batches, 1))),
                                                 batch=batch_idx, total_batches=session.total_batches, event_type=EventType.REPAIRING)
                        
                        try:
                            user_prompt = build_generation_user_prompt(
                                context=bounded_context,
                                topic=session.topic if session.topic.strip() else "Comprehensive Coverage",
                                question_type=session.question_type,
                                difficulty=session.difficulty,
                                marks=session.marks,
                                count=repair_count,
                                exam_name=exam_name,
                                subject_name=subject_name,
                                exam_pattern=pattern_data_str,
                                pattern_examples_str=pattern_examples_str,
                                previous_questions=accepted_questions_texts[-10:] # send last 10 to avoid bloat
                            )
                            
                            gen_request = GenerationRequest(
                                system_prompt=GENERATION_SYSTEM_PROMPT,
                                user_prompt=user_prompt,
                                response_schema=GeneratedQuestionListSchema,
                                temperature=0.7 + (0.1 * current_attempt) 
                            )
                            
                            async def _on_ai_event(event: GenerationEvent):
                                event.progress = 0.1 + (0.8 * (min(batch_idx, session.total_batches) / max(session.total_batches, 1)))
                                event.batch = batch_idx
                                event.total_batches = session.total_batches
                                await event_bus.publish(event)
                            
                            def _provider_check_cancelled():
                                return is_generation_cancelled(session_id)

                            ai_response = await ai_manager.generate(
                                primary_provider, 
                                gen_request,
                                session_id=session_id,
                                on_event=_on_ai_event,
                                check_cancelled=_provider_check_cancelled
                            )
                            parsed_data: GeneratedQuestionListSchema = ai_response.parsed_output
                            session.provider_used = ai_response.provider_name
                            
                            await _check_cancelled(session)
                            session.status = GenerationStatus.VALIDATING
                            await db.commit()
                            await _publish_event(session_id, session.status, "Validating and deduplicating generated questions...", 0.85, batch=batch_idx, total_batches=session.total_batches, event_type=EventType.VALIDATING)
                            
                            # Post-generation pattern constraint validation
                            if len(parsed_data.questions) != repair_count:
                                raise ValueError(f"Pattern Constraint Failed: Requested {repair_count} questions, but LLM generated {len(parsed_data.questions)}.")
                            
                            for q_data in parsed_data.questions:
                                await _check_cancelled(session)
                                if valid_in_this_batch >= target_for_batch:
                                    break # Safety if LLM over-generated
                                    
                                logical_error = validate_question_logic(q_data, session.question_type)
                                if logical_error:
                                    session.invalid_count += 1
                                    logger.warning("question_invalid_logic", reason=logical_error, question_text=q_data.question_text[:50])
                                    continue
                                    
                                session.status = GenerationStatus.DEDUPLICATING
                                await db.commit()
                                await _publish_event(session_id, session.status, "Checking for duplicate questions...", 0.9, batch=batch_idx, total_batches=session.total_batches, event_type=EventType.DEDUPLICATING)
                                
                                is_duplicate = await check_duplicate(
                                    db, 
                                    question_text=q_data.question_text,
                                    exam_id=session.exam_id,
                                    subject_id=session.subject_id
                                )
                                
                                # Also check explicitly against in-memory accepted embeddings from THIS session
                                new_emb = None
                                if not is_duplicate and accepted_embeddings:
                                    new_emb = await generate_question_embedding(q_data.question_text)
                                    new_np = np.array(new_emb)
                                    for acc_emb in accepted_embeddings:
                                        dot = np.dot(new_np, acc_emb)
                                        n1 = np.linalg.norm(new_np)
                                        n2 = np.linalg.norm(acc_emb)
                                        if n1 > 0 and n2 > 0:
                                            sim = dot / (n1 * n2)
                                            if sim >= settings.GENERATION_DUPLICATE_THRESHOLD:
                                                is_duplicate = True
                                                break
                                elif not is_duplicate:
                                    new_emb = await generate_question_embedding(q_data.question_text)
                                
                                if is_duplicate:
                                    session.duplicate_count += 1
                                    logger.info("question_duplicate", question_text=q_data.question_text[:50])
                                    continue
                                    
                                session.status = GenerationStatus.SAVING
                                
                                # Save
                                r_ids = set()
                                c_ids = set()
                                for citation in q_data.source_citations:
                                    mapped = provenance_map.get(citation)
                                    if mapped:
                                        r_ids.add(mapped["resource_id"])
                                        c_ids.add(mapped["chunk_id"])
                                
                                q = GeneratedQuestion(
                                    session_id=session.id,
                                    content=q_data.model_dump(),
                                    question_text=q_data.question_text,
                                    embedding=new_emb,
                                    source_resource_ids=list(r_ids) if r_ids else None,
                                    source_chunk_ids=list(c_ids) if c_ids else None,
                                    is_valid=True,
                                    approval_status=ApprovalStatus.PENDING
                                )
                                db.add(q)
                                
                                session.valid_count += 1
                                valid_in_this_batch += 1
                                accepted_questions_texts.append(q_data.question_text)
                                logger.info("question_validated_and_saved", question_text=q_data.question_text[:50])
                                accepted_embeddings.append(np.array(new_emb))
                                await db.commit()
                                
                        except RuntimeError as re:
                            if str(re) == "GENERATION_CANCELLED":
                                raise GenerationCancelledError("Generation cancelled by you.")
                            logger.warning(f"Generation attempt {current_attempt} failed: {re}")
                            await db.rollback()
                        except GenerationCancelledError:
                            raise
                        except Exception as e:
                            logger.warning(f"Generation attempt {current_attempt} failed: {e}")
                            await db.rollback()
                            # Will loop and retry if max_attempts not reached
                            
                    if current_attempt > 1:
                        session.repair_count += (current_attempt - 1)
                        await db.commit()
                    
                    await _check_cancelled(session)
                    await _publish_event(session_id, session.status, f"{batch_label} completed — {valid_in_this_batch} questions", 1.0, batch=batch_idx, total_batches=session.total_batches, event_type=EventType.BATCH_COMPLETED)
                        
                    return True # Finished batch attempts
                    
                # Initial Batches
                for i, batch_count in enumerate(batch_plan):
                    if total_llm_calls >= settings.GENERATION_MAX_TOTAL_LLM_CALLS:
                        break
                    await _run_batch(i + 1, batch_count, is_supplementary=False)
                    
                # Supplementary Batches if target not reached
                supp_batch_idx = 1
                while session.valid_count < session.requested_count and supp_batch_idx <= settings.GENERATION_MAX_SUPPLEMENTARY_BATCHES:
                    await _check_cancelled(session)
                    if total_llm_calls >= settings.GENERATION_MAX_TOTAL_LLM_CALLS:
                        break
                        
                    deficit = session.requested_count - session.valid_count
                    batch_count = min(deficit, settings.GENERATION_BATCH_SIZE)
                    
                    await _run_batch(session.total_batches + supp_batch_idx, batch_count, is_supplementary=True)
                    supp_batch_idx += 1
                    
                # Finished
                if session.valid_count >= session.requested_count:
                    session.status = GenerationStatus.COMPLETED
                elif session.valid_count > 0:
                    session.status = GenerationStatus.PARTIAL
                else:
                    session.status = GenerationStatus.FAILED
                    
                await db.commit()
                
                # Milestone 3: Track AI usage telemetry per session
                logger.info(
                    "generation_session_completed",
                    session_id=str(session_id),
                    exam_id=str(session.exam_id),
                    subject_id=str(session.subject_id),
                    provider_used=session.provider_used,
                    requested_count=session.requested_count,
                    valid_count=session.valid_count,
                    duplicate_count=session.duplicate_count,
                    invalid_count=session.invalid_count,
                    total_batches=session.total_batches,
                    supplementary_batches=supp_batch_idx - 1 if 'supp_batch_idx' in locals() else 0,
                    total_llm_calls=total_llm_calls,
                    repair_count=session.repair_count,
                    final_status=session.status.value
                )
                
                if session.status == GenerationStatus.FAILED:
                    await _publish_event(session_id, session.status, f"Generation failed to produce valid questions.", 1.0, batch=session.current_batch, total_batches=session.total_batches, event_type=EventType.GENERATION_FAILED)
                else:
                    await _publish_event(session_id, session.status, f"Generation finished. {session.valid_count} valid, {session.duplicate_count} duplicates, {session.invalid_count} invalid.", 1.0, batch=session.current_batch, total_batches=session.total_batches, event_type=EventType.GENERATION_COMPLETED)

            except GenerationCancelledError as ce:
                logger.info(f"Generation session {session_id} cancelled: {ce}")
                if session.valid_count > 0:
                    session.status = GenerationStatus.PARTIAL
                else:
                    session.status = GenerationStatus.FAILED
                await db.commit()
                # Publish CANCELLED before the stream closes naturally
                await _publish_event(
                    session_id, 
                    session.status, 
                    f"Generation was cancelled by you. {session.valid_count} questions were preserved.", 
                    1.0, 
                    event_type=EventType.CANCELLED
                )
            except Exception as e:
                logger.exception(f"Fatal error in generation session {session_id}")
                await db.rollback()
                try:
                    from sqlalchemy import update
                    await db.execute(
                        update(GenerationSession)
                        .where(GenerationSession.id == session_id)
                        .values(
                            status=GenerationStatus.FAILED,
                            invalid_count=GenerationSession.requested_count - GenerationSession.valid_count - GenerationSession.duplicate_count
                        )
                    )
                    await db.commit()
                except Exception as inner_e:
                    logger.error(f"Failed to update session status to FAILED: {inner_e}")
                await _publish_event(session_id, GenerationStatus.FAILED, f"Generation failed: {str(e)}", 1.0, event_type=EventType.GENERATION_FAILED)

    finally:
        clear_generation_cancellation(session_id)
