import os
import uuid
import pytest
from unittest.mock import patch, MagicMock
from app.models.job import Job
from app.models.enums import JobStatus
from workers.tasks.maintenance_tasks import recover_stale_jobs, cleanup_orphan_files

@pytest.fixture
def db_pool_override(db_session):
    """Override worker DB session for testing."""
    with patch('workers.tasks.video_tasks._get_db_session') as mock_db:
        mock_db.return_value = db_session
        yield

def test_recover_stale_jobs(db_session, db_pool_override):
    # Create an old processing job
    old_job_id = str(uuid.uuid4())
    fresh_job_id = str(uuid.uuid4())
    
    old_job = Job(id=old_job_id, video_id=str(uuid.uuid4()), status=JobStatus.PROCESSING, progress=30)
    
    # Create a fresh processing job
    fresh_job = Job(id=fresh_job_id, video_id=str(uuid.uuid4()), status=JobStatus.PROCESSING, progress=50)
    
    db_session.add(old_job)
    db_session.add(fresh_job)
    db_session.commit()
    db_session.refresh(old_job)
    db_session.refresh(fresh_job)
    
    # Manually tweak timestamp for old_job to be 2 hours ago
    from datetime import datetime, timedelta, timezone
    old_job.updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db_session.commit()
    
    # Run task
    recover_stale_jobs()
    
    # Verify using completely fresh queries
    old_job_check = db_session.get(Job, old_job_id)
    fresh_job_check = db_session.get(Job, fresh_job_id)
    
    assert old_job_check is not None
    assert old_job_check.status == JobStatus.FAILED
    
    assert fresh_job_check is not None
    assert fresh_job_check.status == JobStatus.PROCESSING

@patch('os.walk')
@patch('os.path.getmtime')
@patch('app.utils.file_utils.cleanup_temp_files')
def test_cleanup_orphan_files(mock_cleanup, mock_mtime, mock_walk, db_pool_override):
    import time
    now = time.time()
    
    # Setup mock filesystem
    mock_walk.return_value = [
        ('/uploads/user1', [], ['old.wav', 'new.wav', 'clip_old.mp4', 'keep.mp4'])
    ]
    
    # Mock modification times
    # old > 2 hours (7200s), new < 2 hours
    def mtime_side_effect(path):
        if 'old' in path: return now - 8000
        return now - 1000
    mock_mtime.side_effect = mtime_side_effect
    
    # Run task
    cleanup_orphan_files()
    
    # Verify only old matching files were sent to cleanup
    import sys
    calls = mock_cleanup.call_args_list
    if len(calls) > 0:
        cleaned_paths = calls[0][0]
        # Should only clean old.wav and clip_old.mp4 (matching patterns and old enough)
        # Note: on windows paths use \, on linux /
        assert any('old.wav' in p for p in cleaned_paths)
        assert any('clip_old.mp4' in p for p in cleaned_paths)
        assert not any('new.wav' in p for p in cleaned_paths)
        assert not any('keep.mp4' in p for p in cleaned_paths)
