import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CommentStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    deleted = "deleted"


class Sentiment(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"
    unknown = "unknown"


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[Sentiment] = mapped_column(Enum(Sentiment), nullable=False, default=Sentiment.unknown)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[CommentStatus] = mapped_column(Enum(CommentStatus), nullable=False, default=CommentStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
