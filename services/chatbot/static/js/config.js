/**
 * Configuration Constants
 * Central configuration for the ChatBot application
 */

export const CONFIG = {
    // Model names mapping
    MODEL_NAMES: {
        'gemini': 'Gemini',
        'openai': 'GPT-4o-mini',
        'deepseek': 'DeepSeek',
        'qwen': 'Qwen1.5b',
        'bloomvn': 'BloomVN-8B API',
        'bloomvn-local': 'BloomVN-8B Local',
        'qwen1.5-local': 'Qwen1.5 Local',
        'qwen2.5-local': 'Qwen2.5-14B Local'
    },

    // Context names mapping
    CONTEXT_NAMES: {
        'casual': 'Trò chuyện vui vẻ',
        'psychological': 'Tâm lý - Tâm sự',
        'lifestyle': 'Giải pháp đời sống',
        'programming': '💻 Hỗ trợ lập trình'
    },

    // Storage settings
    STORAGE: {
        MAX_SIZE_MB: 200,
        COMPRESSION_QUALITY: 0.6,
        MAX_IMAGE_SIZE: 800,
        SESSION_KEEP_COUNT: 5
    },

    // Image generation settings
    IMAGE_GEN: {
        DEFAULT_WIDTH: 512,
        DEFAULT_HEIGHT: 512,
        DEFAULT_STEPS: 20,
        DEFAULT_CFG_SCALE: 7.0,
        DEFAULT_SAMPLER: 'Euler a',
        MAX_WIDTH: 2048,
        MAX_HEIGHT: 2048
    },

    // API endpoints (relative to base URL)
    API_ENDPOINTS: {
        CHAT: '/chat',
        LOCAL_MODELS_STATUS: '/api/local-models-status',
        SD_STATUS: '/sd-api/status',
        SD_MODELS: '/sd-api/models',
        SD_SAMPLERS: '/sd-api/samplers',
        SD_LORAS: '/sd-api/loras',
        SD_VAES: '/sd-api/vaes',
        SD_TEXT2IMG: '/sd-api/text2img',
        SD_IMG2IMG: '/sd-api/img2img',
        SD_INTERROGATE: '/sd-api/interrogate',
        MEMORY_LIST: '/api/memory/list',
        MEMORY_SAVE: '/api/memory/save',
        MEMORY_DELETE: '/api/memory/delete',
        MEMORY_LOAD: '/api/memory/load',
        STORAGE_IMAGES: '/api/storage/images',
        STORAGE_DELETE: '/api/storage/delete'
    },

    // Feature extraction settings
    FEATURE_EXTRACTION: {
        MODELS: ['deepdanbooru', 'clip', 'wd14'],
        CATEGORY_NAMES: {
            'hair': '💇 Tóc',
            'eyes': '👁️ Mắt',
            'mouth': '👄 Miệng',
            'face': '😊 Khuôn mặt',
            'accessories': '👑 Phụ kiện',
            'clothing': '👔 Quần áo',
            'body': '🧍 Cơ thể',
            'pose': '🤸 Tư thế',
            'background': '🏞️ Background',
            'style': '🎨 Style',
            'other': '📦 Khác'
        }
    },

    // File upload settings
    FILE_UPLOAD: {
        ALLOWED_TYPES: ['image/*', 'text/*', 'application/pdf'],
        MAX_FILE_SIZE_MB: 10
    },

    // UI settings
    UI: {
        MOBILE_BREAKPOINT: 768,
        MESSAGE_INPUT_MAX_HEIGHT: 200,
        AUTO_SCROLL_DELAY: 100,
        TOAST_DURATION: 2000
    }
};

export default CONFIG;
