"""
AI Assistant Hub - Main Gateway (Refactored)
Professional structure following Generative AI template
"""

from flask import Flask, render_template, jsonify
from flask_cors import CORS
import sys
from pathlib import Path

# Add project root to path (go up 2 levels: hub-gateway -> services -> root)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.model_config import HubConfig
from config.logging_config import setup_logging
from handlers.error_handler import (
    HubException, 
    handle_hub_exception, 
    handle_generic_exception,
    error_handler
)
from utils.rate_limiter import rate_limit

# Initialize Flask app
app = Flask(__name__, template_folder='../templates')
app.config.from_object(HubConfig)
CORS(app, origins=HubConfig.CORS_ORIGINS)

# Setup logging
logger = setup_logging(
    log_level=HubConfig.LOG_LEVEL,
    log_file=HubConfig.LOG_FILE
)

# Register error handlers
app.register_error_handler(HubException, handle_hub_exception)
app.register_error_handler(Exception, handle_generic_exception)


@app.route('/')
@error_handler
def index():
    """Home page - Gateway dashboard"""
    logger.info("Serving hub gateway homepage")
    services = HubConfig.get_all_services()
    
    # Convert ServiceConfig objects to dicts for template
    services_dict = {
        key: {
            'name': service.name,
            'description': service.description,
            'icon': service.icon,
            'port': service.port,
            'url': service.url,
            'color': service.color,
            'features': service.features,
            'status': 'available'
        }
        for key, service in services.items()
    }
    
    return render_template('index.html', services=services_dict)


@app.route('/api/services')
@error_handler
@rate_limit(max_requests=100, window_seconds=60)
def get_services():
    """Get all services information"""
    logger.debug("API request: get_services")
    services = HubConfig.get_all_services()
    
    services_dict = {
        key: {
            'name': service.name,
            'description': service.description,
            'icon': service.icon,
            'port': service.port,
            'url': service.url,
            'features': service.features
        }
        for key, service in services.items()
    }
    
    return jsonify(services_dict)


@app.route('/api/services/<service_name>')
@error_handler
@rate_limit(max_requests=200, window_seconds=60)
def get_service(service_name):
    """Get specific service information"""
    logger.debug(f"API request: get_service - {service_name}")
    service = HubConfig.get_service_config(service_name)
    
    if not service:
        raise HubException(
            f"Service '{service_name}' not found",
            status_code=404
        )
    
    return jsonify({
        'name': service.name,
        'description': service.description,
        'icon': service.icon,
        'port': service.port,
        'url': service.url,
        'features': service.features
    })


@app.route('/api/health')
@error_handler
def health_check():
    """Health check endpoint"""
    logger.debug("Health check requested")
    services = HubConfig.get_all_services()
    
    return jsonify({
        'status': 'healthy',
        'services_count': len(services),
        'services': list(services.keys()),
        'message': 'AI Assistant Hub is running',
        'version': '2.0.0'
    })


@app.route('/api/stats')
@error_handler
def get_stats():
    """Get hub statistics"""
    services = HubConfig.get_all_services()
    
    return jsonify({
        'total_services': len(services),
        'services_list': list(services.keys()),
        'cache_enabled': HubConfig.ENABLE_CACHE,
        'debug_mode': HubConfig.DEBUG
    })


def print_banner():
    """Print startup banner"""
    services = HubConfig.get_all_services()
    
    print("=" * 70)
    print("🚀 AI ASSISTANT HUB - MAIN GATEWAY v2.0")
    print("=" * 70)
    print(f"📍 Hub URL: http://{HubConfig.HOST}:{HubConfig.PORT}")
    print(f"🐛 Debug Mode: {HubConfig.DEBUG}")
    print(f"📊 Log Level: {HubConfig.LOG_LEVEL}")
    print(f"")
    print(f"📦 Available Services ({len(services)}):")
    for key, service in services.items():
        print(f"   {service.icon} {service.name:20s} → {service.url}")
    print(f"")
    print(f"💡 Important Notes:")
    print(f"   • Each service must run independently on its designated port")
    print(f"   • Check service README for startup instructions")
    print(f"   • Use 'start_all.bat' to launch all services at once")
    print("=" * 70)
    logger.info("AI Assistant Hub started successfully")


if __name__ == '__main__':
    print_banner()
    app.run(
        debug=HubConfig.DEBUG,
        host=HubConfig.HOST,
        port=HubConfig.PORT
    )
