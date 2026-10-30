from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.comment import Comment, CommentStatus, Sentiment
from app.schemas.comment import CommentCreate, CommentSubmitResponse, PageOut, PublicCommentOut
from app.services.sentiment import get_sentiment_service

router = APIRouter(prefix="/api/v1/comments", tags=["Public comments"])


@router.post("", response_model=CommentSubmitResponse, status_code=201)
def submit_comment(payload: CommentCreate, db: Session = Depends(get_db)):
    name = payload.name.strip()
    message = payload.message.strip()
    if not name or len(message) < 2:
        raise HTTPException(status_code=422, detail="Please provide a name and a message.")

    # A service/model outage must not silently publish an unscored comment.
    # Keep it pending with unknown sentiment and let the admin review it.
    try:
        sentiment, score = get_sentiment_service().predict(message)
    except RuntimeError:
        sentiment, score = None, None

    if sentiment is None:
        sentiment = Sentiment.unknown
        status_value = CommentStatus.pending
    elif sentiment == Sentiment.negative:
        status_value = CommentStatus.pending
    else:
        status_value = CommentStatus.approved

    comment = Comment(
        name=name,
        message=message,
        sentiment=sentiment,
        sentiment_score=score,
        status=status_value,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    # Never reveal sentiment or status to the submitting visitor.
    return CommentSubmitResponse(
        success=True,
        message="Your comment has been submitted successfully.",
        comment_id=comment.id,
    )


@router.get("", response_model=PageOut)
def list_public_comments(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    filters = [Comment.status == CommentStatus.approved]
    total = db.scalar(select(func.count()).select_from(Comment).where(*filters)) or 0
    items = db.scalars(
        select(Comment)
        .where(*filters)
        .order_by(Comment.created_at.desc(), Comment.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    # Explicit public schema prevents internal sentiment/status fields leaking.
    return {
        "items": [PublicCommentOut.model_validate(item).model_dump() for item in items],
        "page": page,
        "limit": limit,
        "total": total,
        "has_more": page * limit < total,
    }
