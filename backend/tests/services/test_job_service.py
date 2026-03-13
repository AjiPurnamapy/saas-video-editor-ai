import pytest
import uuid
from app.services.job_service import JobService
from app.models.video import Video
from app.models.job import Job
from app.models.enums import JobStatus, VideoStatus
from app.core.exceptions import ConflictError, NotFoundError, ForbiddenError

@pytest.fixture
def user_id():
    return str(uuid.uuid4())

@pytest.fixture
def shared_video(db_session, user_id):
    video = Video(id=str(uuid.uuid4()), user_id=user_id, raw_video_path="/tmp/v.mp4", status=VideoStatus.UPLOADED)
    db_session.add(video)
    db_session.commit()
    return video

def test_create_job_success(db_session, shared_video, user_id):
    """Test normal job creation."""
    service = JobService(db_session)
    job = service.create_job(shared_video.id, user_id)
    
    assert job.status == JobStatus.QUEUED
    assert job.video_id == shared_video.id
    
    db_session.refresh(shared_video)
    assert shared_video.status == VideoStatus.PROCESSING

def test_create_job_duplicate_prevents_race(db_session, shared_video, user_id):
    """Test duplicate job creation raises ConflictError."""
    service = JobService(db_session)
    # Create first job
    service.create_job(shared_video.id, user_id)
    
    # Second attempt should fail due to active job check with FOR UPDATE lock
    with pytest.raises(ConflictError, match="Video already has an active processing job"):
        service.create_job(shared_video.id, user_id)

def test_cancel_job_success_and_revokes_celery(db_session, shared_video, user_id, mocker):
    """Test cancelling a queued job."""
    service = JobService(db_session)
    job = service.create_job(shared_video.id, user_id)
    
    # Mock celery app - the cancel_job method does a lazy import:
    #   from workers.celery_app import celery_app
    #   celery_app.control.revoke(...)
    # So we mock the module-level celery_app inside workers.celery_app
    mock_revoke = mocker.patch('workers.celery_app.celery_app.control.revoke')
    
    # Give the job a fake task ID
    task_id = "test-task-123"
    service.set_task_id(job.id, task_id)
    
    # Cancel it
    cancelled_job = service.cancel_job(job.id, user_id)
    
    assert cancelled_job.status == JobStatus.CANCELLED
    # The actual code uses terminate=False
    mock_revoke.assert_called_once_with(task_id, terminate=False)

def test_cancel_job_wrong_user(db_session, shared_video, user_id):
    """Test cancelling someone else's job raises NotFoundError (ownership check fails)."""
    service = JobService(db_session)
    job = service.create_job(shared_video.id, user_id)
    
    wrong_user = str(uuid.uuid4())
    # The cancel_job method joins Video to check user_id, so wrong user => NotFoundError
    with pytest.raises(NotFoundError):
        service.cancel_job(job.id, wrong_user)
