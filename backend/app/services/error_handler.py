import logging

from app.models.errors import PipelineError

logger = logging.getLogger(__name__)


def pipeline_error(message: str, error: Exception) -> PipelineError:
    logger.exception(message, exc_info=error)
    return PipelineError(message)
