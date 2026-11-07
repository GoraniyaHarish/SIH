"""AI quiz generation, review, publishing, attempts and scoring."""
from __future__ import annotations

import datetime as dt
import random
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.provider import AiUnavailable
from app.core.db import get_db
from app.core.deps import Page, Principal, pagination, rate_limit, require_roles
from app.models.assessment import (
    AiUsageLog, CompetencyState, Quiz, QuizAnswer, QuizAttempt, QuizQuestion,
)
from app.models.base import QuestionType, QuizStatus, Role
from app.models.learning import Document, DocumentChunk
from app.schemas import (
    AttemptResultOut, AttemptSubmitRequest, QuestionUpdateRequest, QuizDetailOut,
    QuizGenerateRequest, QuizOut, QuizPublishRequest,
)
from app.services import audit
from app.services import quizgen
from app.services.documents import DocumentRejected

router = APIRouter(tags=["quiz"])

EDITOR_ROLES = (Role.ADMIN, Role.MANAGER, Role.ASSESSOR)
PLAYER_ROLES = (Role.LEARNER, Role.ADMIN, Role.MANAGER, Role.ASSESSOR)


def _quiz_out(db: Session, quiz: Quiz, user_id: uuid.UUID | None = None) -> QuizOut:
    out = QuizOut.model_validate(quiz)
    out.question_count = len([q for q in quiz.questions if q.is_active])
    if user_id:
        attempts = db.scalars(
            select(QuizAttempt).where(
                QuizAttempt.quiz_id == quiz.id,
                QuizAttempt.user_id == user_id,
                QuizAttempt.submitted_at.is_not(None),
            )
        ).all()
        out.attempt_count = len(attempts)
        out.best_score = max((a.score_percent for a in attempts), default=None)
    return out


def _detail(db: Session, quiz: Quiz, principal: Principal) -> QuizDetailOut:
    base = _quiz_out(db, quiz, principal.id)
    out = QuizDetailOut(**base.model_dump())
    out.questions = sorted(
        [q for q in quiz.questions if q.is_active], key=lambda q: q.sort_order
    )
    out.can_manage = principal.role in EDITOR_ROLES and (
        principal.role == Role.ADMIN or quiz.created_by_id == principal.id
        or principal.role in (Role.MANAGER, Role.ASSESSOR)
    )
    return out


def _load_quiz(db: Session, quiz_id: uuid.UUID) -> Quiz:
    quiz = db.get(Quiz, quiz_id)
    if quiz is None:
        raise HTTPException(404, "Quiz not found")
    return quiz


@router.post("/quizzes/generate", response_model=QuizDetailOut, status_code=201,
             dependencies=[Depends(rate_limit("quizgen", 20, 600))])
def generate_quiz(
    payload: QuizGenerateRequest, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*EDITOR_ROLES)),
) -> QuizDetailOut:
    """Generate draft questions from an authorised document, validate, then persist as DRAFT."""
    from app.api.routers.documents import load_document

    document = load_document(db, principal.user, payload.document_id)
    if document.status != "completed":
        raise HTTPException(
            409, "This document has not finished processing, so questions cannot be generated"
        )

    chunk_rows = db.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.ordinal)
    ).all()
    chunk_ids = quizgen.chunk_lookup(chunk_rows)

    try:
        accepted, mode = quizgen.generate_for_document(
            db, document, payload.question_count, payload.difficulty, payload.question_types
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except AiUnavailable as exc:
        db.add(AiUsageLog(user_id=principal.id, operation="quiz_generate",
                          model=None, outcome="error", error_class=exc.error_class))
        db.commit()
        raise HTTPException(
            503, "The AI provider is unavailable. Retry, or generate from a smaller document."
        ) from None

    if not accepted:
        raise HTTPException(
            422,
            "No question passed validation for this document. The material may be too short or "
            "not factual enough. Try a different document or fewer questions.",
        )

    quiz = Quiz(
        title=(payload.title or f"Assessment: {document.title}")[:200],
        description=f"Generated from “{document.title}” ({len(accepted)} validated questions).",
        status=QuizStatus.DRAFT.value,
        source_document_id=document.id,
        competency_ids=[str(c) for c in payload.competency_ids],
        difficulty=payload.difficulty,
        generation_mode=mode,
        created_by_id=principal.id,
    )
    db.add(quiz)
    db.flush()

    for index, item in enumerate(accepted):
        chunk_id = chunk_ids.get(item["source_id"])
        page = None
        if chunk_id:
            chunk = next((c for c in chunk_rows if c.id == chunk_id), None)
            page = chunk.page_from if chunk else None
        db.add(
            QuizQuestion(
                quiz_id=quiz.id,
                question_type=QuestionType.SINGLE_MCQ.value,
                stem=item["stem"],
                options=[{"text": opt, "index": i} for i, opt in enumerate(item["options"])],
                correct_index=item["correct_index"],
                explanation=item["explanation"],
                source_document_id=document.id,
                source_chunk_id=chunk_id,
                source_page=page,
                source_quote=item["source_quote"],
                competency_id=payload.competency_ids[0] if payload.competency_ids else None,
                difficulty=item["difficulty"],
                sort_order=index,
                validation_state="validated",
                validation_notes=[],
            )
        )

    db.add(
        AiUsageLog(
            user_id=principal.id, operation="quiz_generate",
            model=None if mode == "extractive_fallback" else "llm", outcome="ok",
        )
    )
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="quiz.generated", resource_type="quiz", resource_id=str(quiz.id),
                 detail=f"{len(accepted)} questions, mode={mode}")
    db.commit()
    db.refresh(quiz)
    return _detail(db, quiz, principal)


@router.get("/quizzes", response_model=list[QuizOut])
def list_quizzes(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*PLAYER_ROLES)),
    page: Page = Depends(pagination),
    status_filter: str | None = Query(default=None, alias="status"),
    mine: bool = False,
) -> list[QuizOut]:
    stmt = select(Quiz)
    if principal.role not in EDITOR_ROLES:
        stmt = stmt.where(Quiz.status == QuizStatus.PUBLISHED.value)
    elif status_filter:
        stmt = stmt.where(Quiz.status == status_filter)
    if mine:
        stmt = stmt.where(Quiz.created_by_id == principal.id)
    stmt = stmt.order_by(Quiz.created_at.desc()).limit(page.limit).offset(page.offset)
    return [_quiz_out(db, q, principal.id) for q in db.scalars(stmt)]


@router.get("/quizzes/{quiz_id}", response_model=QuizDetailOut)
def get_quiz(
    quiz_id: uuid.UUID, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*PLAYER_ROLES)),
) -> QuizDetailOut:
    quiz = _load_quiz(db, quiz_id)
    if quiz.status != QuizStatus.PUBLISHED.value and principal.role not in EDITOR_ROLES:
        raise HTTPException(404, "Quiz not found")
    return _detail(db, quiz, principal)


@router.patch("/quizzes/{quiz_id}/questions/{question_id}", response_model=QuizDetailOut)
def edit_question(
    quiz_id: uuid.UUID, question_id: uuid.UUID, payload: QuestionUpdateRequest,
    db: Session = Depends(get_db), principal: Principal = Depends(require_roles(*EDITOR_ROLES)),
) -> QuizDetailOut:
    quiz = _load_quiz(db, quiz_id)
    if quiz.status == QuizStatus.PUBLISHED.value and principal.role != Role.ADMIN:
        raise HTTPException(409, "Publish locked; an administrator must unpublish to edit")

    question = db.get(QuizQuestion, question_id)
    if question is None or question.quiz_id != quiz.id:
        raise HTTPException(404, "Question not found")

    if payload.stem is not None:
        question.stem = payload.stem.strip()
    if payload.explanation is not None:
        question.explanation = payload.explanation.strip()
    if payload.difficulty is not None:
        question.difficulty = payload.difficulty
    if payload.options is not None:
        if len(payload.options) != 4:
            raise HTTPException(422, "Exactly four options are required")
        question.options = [
            {"text": opt.strip(), "index": i} for i, opt in enumerate(payload.options)
        ]
    if payload.correct_index is not None:
        question.correct_index = payload.correct_index

    # Re-validate structural integrity after an edit.
    option_texts = [o["text"] for o in question.options]
    if len({t.lower().strip() for t in option_texts}) != 4:
        raise HTTPException(422, "Options must be distinct")

    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="quiz.question_edited", resource_type="quiz_question",
                 resource_id=str(question.id))
    db.commit()
    db.refresh(quiz)
    return _detail(db, quiz, principal)


@router.delete("/quizzes/{quiz_id}/questions/{question_id}", response_model=QuizDetailOut)
def delete_question(
    quiz_id: uuid.UUID, question_id: uuid.UUID, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*EDITOR_ROLES)),
) -> QuizDetailOut:
    quiz = _load_quiz(db, quiz_id)
    question = db.get(QuizQuestion, question_id)
    if question is None or question.quiz_id != quiz.id:
        raise HTTPException(404, "Question not found")
    remaining = [q for q in quiz.questions if q.is_active and q.id != question.id]
    if not remaining:
        raise HTTPException(422, "A quiz must keep at least one question")
    db.delete(question)
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="quiz.question_deleted", resource_type="quiz_question",
                 resource_id=str(question_id))
    db.commit()
    db.refresh(quiz)
    return _detail(db, quiz, principal)


@router.post("/quizzes/{quiz_id}/publish", response_model=QuizDetailOut)
def publish_quiz(
    quiz_id: uuid.UUID, payload: QuizPublishRequest, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*EDITOR_ROLES)),
) -> QuizDetailOut:
    quiz = _load_quiz(db, quiz_id)
    active = [q for q in quiz.questions if q.is_active]
    if not active:
        raise HTTPException(422, "Cannot publish a quiz with no questions")
    for question in active:
        if len(question.options) != 4:
            raise HTTPException(
                422, f"Question {question.sort_order + 1} does not have four options"
            )

    if payload.title:
        quiz.title = payload.title.strip()
    if payload.description is not None:
        quiz.description = payload.description
    quiz.status = QuizStatus.PUBLISHED.value
    quiz.approved_by_id = principal.id
    quiz.approved_at = dt.datetime.now(dt.timezone.utc)
    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="quiz.published", resource_type="quiz", resource_id=str(quiz.id),
                 detail=f"{len(active)} questions")
    db.commit()
    db.refresh(quiz)
    return _detail(db, quiz, principal)


@router.delete("/quizzes/{quiz_id}", status_code=204, response_model=None)
def delete_quiz(
    quiz_id: uuid.UUID, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*EDITOR_ROLES)),
) -> None:
    quiz = _load_quiz(db, quiz_id)
    if quiz.created_by_id != principal.id and principal.role != Role.ADMIN:
        raise HTTPException(403, "Only the creator or an administrator may delete this quiz")
    attempt_count = db.scalar(
        select(func.count(QuizAttempt.id)).where(QuizAttempt.quiz_id == quiz.id)
    ) or 0
    if attempt_count:
        # Preserve attempt history: archive rather than delete.
        quiz.status = QuizStatus.ARCHIVED.value
        audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                     action="quiz.archived", resource_type="quiz", resource_id=str(quiz.id),
                     detail=f"{attempt_count} attempts preserved")
    else:
        db.delete(quiz)
        audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                     action="quiz.deleted", resource_type="quiz", resource_id=str(quiz.id))
    db.commit()


# ---------------------------------------------------------------- attempts
@router.post("/quizzes/{quiz_id}/attempts", response_model=dict, status_code=201)
def start_attempt(
    quiz_id: uuid.UUID, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*PLAYER_ROLES)),
) -> dict:
    quiz = _load_quiz(db, quiz_id)
    if quiz.status != QuizStatus.PUBLISHED.value:
        raise HTTPException(409, "This quiz is not open for attempts")
    active = [q for q in quiz.questions if q.is_active]
    if not active:
        raise HTTPException(422, "Quiz has no questions")

    attempt = QuizAttempt(
        quiz_id=quiz.id, user_id=principal.id, score_total=len(active), option_order={}
    )
    db.add(attempt)
    db.flush()

    # Per-attempt option order, so re-attempts do not memorise positions.
    rng = random.Random(f"{attempt.id}")
    rendered = []
    for question in active:
        indices = list(range(len(question.options)))
        if quiz.shuffle_options:
            rng.shuffle(indices)
        attempt.option_order[str(question.id)] = indices
        rendered.append(
            {
                "question_id": str(question.id),
                "stem": question.stem,
                "options": [
                    {"index": new_index, "text": question.options[old_index]["text"]}
                    for new_index, old_index in enumerate(indices)
                ],
                "difficulty": question.difficulty,
                "source_page": question.source_page,
            }
        )
    db.commit()
    return {
        "attempt_id": str(attempt.id),
        "quiz_id": str(quiz.id),
        "title": quiz.title,
        "time_limit_minutes": quiz.time_limit_minutes,
        "pass_percent": quiz.pass_percent,
        "questions": rendered,
    }


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptResultOut)
def submit_attempt(
    attempt_id: uuid.UUID, payload: AttemptSubmitRequest, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*PLAYER_ROLES)),
) -> AttemptResultOut:
    attempt = db.get(QuizAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(404, "Attempt not found")
    # IDOR guard: attempts belong to exactly one user.
    if attempt.user_id != principal.id:
        raise HTTPException(403, "This attempt does not belong to you")
    if attempt.submitted_at is not None:
        raise HTTPException(409, "This attempt has already been submitted")

    quiz = db.get(Quiz, attempt.quiz_id)
    assert quiz is not None
    active = [q for q in quiz.questions if q.is_active]
    order_map = attempt.option_order or {}

    correct = 0
    answers_out = []
    competency_scores: dict[uuid.UUID, list[bool]] = {}

    for question in active:
        raw = payload.answers.get(str(question.id))
        chosen_render_index = raw if isinstance(raw, int) else None
        order = order_map.get(str(question.id)) or list(range(len(question.options)))

        original_index = None
        if chosen_render_index is not None and 0 <= chosen_render_index < len(order):
            original_index = order[chosen_render_index]

        is_correct = original_index == question.correct_index
        if is_correct:
            correct += 1
        if question.competency_id:
            competency_scores.setdefault(question.competency_id, []).append(is_correct)

        db.add(
            QuizAnswer(
                attempt_id=attempt.id, question_id=question.id,
                selected_index=original_index, is_correct=is_correct,
            )
        )
        answers_out.append(
            {
                "question_id": question.id, "stem": question.stem,
                "options": question.options, "correct_index": question.correct_index,
                "selected_index": original_index, "is_correct": is_correct,
                "explanation": question.explanation,
                "source_page": question.source_page, "source_quote": question.source_quote,
            }
        )

    total = max(len(active), 1)
    percent = round(100.0 * correct / total, 1)
    attempt.score_correct = correct
    attempt.score_total = len(active)
    attempt.score_percent = percent
    attempt.passed = percent >= quiz.pass_percent
    attempt.submitted_at = dt.datetime.now(dt.timezone.utc)

    # Feed quiz evidence back into competency state (bounded: gap engine caps its influence).
    for competency_id, results in competency_scores.items():
        accuracy = sum(results) / len(results)
        state = db.scalars(
            select(CompetencyState).where(
                CompetencyState.user_id == principal.id,
                CompetencyState.competency_id == competency_id,
            )
        ).first()
        if state is None:
            db.add(
                CompetencyState(
                    user_id=principal.id, competency_id=competency_id, level=0.0,
                    method="quiz_only", confidence=2, quiz_evidence=round(accuracy, 3),
                    assessed_at=dt.datetime.now(dt.timezone.utc),
                )
            )
        else:
            state.quiz_evidence = round(accuracy, 3)

    audit.record(db, actor_id=principal.id, actor_role=principal.role.value,
                 action="quiz.submitted", resource_type="quiz_attempt",
                 resource_id=str(attempt.id), detail=f"{correct}/{len(active)} ({percent}%)")
    db.commit()

    from app.services import recommend

    recommend.ensure_plan(db, principal.user, force=True)
    db.commit()

    return AttemptResultOut(
        id=attempt.id, quiz_id=quiz.id, quiz_title=quiz.title, score_correct=correct,
        score_total=len(active), score_percent=percent, passed=attempt.passed,
        submitted_at=attempt.submitted_at, answers=answers_out,
    )


@router.get("/attempts/{attempt_id}", response_model=AttemptResultOut)
def get_attempt(
    attempt_id: uuid.UUID, db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*PLAYER_ROLES)),
) -> AttemptResultOut:
    attempt = db.get(QuizAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(404, "Attempt not found")
    if attempt.user_id != principal.id and principal.role not in (Role.ADMIN, Role.ASSESSOR):
        raise HTTPException(403, "This attempt does not belong to you")

    quiz = db.get(Quiz, attempt.quiz_id)
    questions = {q.id: q for q in quiz.questions} if quiz else {}
    answers = []
    for answer in attempt.answers:
        question = questions.get(answer.question_id)
        if question is None:
            continue
        answers.append(
            {
                "question_id": question.id, "stem": question.stem,
                "options": question.options, "correct_index": question.correct_index,
                "selected_index": answer.selected_index, "is_correct": answer.is_correct,
                "explanation": question.explanation, "source_page": question.source_page,
                "source_quote": question.source_quote,
            }
        )
    return AttemptResultOut(
        id=attempt.id, quiz_id=attempt.quiz_id,
        quiz_title=quiz.title if quiz else "Quiz", score_correct=attempt.score_correct,
        score_total=attempt.score_total, score_percent=attempt.score_percent,
        passed=attempt.passed, submitted_at=attempt.submitted_at, answers=answers,
    )


@router.get("/me/attempts", response_model=list[dict])
def my_attempts(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_roles(*PLAYER_ROLES)),
) -> list[dict]:
    rows = db.execute(
        select(QuizAttempt, Quiz.title)
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
        .where(QuizAttempt.user_id == principal.id, QuizAttempt.submitted_at.is_not(None))
        .order_by(QuizAttempt.submitted_at.desc())
        .limit(50)
    ).all()
    return [
        {
            "id": str(attempt.id), "quiz_id": str(attempt.quiz_id), "quiz_title": title,
            "score_percent": attempt.score_percent, "score_correct": attempt.score_correct,
            "score_total": attempt.score_total, "passed": attempt.passed,
            "submitted_at": attempt.submitted_at,
        }
        for attempt, title in rows
    ]
