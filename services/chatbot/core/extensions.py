"""
Extensions module - MongoDB, cache, logger, rate limiter setup
"""
import os
import sys
import logging
import importlib.util
from pathlib import Path

from .config import CHATBOT_DIR, ROOT_DIR

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Enable werkzeug logging
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.INFO)


def _load_root_config_module(module_name, file_name):
    """Load a module from root config directory"""
    root_path = str(ROOT_DIR)
    chatbot_path = str(CHATBOT_DIR)
    
    original_path_0 = sys.path[0] if sys.path else None
    
    if root_path in sys.path:
        sys.path.remove(root_path)
    sys.path.insert(0, root_path)
    
    try:
        module_path = ROOT_DIR / 'config' / file_name
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if root_path in sys.path:
            sys.path.remove(root_path)
        if chatbot_path in sys.path:
            sys.path.remove(chatbot_path)
        sys.path.insert(0, chatbot_path)
        if root_path not in sys.path:
            sys.path.insert(1, root_path)


# Load rate limiter
_rate_limiter_module = _load_root_config_module('root_rate_limiter', 'rate_limiter.py')
# NOTE: Gemini đã bị xóa - chỉ sử dụng GROK
wait_for_openai_rate_limit = _rate_limiter_module.wait_for_openai_rate_limit
get_rate_limit_stats = _rate_limiter_module.get_rate_limit_stats

# Load response cache
_response_cache_module = _load_root_config_module('root_response_cache', 'response_cache.py')
get_cached_response = _response_cache_module.get_cached_response
cache_response = _response_cache_module.cache_response
get_all_cache_stats = _response_cache_module.get_all_cache_stats

# Load monitor
_monitor_module = _load_root_config_module('root_monitor', 'monitor.py')
register_monitor = _monitor_module.register_monitor


# Load MongoDB config
def _load_mongodb():
    """Load MongoDB configuration"""
    mongodb_config_path = CHATBOT_DIR / 'config' / 'mongodb_config.py'
    spec = importlib.util.spec_from_file_location("mongodb_config_chatbot", mongodb_config_path)
    mongodb_config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mongodb_config_module)
    return mongodb_config_module.mongodb_client, mongodb_config_module.get_db


def _load_mongodb_helpers():
    """Load MongoDB helpers"""
    mongodb_helpers_path = CHATBOT_DIR / 'config' / 'mongodb_helpers.py'
    spec = importlib.util.spec_from_file_location("mongodb_helpers_chatbot", mongodb_helpers_path)
    mongodb_helpers_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mongodb_helpers_module)
    return mongodb_helpers_module


mongodb_client, get_db = _load_mongodb()
_helpers = _load_mongodb_helpers()
ConversationDB = _helpers.ConversationDB
MessageDB = _helpers.MessageDB
MemoryDB = _helpers.MemoryDB
FileDB = _helpers.FileDB
UserSettingsDB = _helpers.UserSettingsDB

# Initialize MongoDB
MONGODB_ENABLED = False
try:
    mongodb_client.connect()
    MONGODB_ENABLED = True
    logger.info("✅ MongoDB connection established")
except Exception as e:
    logger.warning(f"⚠️ MongoDB not available: {e}")


# Performance modules
PERFORMANCE_ENABLED = False
cache = None
db = None
streaming = None

try:
    from src.utils.cache_manager import get_cache_manager
    from src.utils.database_manager import get_database_manager
    from src.utils.streaming_handler import StreamingHandler
    PERFORMANCE_ENABLED = True
    cache = get_cache_manager()
    db = get_database_manager()
    streaming = StreamingHandler()
    logger.info("✅ Performance optimization modules loaded")
except Exception as e:
    logger.warning(f"⚠️ Performance modules not available: {e}")


# ImgBB uploader
CLOUD_UPLOAD_ENABLED = False
try:
    from src.utils.imgbb_uploader import ImgBBUploader, upload_to_imgbb
    CLOUD_UPLOAD_ENABLED = True
    logger.info("✅ ImgBB uploader loaded")
except ImportError as e:
    logger.warning(f"⚠️ ImgBB uploader not available: {e}")


# Local models
LOCALMODELS_AVAILABLE = False
model_loader = None

try:
    from src.utils.local_model_loader import model_loader as _model_loader
    model_loader = _model_loader
    LOCALMODELS_AVAILABLE = True
    logger.info("✅ Local model loader imported")
except Exception as e:
    logger.warning(f"⚠️ Local models not available: {e}")
