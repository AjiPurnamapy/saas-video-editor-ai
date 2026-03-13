import os
import pytest
from app.services.storage_service import StorageService, LocalStorageBackend

def test_local_storage_backend(tmp_path):
    backend = LocalStorageBackend()
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")
    
    # file_exists
    assert backend.file_exists(str(test_file))
    assert not backend.file_exists("/tmp/nonexistent_file_123")
    
    # read_file
    assert backend.read_file(str(test_file)) == b"hello"
    
    # delete
    backend.delete_file(str(test_file))
    assert not test_file.exists()
    
    # delete non-existent should not raise
    backend.delete_file("/tmp/nonexistent")

def test_storage_service_default():
    service = StorageService()
    # It should function as a LocalStorageBackend by default
    assert service.file_exists("/some/nonexistent/path") is False
