"""
Tests for PhoWhisperClient
Run with: pytest app/tests/test_phowhisper.py -v
"""

import pytest
import torch
from pathlib import Path
from app.core.models.phowhisper_model import PhoWhisperClient


@pytest.fixture
def sample_audio():
    """Return path to sample audio file"""
    return "app/audio/sample.wav"


@pytest.fixture
def phowhisper_client():
    """Create PhoWhisperClient instance"""
    return PhoWhisperClient()


class TestPhoWhisperClient:
    """Test suite for PhoWhisperClient"""
    
    def test_initialization(self):
        """Test client initialization"""
        client = PhoWhisperClient()
        assert client.model_name == "vinai/PhoWhisper-large"
        assert client.device in ["cuda:0", "cpu"]
        assert client.chunk_duration == 30
        assert not client._is_loaded
        
    def test_custom_chunk_duration(self):
        """Test custom chunk duration"""
        client = PhoWhisperClient(chunk_duration=20)
        assert client.chunk_duration == 20
        
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_cuda_detection(self):
        """Test CUDA device detection"""
        client = PhoWhisperClient()
        assert client.device == "cuda:0"
        
    def test_load_model(self, phowhisper_client):
        """Test model loading"""
        load_time = phowhisper_client.load()
        assert load_time > 0
        assert phowhisper_client._is_loaded
        assert phowhisper_client.pipe is not None
        
    @pytest.mark.skipif(not Path("app/audio/sample.wav").exists(), reason="Sample audio not found")
    def test_transcribe(self, phowhisper_client, sample_audio):
        """Test transcription with chunking"""
        transcript, processing_time = phowhisper_client.transcribe(sample_audio)
        
        assert isinstance(transcript, str)
        assert len(transcript) > 0
        assert processing_time > 0
        
    def test_save_result(self, phowhisper_client, tmp_path):
        """Test saving transcript"""
        test_transcript = "Đây là một bản ghi âm tiếng Việt."
        output_path = tmp_path / "test_output.txt"
        
        phowhisper_client.save_result(test_transcript, str(output_path))
        
        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == test_transcript
        
    def test_repr(self, phowhisper_client):
        """Test string representation"""
        repr_str = repr(phowhisper_client)
        assert "PhoWhisperClient" in repr_str
        assert "not loaded" in repr_str
        assert "30s" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
