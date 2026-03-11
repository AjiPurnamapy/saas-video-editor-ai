"""
Output service.

Business logic for retrieving processed video outputs.
All queries enforce user ownership via the Video table.
"""

import logging
from typing import List

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.output import Output
from app.models.video import Video

logger = logging.getLogger(__name__)


class OutputService:
    """Encapsulates output retrieval business logic."""

    def __init__(self, db: Session) -> None:
        """Initialize OutputService with a database session.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db

    def list_outputs(self, video_id: str, user_id: str) -> tuple[List[Output], int]:
        """List all outputs for a video, with ownership verification.

        Joins through the Video table to ensure the requesting user
        owns the video.

        Args:
            video_id: The video UUID.
            user_id: The requesting user's UUID.

        Returns:
            A tuple of (list of outputs, total count).

        Raises:
            NotFoundError: If the video is not found or not owned by user.
        """
        # Verify video ownership
        video = (
            self.db.query(Video)
            .filter(Video.id == video_id, Video.user_id == user_id)
            .first()
        )
        if not video:
            raise NotFoundError("Video not found")

        outputs = (
            self.db.query(Output)
            .filter(Output.video_id == video_id)
            .order_by(Output.created_at.desc())
            .all()
        )
        return outputs, len(outputs)

    def get_output(self, output_id: str, user_id: str) -> Output:
        """Retrieve a single output with ownership verification.

        Joins through the Video table to ensure the requesting user
        owns the video associated with this output.

        Args:
            output_id: The output UUID.
            user_id: The requesting user's UUID.

        Returns:
            The Output model.

        Raises:
            NotFoundError: If the output is not found or not owned by user.
        """
        output = (
            self.db.query(Output)
            .join(Video, Output.video_id == Video.id)
            .filter(Output.id == output_id, Video.user_id == user_id)
            .first()
        )
        if not output:
            raise NotFoundError("Output not found")
        return output
