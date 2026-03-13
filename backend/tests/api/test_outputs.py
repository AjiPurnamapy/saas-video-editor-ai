import pytest
from fastapi.testclient import TestClient
import uuid
from app.models.enums import JobStatus, VideoStatus

def test_list_outputs_success(auth_client: TestClient, db_session):
    # Setup video
    video_id = str(uuid.uuid4())
    user_id = auth_client.get("/api/auth/me").json()["id"]
    from app.models.video import Video
    video = Video(id=video_id, user_id=user_id, raw_video_path="/tmp/v.mp4", status=VideoStatus.COMPLETED)
    db_session.add(video)
    
    # Setup output
    from app.models.output import Output
    output_id = str(uuid.uuid4())
    output = Output(id=output_id, video_id=video_id, file_url="/tmp/output.mp4")
    db_session.add(output)
    db_session.commit()
    
    response = auth_client.get(f"/api/outputs?video_id={video_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["outputs"][0]["id"] == output_id

def test_get_output_success(auth_client: TestClient, db_session):
    # Setup video
    video_id = str(uuid.uuid4())
    user_id = auth_client.get("/api/auth/me").json()["id"]
    from app.models.video import Video
    video = Video(id=video_id, user_id=user_id, raw_video_path="/tmp/v.mp4", status=VideoStatus.COMPLETED)
    db_session.add(video)
    
    # Setup output
    from app.models.output import Output
    output_id = str(uuid.uuid4())
    output = Output(id=output_id, video_id=video_id, file_url="/tmp/output.mp4")
    db_session.add(output)
    db_session.commit()
    
    response = auth_client.get(f"/api/outputs/{output_id}")
    assert response.status_code == 200
    assert response.json()["id"] == output_id
