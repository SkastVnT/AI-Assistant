"""
Tests for WhisperClient
Run with: pytest app/tests/test_whisper.py -v
"""

import pytest
import torch
from pathlib import Path
from app.core.models.whisper_model import WhisperClient


@pytest.fixture
def sample_audio():
    """Return path to sample audio file"""
    # Use a sample from your project or create a test fixture
    return "app/audio/sample.wav"  # Update with actual path


@pytest.fixture
def whisper_client():
    """Create WhisperClient instance"""
    return WhisperClient(model_name="base")  # Use smaller model for faster tests


class TestWhisperClient:
    """Test suite for WhisperClient"""
    
    def test_initialization(self):
        """Test client initialization"""
        client = WhisperClient()
        assert client.model_name == "large-v3"
        assert client.device in ["cuda", "cpu"]
        assert not client._is_loaded
        
    def test_custom_initialization(self):
        """Test client with custom parameters"""
        client = WhisperClient(
            model_name="base",
            device="cpu",
            compute_type="int8"
        )
        assert client.model_name == "base"
        assert client.device == "cpu"
        assert client.compute_type == "int8"
        
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_cuda_detection(self):
        """Test CUDA device detection"""
        client = WhisperClient()
        assert client.device == "cuda"
        assert client.compute_type == "float16"
        
    def test_load_model(self, whisper_client):
        """Test model loading"""
        load_time = whisper_client.load()
        assert load_time > 0
        assert whisper_client._is_loaded
        assert whisper_client.model is not None
        
    @pytest.mark.skipif(not Path("app/audio/sample.wav").exists(), reason="Sample audio not found")
    def test_transcribe(self, whisper_client, sample_audio):
        """Test transcription"""
        transcript, processing_time = whisper_client.transcribe(sample_audio)
        
        assert isinstance(transcript, str)
        assert len(transcript) > 0
        assert processing_time > 0
        
    def test_save_result(self, whisper_client, tmp_path):
        """Test saving transcript"""
        test_transcript = "This is a test transcript."
        output_path = tmp_path / "test_output.txt"
        
        whisper_client.save_result(test_transcript, str(output_path))
        
        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == test_transcript
        
    def test_repr(self, whisper_client):
        """Test string representation"""
        repr_str = repr(whisper_client)
        assert "WhisperClient" in repr_str
        assert "not loaded" in repr_str
        
        whisper_client.load()
        repr_str = repr(whisper_client)
        assert "loaded" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
