from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.comment import CommentStatus, Sentiment


class CommentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=2, max_length=2000)


class CommentSubmitResponse(BaseModel):
    success: bool = True
    message: str = "Your comment has been submitted successfully."
    comment_id: str


class PublicCommentOut(BaseModel):
    id: str
    name: str
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminCommentOut(PublicCommentOut):
    sentiment: Sentiment
    sentiment_score: float | None
    status: CommentStatus
    reviewed_at: datetime | None
    reviewed_by: str | None

    model_config = ConfigDict(from_attributes=True)


class PageOut(BaseModel):
    items: list
    page: int
    limit: int
    total: int
    has_more: bool


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ActionResponse(BaseModel):
    success: bool = True
    message: str


class AnalyticsOut(BaseModel):
    total: int
    approved: int
    pending: int
    negative: int
