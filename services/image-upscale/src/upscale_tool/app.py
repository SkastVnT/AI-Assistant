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
        server_name="127.0.0.1",
        server_port=7861,
        share=False,
        inbrowser=False,
        quiet=False,
        theme=custom_theme,
        css=custom_css
    )


def launch(host="127.0.0.1", port=5000, debug=True):
    """Launch Flask app with Gradio in background"""
    print(f"""
    ╔════════════════════════════════════════════════════════════╗
    ║          🎨 AI Image Upscaler - Flask + Gradio            ║
    ║                                                            ║
    ║  🌐 Gradio UI: http://127.0.0.1:7861                       ║
    ║  🔧 Flask Server: http://{host}:{port}                      ║
    ║  🔄 Hot Reload: Enabled (Ctrl + Shift + R to refresh)     ║
    ║  📝 Debug Mode: {'ON' if debug else 'OFF'}                                         ║
    ║                                                            ║
    ║  💡 Features:                                              ║
    ║     ✓ 11 AI Models (Real-ESRGAN + Chinese)                ║
    ║     ✓ Auto image info display                             ║
    ║     ✓ Upscale preview calculator                          ║
    ║     ✓ ImgBB sharing                                        ║
    ║     ✓ Hot reload support                                   ║
    ║                                                            ║
    ║  🚀 Open: http://127.0.0.1:7861 in your browser           ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    # Start Gradio in background thread
    gradio_thread = threading.Thread(target=run_gradio, daemon=True)
    gradio_thread.start()
    
    # Give Gradio time to start
    time.sleep(2)
    
    # Start Flask (won't actually be used, just for hot reload)
    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=False,  # Disable Flask reloader to avoid conflicts
        threaded=True
    )


if __name__ == '__main__':
    launch()

