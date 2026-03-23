"""
Flask app with Gradio embedded - supports hot reload
"""
from flask import Flask, redirect
import gradio as gr
import threading
import time
import os

app = Flask(__name__)

# Default port from env or 7863 (matching start-image-upscale.bat)
DEFAULT_PORT = int(os.getenv('IMAGE_UPSCALE_PORT', '7863'))


@app.route('/')
def home():
    """Redirect to Gradio interface"""
    return redirect(f'http://127.0.0.1:{DEFAULT_PORT}')


def run_gradio():
    """Run Gradio in separate thread"""
    try:
        from . import web_ui
    except ImportError:
        # Fallback for when running as script
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import web_ui
    
    ui = web_ui.UpscaleWebUI()
    interface = ui.create_interface()
    
    # Get custom CSS and theme from interface
    custom_css = getattr(interface, 'custom_css', None)
    custom_theme = getattr(interface, 'custom_theme', None)
    
    interface.launch(
        server_name="0.0.0.0",
        server_port=DEFAULT_PORT,
        share=False,
        inbrowser=False,
        quiet=False,
        theme=custom_theme,
        css=custom_css
    )


def launch(host="0.0.0.0", port=None, debug=False):
    """Launch Gradio app directly without Flask wrapper"""
    if port is None:
        port = DEFAULT_PORT
    """Launch Gradio app directly without Flask wrapper"""
    print(f"""
    â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
    â•‘          ðŸŽ¨ AI Image Upscaler - Gradio                    â•‘
    â•‘                                                            â•‘
    â•‘  ðŸŒ Gradio UI: http://{host}:{port}                        â•‘
    â•‘                                                            â•‘
    â•‘  ðŸ’¡ Features:                                              â•‘
    â•‘     âœ“ 11 AI Models (Real-ESRGAN + Chinese)                â•‘
    â•‘     âœ“ Auto image info display                             â•‘
    â•‘     âœ“ Upscale preview calculator                          â•‘
    â•‘     âœ“ ImgBB sharing                                        â•‘
    â•‘                                                            â•‘
    â•‘  ðŸš€ Open: http://{host}:{port} in your browser            â•‘
    â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    """)
    
    # Run Gradio directly
    run_gradio()


if __name__ == '__main__':
    launch()

