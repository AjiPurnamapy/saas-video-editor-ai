import os
import shutil
import pytest
from app.utils.file_utils import (
    ensure_directory,
    generate_unique_filename,
    get_file_extension,
    get_file_size_mb,
    cleanup_temp_files,
    create_temp_directory,
)

def test_ensure_directory(tmp_path):
    new_dir = os.path.join(tmp_path, "new_folder")
    assert not os.path.exists(new_dir)
    
    result = ensure_directory(new_dir)
    assert os.path.exists(result)
    assert os.path.isdir(result)

def test_generate_unique_filename():
    name1 = generate_unique_filename("test.mp4")
    name2 = generate_unique_filename("test.mp4")
    
    assert name1.endswith(".mp4")
    assert name1 != name2
    
    name3 = generate_unique_filename("movie.MOV", prefix="clip")
    assert name3.startswith("clip_")
    assert name3.endswith(".mov")

def test_get_file_extension():
    assert get_file_extension("audio.WAV") == ".wav"
    assert get_file_extension("no_ext") == ""
    assert get_file_extension(".hidden.mp4") == ".mp4"

def test_cleanup_temp_files(tmp_path):
    file1 = tmp_path / "f1.txt"
    file2 = tmp_path / "f2.txt"
    dir1 = tmp_path / "d1"
    
    file1.write_text("test")
    file2.write_text("test")
    dir1.mkdir()
    (dir1 / "inside.txt").write_text("test")
    
    assert file1.exists()
    assert file2.exists()
    assert dir1.exists()
    
    # Clean file1 and dir1, leave file2
    cleanup_temp_files(str(file1), str(dir1))
    
    assert not file1.exists()
    assert not dir1.exists()
    assert file2.exists()

def test_cleanup_silent_fail():
    # Should not raise exception for non-existent files
    cleanup_temp_files("/tmp/does_not_exist_1234.tmp")

def test_create_temp_directory(tmp_path):
    temp_dir = create_temp_directory(base_dir=str(tmp_path))
    assert os.path.exists(temp_dir)
    assert os.path.isdir(temp_dir)
    assert os.path.basename(temp_dir).startswith("aive_")
