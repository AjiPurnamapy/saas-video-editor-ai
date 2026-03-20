import os
import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi import UploadFile
from app.services.video_service import VideoService
from app.models.video import Video
from app.models.job import Job
from app.models.enums import JobStatus, VideoStatus
from app.core.exceptions import ConflictError, ValidationError, FileTooLargeError

@pytest.fixture
def user_id():
    return str(uuid.uuid4())

@pytest.fixture
def video_service(db_session):
    return VideoService(db_session)

def test_delete_video_with_active_job_raises_conflict(video_service, db_session, user_id):
    """Test that deleting a video with a QUEUED or PROCESSING job is blocked."""
    # Setup: Create video and an active job
    video = Video(id=str(uuid.uuid4()), user_id=user_id, raw_video_path="/tmp/vid.mp4", status=VideoStatus.PROCESSING)
    db_session.add(video)
    db_session.commit()
    
    job = Job(id=str(uuid.uuid4()), video_id=video.id, status=JobStatus.PROCESSING, progress=50)
    db_session.add(job)
    db_session.commit()

    # Attempt to delete, should raise ConflictError
    with pytest.raises(ConflictError, match="Cannot delete video with an active processing job"):
        video_service.delete_video(video.id, user_id)

def test_delete_video_success_cascades_outputs(video_service, db_session, user_id):
    """Test safe video deletion removes output directories."""
    # Setup
    video_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    video_dir = os.path.join("/tmp/uploads", user_id)
    raw_path = os.path.join(video_dir, f"{video_id}.mp4")
    outputs_dir = os.path.join(video_dir, "outputs")
    job_output_dir = os.path.join(outputs_dir, job_id)
    
    video = Video(id=video_id, user_id=user_id, raw_video_path=raw_path, status=VideoStatus.COMPLETED)
    db_session.add(video)
    job = Job(id=job_id, video_id=video.id, status=JobStatus.COMPLETED, progress=100)
    db_session.add(job)
    db_session.commit()

    # Mock filesystem functions
    with patch('os.path.isdir') as mock_isdir, \
         patch('shutil.rmtree') as mock_rmtree, \
         patch('os.rmdir') as mock_rmdir, \
         patch('app.services.storage_service.StorageService.delete_file') as mock_storage_delete:
         
         # Force isdir to true to simulate outputs dir existing
         mock_isdir.return_value = True
         
         video_service.delete_video(video.id, user_id)
         
         # Assert output directory was deleted
         mock_rmtree.assert_called_once_with(job_output_dir, ignore_errors=True)
         # Assert raw file deleted
         mock_storage_delete.assert_called_once_with(raw_path)
         
         # Assert DB records are gone (cascade)
         assert db_session.query(Video).count() == 0
         assert db_session.query(Job).count() == 0

@pytest.mark.asyncio
async def test_upload_video_invalid_type(video_service, user_id):
    """Test uploading non-video file raises ValidationError."""
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "document.pdf"
    mock_file.content_type = "application/pdf"
    
    with pytest.raises(ValidationError, match="Unsupported file type"):
        await video_service.upload_video(mock_file, user_id)
