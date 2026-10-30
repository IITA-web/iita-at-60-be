from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from app.core.security import require_admin
from app.db.session import get_db
from app.models.comment import Comment, CommentStatus, Sentiment
from app.schemas.comment import ActionResponse, AdminCommentOut, PageOut, AnalyticsOut

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


@router.get("/comments", response_model=PageOut)
def list_admin_comments(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    sentiment_filter: str | None = Query(default=None, alias="sentiment"),
    search: str | None = Query(default=None, max_length=200),
    db: Session = Depends(get_db),
):
    filters = []
    if status_filter and status_filter != "all":
        try:
            filters.append(Comment.status == CommentStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid status filter.")
    if sentiment_filter:
        try:
            filters.append(Comment.sentiment == Sentiment(sentiment_filter))
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid sentiment filter.")
    if search and search.strip():
        term = f"%{search.strip()}%"
        filters.append(or_(Comment.name.ilike(term), Comment.message.ilike(term)))

    total = db.scalar(select(func.count()).select_from(Comment).where(*filters)) or 0
    items = db.scalars(
        select(Comment)
        .where(*filters)
        .order_by(Comment.created_at.desc(), Comment.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return {
        "items": [AdminCommentOut.model_validate(item).model_dump() for item in items],
        "page": page,
        "limit": limit,
        "total": total,
        "has_more": page * limit < total,
    }


@router.patch("/comments/{comment_id}/approve", response_model=ActionResponse)
def approve_comment(
    comment_id: str,
    admin_username: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    comment = db.get(Comment, comment_id)
    if comment is None or comment.status == CommentStatus.deleted:
        raise HTTPException(status_code=404, detail="Comment not found.")
    comment.status = CommentStatus.approved
    comment.reviewed_at = datetime.now(timezone.utc)
    comment.reviewed_by = admin_username
    db.commit()
    return ActionResponse(message="Comment approved and available for public display.")


@router.delete("/comments/{comment_id}", response_model=ActionResponse)
def delete_comment(
    comment_id: str,
    admin_username: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found.")
    if comment.status == CommentStatus.deleted:
        return ActionResponse(message="Comment is already deleted.")
    # Soft-delete to preserve auditability; public API excludes deleted records.
    comment.status = CommentStatus.deleted
    comment.reviewed_at = datetime.now(timezone.utc)
    comment.reviewed_by = admin_username
    db.commit()
    return ActionResponse(message="Comment deleted.")


@router.get("/analytics", response_model=AnalyticsOut)
def analytics(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(Comment).where(Comment.status != CommentStatus.deleted)) or 0
    approved = db.scalar(select(func.count()).select_from(Comment).where(Comment.status == CommentStatus.approved)) or 0
    pending = db.scalar(select(func.count()).select_from(Comment).where(Comment.status == CommentStatus.pending)) or 0
    negative = db.scalar(select(func.count()).select_from(Comment).where(
        Comment.sentiment == Sentiment.negative,
        Comment.status != CommentStatus.deleted,
    )) or 0
    return AnalyticsOut(total=total, approved=approved, pending=pending, negative=negative)
