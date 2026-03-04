"""
Model Health & Status routes — /api/models/*
Provides real-time model availability, health checks, and performance stats.
"""
import json
import time
import os
import sys
from datetime import datetime
from pathlib import Path
from flask import Blueprint, jsonify, request
import logging

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.config import (
    OPENAI_API_KEY, DEEPSEEK_API_KEY, GROK_API_KEY,
    QWEN_API_KEY, HUGGINGFACE_API_KEY,
    OPENROUTER_API_KEY, STEPFUN_API_KEY, GEMINI_API_KEYS,
    get_system_prompts
)
from core.extensions import logger

models_bp = Blueprint('models', __name__)

# ============================================================
# MODEL CATALOG — Complete info for all supported models
# ============================================================

MODEL_CATALOG = {
    'grok': {
        'name': 'Grok-3',
        'provider': 'xAI',
        'model_id': 'grok-3',
        'context_window': 128000,
        'pricing': 'Paid — $5/$15 per 1M tokens',
        'supports_streaming': True,
        'supports_deep_thinking': True,
        'description': 'Powerful conversational AI by xAI with real-time knowledge',
        'icon': '🤖',
        'tier': 'premium',
        'languages': ['en', 'vi', 'multi'],
        'strengths': ['Conversation', 'Analysis', 'Creative', 'NSFW-capable'],
    },
    'openai': {
        'name': 'GPT-4o Mini',
        'provider': 'OpenAI',
        'model_id': 'gpt-4o-mini',
        'context_window': 128000,
        'pricing': '$0.15/$0.60 per 1M tokens',
        'supports_streaming': True,
        'supports_deep_thinking': True,
        'description': 'Fast and affordable GPT model for everyday tasks',
        'icon': '🧠',
        'tier': 'standard',
        'languages': ['en', 'vi', 'multi'],
        'strengths': ['General', 'Code', 'Analysis', 'Creative'],
    },
    'deepseek': {
        'name': 'DeepSeek Chat',
        'provider': 'DeepSeek',
        'model_id': 'deepseek-chat',
        'context_window': 64000,
        'pricing': '$0.14/$0.28 per 1M tokens',
        'supports_streaming': True,
        'supports_deep_thinking': True,
        'description': 'Cost-effective model with strong coding abilities',
        'icon': '🔍',
        'tier': 'standard',
        'languages': ['en', 'zh', 'vi', 'multi'],
        'strengths': ['Code', 'Math', 'Analysis', 'Reasoning'],
    },
    'deepseek-reasoner': {
        'name': 'DeepSeek R1',
        'provider': 'DeepSeek',
        'model_id': 'deepseek-reasoner',
        'context_window': 64000,
        'pricing': '$0.55/$2.19 per 1M tokens',
        'supports_streaming': True,
        'supports_deep_thinking': True,
        'description': 'Advanced reasoning model with chain-of-thought',
        'icon': '🧪',
        'tier': 'premium',
        'languages': ['en', 'zh', 'vi', 'multi'],
        'strengths': ['Reasoning', 'Math', 'Code', 'Logic'],
    },
    'gemini': {
        'name': 'Gemini 2.0 Flash',
        'provider': 'Google',
        'model_id': 'gemini-2.0-flash',
        'context_window': 1000000,
        'pricing': 'FREE tier available',
        'supports_streaming': True,
        'supports_deep_thinking': True,
        'description': 'Google\'s fastest multimodal model with 1M context',
        'icon': '💎',
        'tier': 'free',
        'languages': ['en', 'vi', 'multi'],
        'strengths': ['Multimodal', 'Long context', 'Creative', 'Speed'],
    },
    'step-flash': {
        'name': 'Step-3.5 Flash',
        'provider': 'StepFun (via OpenRouter)',
        'model_id': 'stepfun/step-3.5-flash:free',
        'context_window': 128000,
        'pricing': 'FREE via OpenRouter',
        'supports_streaming': True,
        'supports_deep_thinking': True,
        'description': '196B MoE (11B active) — Free powerful Chinese AI model',
        'icon': '⚡',
        'tier': 'free',
        'languages': ['en', 'zh', 'vi', 'multi'],
        'strengths': ['Chinese', 'Reasoning', 'Code', 'Multilingual'],
    },
    'stepfun': {
        'name': 'Step-2-16K',
        'provider': 'StepFun Direct',
        'model_id': 'step-2-16k',
        'context_window': 16000,
        'pricing': 'Paid — requires StepFun balance',
        'supports_streaming': True,
        'supports_deep_thinking': True,
        'description': 'StepFun\'s direct API model',
        'icon': '🚀',
        'tier': 'standard',
        'languages': ['en', 'zh', 'vi'],
        'strengths': ['Chinese', 'General', 'Code'],
    },
    'qwen': {
        'name': 'Qwen Turbo',
        'provider': 'Alibaba Cloud',
        'model_id': 'qwen-turbo',
        'context_window': 8000,
        'pricing': 'Cheap — $0.001/$0.002 per 1K tokens',
        'supports_streaming': True,
        'supports_deep_thinking': False,
        'description': 'Fast and affordable Chinese AI model',
        'icon': '🌙',
        'tier': 'economy',
        'languages': ['en', 'zh', 'vi'],
        'strengths': ['Chinese', 'Speed', 'General'],
    },
    'bloomvn': {
        'name': 'BloomVN-8B',
        'provider': 'HuggingFace',
        'model_id': 'BlossomsAI/BloomVN-8B-chat',
        'context_window': 4000,
        'pricing': 'FREE via HuggingFace Inference',
        'supports_streaming': False,
        'supports_deep_thinking': False,
        'description': 'Vietnamese-focused open-source model',
        'icon': '🌸',
        'tier': 'free',
        'languages': ['vi', 'en'],
        'strengths': ['Vietnamese', 'General'],
    },
}


def _check_key_configured(model_name: str) -> bool:
    """Check if API key is configured for a model"""
    key_map = {
        'grok': bool(GROK_API_KEY),
        'openai': bool(OPENAI_API_KEY),
        'deepseek': bool(DEEPSEEK_API_KEY),
        'deepseek-reasoner': bool(DEEPSEEK_API_KEY),
        'gemini': bool(GEMINI_API_KEYS),
        'step-flash': bool(OPENROUTER_API_KEY),
        'stepfun': bool(STEPFUN_API_KEY),
        'qwen': bool(QWEN_API_KEY),
        'bloomvn': bool(HUGGINGFACE_API_KEY),
    }
    return key_map.get(model_name, False)


@models_bp.route('/api/models', methods=['GET'])
def list_models():
    """
    List all available models with their status.
    Query params:
        - tier: filter by tier (free, economy, standard, premium)
        - available_only: only show models with configured keys (default: false)
    """
    tier_filter = request.args.get('tier')
    available_only = request.args.get('available_only', 'false').lower() == 'true'
    
    models = []
    for name, info in MODEL_CATALOG.items():
        configured = _check_key_configured(name)
        
        if available_only and not configured:
            continue
        
        if tier_filter and info.get('tier') != tier_filter:
            continue
        
        models.append({
            'id': name,
            **info,
            'configured': configured,
            'available': configured,
        })
    
    # Sort: available first, then by tier (free > economy > standard > premium)
    tier_order = {'free': 0, 'economy': 1, 'standard': 2, 'premium': 3}
    models.sort(key=lambda m: (0 if m['available'] else 1, tier_order.get(m.get('tier', 'standard'), 2)))
    
    return jsonify({
        'models': models,
        'total': len(models),
        'available_count': sum(1 for m in models if m['available']),
        'tiers': list(set(m.get('tier', 'standard') for m in models)),
    })


@models_bp.route('/api/models/<model_id>', methods=['GET'])
def get_model_info(model_id):
    """Get detailed info about a specific model"""
    if model_id not in MODEL_CATALOG:
        return jsonify({'error': f'Model {model_id} not found'}), 404
    
    info = MODEL_CATALOG[model_id]
    configured = _check_key_configured(model_id)
    
    return jsonify({
        'id': model_id,
        **info,
        'configured': configured,
        'available': configured,
    })


@models_bp.route('/api/models/health', methods=['GET'])
def models_health():
    """
    Quick health check for all configured models.
    Returns status without actually calling APIs.
    """
    health = {}
    for name in MODEL_CATALOG:
        configured = _check_key_configured(name)
        health[name] = {
            'configured': configured,
            'status': 'ready' if configured else 'no_api_key',
            'icon': MODEL_CATALOG[name]['icon'],
            'name': MODEL_CATALOG[name]['name'],
        }
    
    available_count = sum(1 for h in health.values() if h['status'] == 'ready')
    
    return jsonify({
        'health': health,
        'summary': {
            'total': len(health),
            'available': available_count,
            'unavailable': len(health) - available_count,
        },
        'timestamp': datetime.now().isoformat()
    })


@models_bp.route('/api/models/contexts', methods=['GET'])
def list_contexts():
    """List all available conversation contexts/personas"""
    language = request.args.get('language', 'vi')
    prompts = get_system_prompts(language)
    
    context_info = {
        'psychological': {
            'name': 'Tâm lý' if language == 'vi' else 'Psychology',
            'icon': '🧘',
            'description': 'Tư vấn tâm lý, hỗ trợ cảm xúc' if language == 'vi' else 'Psychological counseling, emotional support',
        },
        'lifestyle': {
            'name': 'Lối sống' if language == 'vi' else 'Lifestyle',
            'icon': '🌟',
            'description': 'Tư vấn lối sống, phát triển bản thân' if language == 'vi' else 'Lifestyle advice, personal development',
        },
        'casual': {
            'name': 'Thân mật' if language == 'vi' else 'Casual',
            'icon': '💬',
            'description': 'Trò chuyện thân thiện, đa chủ đề' if language == 'vi' else 'Friendly chat, any topic',
        },
        'programming': {
            'name': 'Lập trình' if language == 'vi' else 'Programming',
            'icon': '💻',
            'description': 'Coding, debug, kiến trúc phần mềm' if language == 'vi' else 'Coding, debug, software architecture',
        },
        'creative': {
            'name': 'Sáng tạo' if language == 'vi' else 'Creative',
            'icon': '🎨',
            'description': 'Viết lách, brainstorm, thiết kế' if language == 'vi' else 'Writing, brainstorming, design',
        },
        'research': {
            'name': 'Nghiên cứu' if language == 'vi' else 'Research',
            'icon': '🔬',
            'description': 'Phân tích chuyên sâu, tổng hợp thông tin' if language == 'vi' else 'Deep analysis, information synthesis',
        },
    }
    
    contexts = []
    for key, info in context_info.items():
        if key in prompts:
            contexts.append({
                'id': key,
                **info,
                'available': True,
            })
    
    return jsonify({'contexts': contexts})


@models_bp.route('/api/models/recommend', methods=['POST'])
def recommend_model():
    """
    Recommend the best model for a given use case.
    Request body:
        - task: Description of the task
        - language: Preferred language
        - budget: 'free', 'cheap', 'any'
        - need_streaming: boolean
    """
    data = request.json or {}
    task = data.get('task', '').lower()
    budget = data.get('budget', 'any')
    need_streaming = data.get('need_streaming', True)
    
    scores = {}
    
    for name, info in MODEL_CATALOG.items():
        if not _check_key_configured(name):
            continue
        
        if need_streaming and not info['supports_streaming']:
            continue
            
        score = 50  # Base score
        
        # Budget preference
        if budget == 'free':
            if info['tier'] == 'free':
                score += 30
            elif info['tier'] == 'economy':
                score += 10
            else:
                score -= 20
        elif budget == 'cheap':
            if info['tier'] in ['free', 'economy']:
                score += 20
            elif info['tier'] == 'standard':
                score += 10
        
        # Task matching
        strengths = [s.lower() for s in info.get('strengths', [])]
        if 'code' in task or 'programming' in task or 'debug' in task:
            if 'code' in strengths:
                score += 25
        if 'creative' in task or 'write' in task or 'story' in task:
            if 'creative' in strengths:
                score += 25
        if 'reason' in task or 'math' in task or 'logic' in task:
            if 'reasoning' in strengths:
                score += 25
        if 'vietnamese' in task or 'tiếng việt' in task:
            if 'vietnamese' in strengths:
                score += 30
        if 'chinese' in task or 'tiếng trung' in task:
            if 'chinese' in strengths:
                score += 30
        
        # Context window bonus for long tasks
        if 'long' in task or 'document' in task:
            score += min(info['context_window'] / 10000, 20)
        
        scores[name] = score
    
    # Sort by score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    recommendations = []
    for name, score in ranked[:3]:
        info = MODEL_CATALOG[name]
        recommendations.append({
            'id': name,
            'name': info['name'],
            'icon': info['icon'],
            'provider': info['provider'],
            'score': round(score),
            'pricing': info['pricing'],
            'reason': f"Best for: {', '.join(info.get('strengths', [])[:3])}",
        })
    
    return jsonify({
        'recommendations': recommendations,
        'default': recommendations[0]['id'] if recommendations else 'grok',
    })
