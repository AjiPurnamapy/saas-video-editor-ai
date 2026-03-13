import os
import uuid
import pytest
from unittest.mock import patch, MagicMock
from app.models.job import Job
from app.models.enums import JobStatus
from workers.tasks.video_tasks import _check_cancelled, _CancelledError

def test_check_cancelled_aborts_on_cancelled_status(db_session):
    job = Job(id=str(uuid.uuid4()), video_id=str(uuid.uuid4()), status=JobStatus.CANCELLED, progress=0)
    db_session.add(job)
    db_session.commit()
    
    with pytest.raises(_CancelledError, match="cancelled by user"):
        _check_cancelled(db_session, job.id, [])

def test_check_cancelled_aborts_on_failed_status(db_session):
    job = Job(id=str(uuid.uuid4()), video_id=str(uuid.uuid4()), status=JobStatus.FAILED, progress=0)
    db_session.add(job)
    db_session.commit()
    
    with pytest.raises(_CancelledError, match="marked failed by recovery system"):
        _check_cancelled(db_session, job.id, [])

def test_check_cancelled_passes_on_processing(db_session):
    job = Job(id=str(uuid.uuid4()), video_id=str(uuid.uuid4()), status=JobStatus.PROCESSING, progress=0)
    db_session.add(job)
    db_session.commit()
    
    # Should not raise any exception
    _check_cancelled(db_session, job.id, [])

@patch('app.utils.file_utils.cleanup_temp_files')
def test_check_cancelled_cleans_temp_files(mock_cleanup, db_session):
    job = Job(id=str(uuid.uuid4()), video_id=str(uuid.uuid4()), status=JobStatus.CANCELLED, progress=0)
    db_session.add(job)
    db_session.commit()
    
    temp_files = ["/tmp/file1.mp4", "/tmp/file2.wav"]
    
    with pytest.raises(_CancelledError):
        _check_cancelled(db_session, job.id, temp_files)
        
    mock_cleanup.assert_called_once_with(*temp_files)
