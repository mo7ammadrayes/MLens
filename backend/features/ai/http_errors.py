import json
import logging
from contextlib import contextmanager

from fastapi import HTTPException
from pydantic import ValidationError
from google.genai._gaos.lib.compat_errors import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)

from backend.features.ai.errors import UnsupportedRecommendationError


logger = logging.getLogger(__name__)


@contextmanager
def handle_ai_errors(operation: str):
    try:
        yield

    except APITimeoutError as exc:
        logger.exception("%s timed out", operation)
        raise HTTPException(
            504,
            "The AI provider timed out. Please try again later.",
        ) from exc

    except RateLimitError as exc:
        logger.exception("%s reached a provider limit", operation)
        raise HTTPException(
            503,
            "The AI feature is temporarily unavailable.",
        ) from exc

    except APIConnectionError as exc:
        logger.exception("%s could not connect to the provider", operation)
        raise HTTPException(
            503,
            "Could not connect to the AI provider.",
        ) from exc

    except APIStatusError as exc:
        logger.exception("%s was rejected by the provider", operation)
        raise HTTPException(
            502,
            "The AI provider could not complete the request.",
        ) from exc

    except (json.JSONDecodeError, ValidationError) as exc:
        logger.exception("%s returned invalid output", operation)
        raise HTTPException(
            502,
            "The AI provider returned an invalid response.",
        ) from exc

    except UnsupportedRecommendationError as exc:
        logger.exception("%s returned unsupported recommendations", operation)
        raise HTTPException(
            502,
            "The AI provider suggested an unsupported configuration.",
        ) from exc