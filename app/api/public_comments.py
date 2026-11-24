import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.comment import Comment, CommentStatus, Sentiment
from app.schemas.comment import CommentSubmitResponse, PageOut, PublicCommentOut
from app.services.sentiment import get_sentiment_service
from app.core.config import settings

router = APIRouter(prefix="/api/v1/comments", tags=["Public comments"])


@router.post("", response_model=CommentSubmitResponse, status_code=201)
async def submit_comment(
    name: str = Form(min_length=1, max_length=100),
    message: str = Form(min_length=2, max_length=2000),
    profile_picture: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    name = name.strip()
    message = message.strip()
    if not name or len(message) < 2:
        raise HTTPException(status_code=422, detail="Please provide a name and a message.")

    profile_picture_url = None
    if profile_picture and profile_picture.filename:
        extensions = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif", "image/webp": ".webp"}
        extension = extensions.get(profile_picture.content_type or "")
        if not extension:
            raise HTTPException(status_code=422, detail="Please upload a JPG, PNG, GIF, or WebP profile picture.")
        image_bytes = await profile_picture.read(2 * 1024 * 1024 + 1)
        if len(image_bytes) > 2 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="The profile picture must be 2 MB or smaller.")
        upload_dir = Path(settings.upload_dir)
        try:
            upload_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise HTTPException(status_code=500, detail="The profile picture storage directory is unavailable.") from exc
        filename = f"{uuid.uuid4().hex}{extension}"
        try:
            (upload_dir / filename).write_bytes(image_bytes)
        except OSError as exc:
            raise HTTPException(status_code=500, detail="The profile picture could not be saved.") from exc
        profile_picture_url = f"/uploads/{filename}"
    if profile_picture:
        await profile_picture.close()

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
        profile_picture=profile_picture_url,
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
