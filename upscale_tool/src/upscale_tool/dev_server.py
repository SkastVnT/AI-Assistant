"""
Development server with auto-reload using watchdog
"""
import sys
import time
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class CodeChangeHandler(FileSystemEventHandler):
    """Handle file changes and restart server"""
    
    def __init__(self):
        self.process = None
        self.last_restart = 0
        self.restart_server()
    
    def on_modified(self, event):
        """Restart server when Python files change"""
        if event.src_path.endswith('.py'):
            current_time = time.time()
            # Debounce: only restart once per 2 seconds
            if current_time - self.last_restart > 2:
                print(f"\n🔄 Detected change in: {event.src_path}")
                print("⚡ Restarting server...\n")
                self.last_restart = current_time
                self.restart_server()
    
    def restart_server(self):
        """Kill old process and start new one"""
        if self.process:
            self.process.terminate()
            self.process.wait()
        
        # Start new server process
        self.process = subprocess.Popen(
            [sys.executable, '-m', 'upscale_tool.web_ui'],
            cwd=Path(__file__).parent.parent.parent
        )


def main():
    """Run development server with file watching"""
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║       🔥 Development Server with Hot Reload 🔥            ║
    ║                                                            ║
    ║  🌐 URL: http://127.0.0.1:7861                            ║
    ║  🔄 Watching for file changes...                          ║
    ║  💡 Edit web_ui.py and press Ctrl+S to auto-reload       ║
    ║  🛑 Press Ctrl+C to stop                                  ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    # Watch current directory
    watch_path = Path(__file__).parent
    
    event_handler = CodeChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, str(watch_path), recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping server...")
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
    
    observer.join()


if __name__ == '__main__':
    main()
