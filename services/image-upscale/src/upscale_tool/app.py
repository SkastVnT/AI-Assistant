"""
Flask app with Gradio embedded - supports hot reload
"""
from flask import Flask, redirect
import gradio as gr
import threading
import time

app = Flask(__name__)


@app.route('/')
def home():
    """Redirect to Gradio interface"""
    return redirect('http://127.0.0.1:7861')


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
        server_port=7861,
        share=False,
        inbrowser=False,
        quiet=False,
        theme=custom_theme,
        css=custom_css
    )


def launch(host="0.0.0.0", port=7861, debug=False):
    """Launch Gradio app directly without Flask wrapper"""
    print(f"""
    ╔════════════════════════════════════════════════════════════╗
    ║          🎨 AI Image Upscaler - Gradio                    ║
    ║                                                            ║
    ║  🌐 Gradio UI: http://{host}:{port}                        ║
    ║                                                            ║
    ║  💡 Features:                                              ║
    ║     ✓ 11 AI Models (Real-ESRGAN + Chinese)                ║
    ║     ✓ Auto image info display                             ║
    ║     ✓ Upscale preview calculator                          ║
    ║     ✓ ImgBB sharing                                        ║
    ║                                                            ║
    ║  🚀 Open: http://{host}:{port} in your browser            ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    # Run Gradio directly
    run_gradio()


if __name__ == '__main__':
    launch()

