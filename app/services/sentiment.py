from functools import lru_cache
from app.core.config import settings
from app.models.comment import Sentiment


class SentimentService:
    """Lazy-load a pretrained Hugging Face sentiment model on first use.

    The default SST-2 model is English-focused and binary. We treat low-confidence
    predictions as neutral; the score returned by this pipeline is confidence in
    its predicted label, not the probability of a positive label.
    """

    def __init__(self) -> None:
        self._pipeline = None
        self._load_error: str | None = None

    def _load(self):
        if self._pipeline is not None:
            return self._pipeline
        if self._load_error:
            raise RuntimeError(self._load_error)
        try:
            from transformers import pipeline
            self._pipeline = pipeline(
                "sentiment-analysis",
                model=settings.sentiment_model,
                truncation=True,
            )
            return self._pipeline
        except Exception as exc:
            self._load_error = (
                "The sentiment model could not be loaded. Check backend internet access, "
                "installed ML dependencies, and the SENTIMENT_MODEL setting."
            )
            raise RuntimeError(self._load_error) from exc

    def predict(self, text: str) -> tuple[Sentiment, float]:
        model = self._load()
        result = model(text[:4000], truncation=True, max_length=512)[0]
        label = str(result.get("label", "")).upper()
        score = float(result.get("score", 0.0))

        # SST-2 returns confidence in the predicted class. Low confidence is held
        # as neutral for human review instead of treating confidence as polarity.
        confidence_threshold = max(0.50, min(0.99, 1.0 - settings.sentiment_neutral_band))
        if score < confidence_threshold:
            return Sentiment.neutral, score

        if label in {"POSITIVE", "LABEL_1"}:
            return Sentiment.positive, score
        if label in {"NEGATIVE", "LABEL_0"}:
            return Sentiment.negative, score
        return Sentiment.unknown, score


@lru_cache
def get_sentiment_service() -> SentimentService:
    return SentimentService()
