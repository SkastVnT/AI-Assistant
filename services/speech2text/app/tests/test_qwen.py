"""
Tests for QwenClient
Run with: pytest app/tests/test_qwen.py -v
"""

import pytest
import torch
from pathlib import Path
from app.core.models.qwen_model import QwenClient


@pytest.fixture
def qwen_client():
    """Create QwenClient instance"""
    return QwenClient()


class TestQwenClient:
    """Test suite for QwenClient"""
    
    def test_initialization(self):
        """Test client initialization"""
        client = QwenClient()
        assert client.model_name == "Qwen/Qwen2.5-1.5B-Instruct"
        assert client.device == "auto"
        assert not client._is_loaded
        
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_dtype_detection(self):
        """Test dtype detection with CUDA"""
        client = QwenClient()
        assert client.torch_dtype == torch.float16
        
    def test_load_model(self, qwen_client):
        """Test model loading"""
        load_time = qwen_client.load()
        assert load_time > 0
        assert qwen_client._is_loaded
        assert qwen_client.model is not None
        assert qwen_client.tokenizer is not None
        
    def test_generate_simple(self, qwen_client):
        """Test simple text generation"""
        prompt = """<|im_start|>system
Báº¡n lÃ  trá»£ lÃ½ AI.<|im_end|>
<|im_start|>user
Xin chÃ o, báº¡n khá»e khÃ´ng?<|im_end|>
<|im_start|>assistant"""
        
        qwen_client.load()
        response, gen_time = qwen_client.generate(
            prompt,
            max_new_tokens=100,
            temperature=0.3
        )
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert gen_time > 0
        
    def test_fuse_transcripts(self, qwen_client):
        """Test transcript fusion"""
        whisper_text = "Xin chÃ o tÃ´i muá»‘n há»i vá» Ä‘Æ¡n hÃ ng"
        phowhisper_text = "Xin chÃ o, tÃ´i muá»‘n há»i vá» Ä‘Æ¡n hÃ ng cá»§a tÃ´i"
        
        qwen_client.load()
        fused_text, fusion_time = qwen_client.fuse_transcripts(
            whisper_text,
            phowhisper_text,
            max_new_tokens=200
        )
        
        assert isinstance(fused_text, str)
        assert len(fused_text) > 0
        assert fusion_time > 0
        
    def test_save_result(self, qwen_client, tmp_path):
        """Test saving generated text"""
        test_text = "KhÃ¡ch hÃ ng: Xin chÃ o.\nNhÃ¢n viÃªn: Dáº¡, chÃ o anh."
        output_path = tmp_path / "test_fusion.txt"
        
        qwen_client.save_result(test_text, str(output_path))
        
        assert output_path.exists()
        assert output_path.read_text(encoding="utf-8") == test_text
        
    def test_repr(self, qwen_client):
        """Test string representation"""
        repr_str = repr(qwen_client)
        assert "QwenClient" in repr_str
        assert "not loaded" in repr_str
        
        qwen_client.load()
        repr_str = repr(qwen_client)
        assert "loaded" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
