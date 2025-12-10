"""
Phase 2: Advanced Features - Test Suite
Tests all Phase 2 components
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("="*80)
print("PHASE 2: ADVANCED FEATURES - TEST SUITE")
print("="*80)
print()


def test_imports():
    """Test if all required packages are installed"""
    print("🧪 Testing imports...")
    
    try:
        import sentence_transformers
        print(f"  ✅ sentence-transformers: {sentence_transformers.__version__}")
    except ImportError as e:
        print(f"  ❌ sentence-transformers: {e}")
        return False
    
    try:
        import torch
        print(f"  ✅ torch: {torch.__version__}")
        print(f"     CUDA available: {torch.cuda.is_available()}")
    except ImportError as e:
        print(f"  ❌ torch: {e}")
        return False
    
    try:
        from PIL import Image
        print(f"  ✅ Pillow: OK")
    except ImportError as e:
        print(f"  ❌ Pillow: {e}")
        return False
    
    try:
        import numpy
        print(f"  ✅ numpy: {numpy.__version__}")
    except ImportError as e:
        print(f"  ❌ numpy: {e}")
        return False
    
    print()
    return True


def test_multimodal_handler():
    """Test multimodal handler"""
    print("🧪 Testing Multimodal Handler...")
    
    try:
        from src.handlers.multimodal_handler import MultimodalHandler
        
        # Initialize handler
        handler = MultimodalHandler()
        print("  ✅ Handler initialized")
        
        # Get capabilities
        capabilities = handler.get_capabilities()
        print(f"  ✅ Capabilities loaded:")
        print(f"     - Vision: {capabilities['vision']['enabled']}")
        print(f"     - Audio: {capabilities['audio']['enabled']}")
        print(f"     - Document: {capabilities['document']['enabled']}")
        print(f"     - Multimodal: {capabilities['multimodal']['enabled']}")
        
        # Test vision models
        if capabilities['vision']['enabled']:
            models = capabilities['vision']['models']
            print(f"     - Vision models: {', '.join(models)}")
        
        print()
        return True
        
    except Exception as e:
        print(f"  ❌ Multimodal handler test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_advanced_image_gen():
    """Test advanced image generator"""
    print("🧪 Testing Advanced Image Generator...")
    
    try:
        from src.handlers.advanced_image_gen import AdvancedImageGenerator
        
        # Initialize generator
        generator = AdvancedImageGenerator()
        print(f"  ✅ Generator initialized")
        print(f"     SD API available: {generator.is_available}")
        
        # Get capabilities
        capabilities = generator.get_capabilities()
        print(f"  ✅ Capabilities loaded:")
        print(f"     - ControlNet: {capabilities['controlnet']['enabled']}")
        
        if capabilities['controlnet']['enabled']:
            print(f"       Models: {len(capabilities['controlnet']['models'])} available")
        
        print(f"     - Upscaling: {capabilities['upscaling']['enabled']}")
        
        if capabilities['upscaling']['enabled']:
            print(f"       Upscalers: {', '.join(capabilities['upscaling']['upscalers'][:3])}...")
        
        print(f"     - Inpainting: {capabilities['inpainting']['enabled']}")
        print(f"     - Outpainting: {capabilities['outpainting']['enabled']}")
        print(f"     - Style Transfer: {capabilities['style_transfer']['enabled']}")
        print(f"     - LoRA Mixing: {capabilities['lora_mixing']['enabled']}")
        
        print()
        return True
        
    except Exception as e:
        print(f"  ❌ Advanced image generator test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_conversation_manager():
    """Test conversation manager"""
    print("🧪 Testing Conversation Manager...")
    
    try:
        from src.utils.conversation_manager import ConversationManager
        
        # Initialize manager
        manager = ConversationManager()
        print("  ✅ Manager initialized")
        
        # Get statistics
        stats = manager.get_statistics()
        print(f"  ✅ Statistics loaded:")
        print(f"     - Total conversations: {stats['total_conversations']}")
        print(f"     - Total messages: {stats['total_messages']}")
        print(f"     - Total tags: {stats['total_tags']}")
        print(f"     - Embeddings enabled: {stats['embeddings_enabled']}")
        
        # Test create conversation
        conv_id = manager.create_conversation(
            title="Test Conversation",
            tags=["test", "phase2"]
        )
        print(f"  ✅ Created test conversation: {conv_id}")
        
        # Test add message
        success = manager.add_message(
            conv_id,
            "user",
            "This is a test message"
        )
        print(f"  ✅ Added message: {success}")
        
        # Test full-text search
        results = manager.full_text_search("test", limit=5)
        print(f"  ✅ Full-text search: {len(results)} results")
        
        # Test semantic search (if embeddings enabled)
        if stats['embeddings_enabled']:
            results = manager.semantic_search("test message", top_k=5)
            print(f"  ✅ Semantic search: {len(results)} results")
        else:
            print(f"  ⚠️  Semantic search: Disabled (embeddings not available)")
        
        # Test export
        markdown = manager.export_conversation(conv_id, format="markdown")
        print(f"  ✅ Export markdown: {len(markdown)} characters")
        
        # Cleanup
        manager.delete_conversation(conv_id)
        print(f"  ✅ Deleted test conversation")
        
        print()
        return True
        
    except Exception as e:
        print(f"  ❌ Conversation manager test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_integration():
    """Test integration between components"""
    print("🧪 Testing Integration...")
    
    try:
        from src.handlers.multimodal_handler import get_multimodal_handler
        from src.handlers.advanced_image_gen import get_advanced_image_generator
        from src.utils.conversation_manager import get_conversation_manager
        
        # Get singleton instances
        multimodal = get_multimodal_handler()
        image_gen = get_advanced_image_generator()
        conv_manager = get_conversation_manager()
        
        print("  ✅ All singleton instances created")
        
        # Test cross-component functionality
        # Create conversation with multimodal metadata
        conv_id = conv_manager.create_conversation(
            title="Multimodal Test",
            tags=["multimodal", "test"],
            metadata={
                'has_images': True,
                'has_audio': False,
                'has_documents': False
            }
        )
        print("  ✅ Created multimodal conversation")
        
        # Cleanup
        conv_manager.delete_conversation(conv_id)
        print("  ✅ Integration test complete")
        
        print()
        return True
        
    except Exception as e:
        print(f"  ❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def main():
    """Run all tests"""
    
    results = {
        'imports': test_imports(),
        'multimodal': test_multimodal_handler(),
        'image_gen': test_advanced_image_gen(),
        'conversation': test_conversation_manager(),
        'integration': test_integration()
    }
    
    # Summary
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.upper():<20} {status}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print()
        print("🎉 ALL TESTS PASSED!")
        print()
        print("Phase 2 backend components are ready!")
        print("Next: Implement frontend components")
        return 0
    else:
        print()
        print("⚠️  SOME TESTS FAILED")
        print()
        print("Please fix the failing components before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
