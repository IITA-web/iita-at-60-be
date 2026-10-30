"""Small sanity tests for core moderation policy.

Run from backend with: pytest
These tests do not download or initialize the ML model.
"""
from app.models.comment import CommentStatus, Sentiment


def initial_status(sentiment: Sentiment | None) -> CommentStatus:
    if sentiment is None or sentiment in (Sentiment.negative, Sentiment.unknown):
        return CommentStatus.pending
    return CommentStatus.approved


def test_negative_comments_are_pending():
    assert initial_status(Sentiment.negative) == CommentStatus.pending


def test_positive_comments_are_approved():
    assert initial_status(Sentiment.positive) == CommentStatus.approved


def test_neutral_comments_are_approved():
    assert initial_status(Sentiment.neutral) == CommentStatus.approved


def test_unknown_comments_are_pending():
    assert initial_status(Sentiment.unknown) == CommentStatus.pending
