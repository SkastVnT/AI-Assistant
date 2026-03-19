#!/usr/bin/env python3
"""
AI-Assistant Public Deployment Script
=====================================
Starts all services and exposes them via ngrok for public access.

Usage:
    python3 scripts/deploy_public.py [--services all|hub,chatbot,...]
    
Requirements:
    pip install pyngrok
"""

import subprocess
import sys
import os
import time
import signal
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional

# Service configuration
SERVICES = {
    "hub-gateway": {
        "port": 3000,
        "dir": "services/hub-gateway",
        "command": ["python3", "hub.py"],
        "name": "Hub Gateway",
        "description": "Main API Gateway"
    },
    "chatbot": {
        "port": 5000,
        "dir": "services/chatbot",
        "command": ["python3", "run.py"],
        "name": "ChatBot",
        "description": "Multi-Model AI Chat"
    },
    "text2sql": {
        "port": 5002,
        "dir": "services/text2sql",
        "command": ["python3", "run.py"],
        "name": "Text2SQL",
        "description": "Natural Language to SQL"
    },
    "document-intelligence": {
        "port": 5003,
        "dir": "services/document-intelligence",
        "command": ["python3", "run.py"],
        "name": "Document Intelligence",
        "description": "OCR & Document Processing"
    },
    "speech2text": {
        "port": 5001,
        "dir": "services/speech2text/app",
        "command": ["python3", "web_ui.py"],
        "name": "Speech2Text",
        "description": "Audio Transcription"
    },
    "edit-image": {
        "port": 8100,
        "dir": "services/edit-image",
        "command": ["python3", "run_grok_ui.py"],
        "name": "Edit Image",
        "description": "Grok-like Image Editor"
    },
    "mcp-server": {
        "port": 8080,
        "dir": "services/mcp-server",
        "command": ["python3", "server.py"],
        "name": "MCP Server",
        "description": "Model Context Protocol"
    }
}

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_banner():
    """Print startup banner"""
    banner = f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   █████╗ ██╗    ███████╗███████╗██████╗ ██╗   ██╗██╗ ██████╗███████╗        ║
║  ██╔══██╗██║    ██╔════╝██╔════╝██╔══██╗██║   ██║██║██╔════╝██╔════╝        ║
║  ███████║██║    ███████╗█████╗  ██████╔╝██║   ██║██║██║     █████╗          ║
║  ██╔══██║██║    ╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██║██║     ██╔══╝          ║
║  ██║  ██║██║    ███████║███████╗██║  ██║ ╚████╔╝ ██║╚██████╗███████╗        ║
║  ╚═╝  ╚═╝╚═╝    ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚═╝ ╚═════╝╚══════╝        ║
║                                                                              ║
║                    🌐 Public Deployment Manager v1.0 🌐                      ║
╚══════════════════════════════════════════════════════════════════════════════╝{Colors.END}
"""
    print(banner)

def check_pyngrok():
    """Check and install pyngrok if needed"""
    try:
        from pyngrok import ngrok
        return True
    except ImportError:
        print(f"{Colors.YELLOW}📦 Installing pyngrok...{Colors.END}")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyngrok", "-q"])
        return True

def get_project_root() -> Path:
    """Get project root directory"""
    script_dir = Path(__file__).parent
    return script_dir.parent

def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_port(port: int):
    """Kill process on a specific port"""
    try:
        result = subprocess.run(
            f"lsof -ti :{port} | xargs kill -9 2>/dev/null",
            shell=True, capture_output=True
        )
    except:
        pass

class ServiceManager:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.processes: Dict[str, subprocess.Popen] = {}
        self.tunnels: Dict[str, any] = {}
        self.public_urls: Dict[str, str] = {}
        self.running = True
        
    def start_service(self, service_id: str) -> bool:
        """Start a single service"""
        config = SERVICES.get(service_id)
        if not config:
            print(f"{Colors.RED}❌ Unknown service: {service_id}{Colors.END}")
            return False
            
        service_dir = self.root_dir / config["dir"]
        if not service_dir.exists():
            print(f"{Colors.YELLOW}⚠️  Directory not found: {config['dir']}{Colors.END}")
            return False
            
        port = config["port"]
        
        # Kill existing process on port
        if is_port_in_use(port):
            print(f"{Colors.YELLOW}   Killing existing process on port {port}...{Colors.END}")
            kill_port(port)
            time.sleep(1)
        
        print(f"{Colors.BLUE}🚀 Starting {config['name']} on port {port}...{Colors.END}")
        
        try:
            # Start the service
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            
            log_dir = self.root_dir / "logs"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"{service_id}.log"
            
            with open(log_file, "w") as log:
                process = subprocess.Popen(
                    config["command"],
                    cwd=service_dir,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )
            
            self.processes[service_id] = process
            
            # Wait for service to start
            for _ in range(30):  # 30 seconds timeout
                time.sleep(1)
                if is_port_in_use(port):
                    print(f"{Colors.GREEN}   ✓ {config['name']} started successfully{Colors.END}")
                    return True
                if process.poll() is not None:
                    print(f"{Colors.RED}   ✗ {config['name']} exited unexpectedly{Colors.END}")
                    return False
                    
            print(f"{Colors.YELLOW}   ⚠️  {config['name']} may still be starting...{Colors.END}")
            return True
            
        except Exception as e:
            print(f"{Colors.RED}   ✗ Failed to start {config['name']}: {e}{Colors.END}")
            return False
    
    def create_tunnel(self, service_id: str) -> Optional[str]:
        """Create ngrok tunnel for a service"""
        from pyngrok import ngrok, conf
        
        config = SERVICES.get(service_id)
        if not config:
            return None
            
        port = config["port"]
        
        if not is_port_in_use(port):
            print(f"{Colors.YELLOW}   ⚠️  Port {port} not listening, skipping tunnel{Colors.END}")
            return None
            
        try:
            print(f"{Colors.CYAN}🔗 Creating tunnel for {config['name']}...{Colors.END}")
            tunnel = ngrok.connect(port, "http")
            self.tunnels[service_id] = tunnel
            public_url = tunnel.public_url
            self.public_urls[service_id] = public_url
            print(f"{Colors.GREEN}   ✓ Tunnel created: {public_url}{Colors.END}")
            return public_url
        except Exception as e:
            print(f"{Colors.RED}   ✗ Failed to create tunnel: {e}{Colors.END}")
            return None
    
    def start_all(self, service_list: List[str] = None):
        """Start all specified services"""
        services_to_start = service_list or list(SERVICES.keys())
        
        print(f"\n{Colors.BOLD}📋 Starting {len(services_to_start)} services...{Colors.END}\n")
        
        started = []
        failed = []
        
        for service_id in services_to_start:
            if self.start_service(service_id):
                started.append(service_id)
            else:
                failed.append(service_id)
        
        print(f"\n{Colors.BOLD}🔗 Creating ngrok tunnels...{Colors.END}\n")
        
        for service_id in started:
            self.create_tunnel(service_id)
            
        return started, failed
    
    def print_status(self):
        """Print status table of all services"""
        print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}{'SERVICE':<25} {'PORT':<8} {'STATUS':<12} {'PUBLIC URL'}{Colors.END}")
        print(f"{Colors.BOLD}{'='*80}{Colors.END}")
        
        for service_id, config in SERVICES.items():
            port = config["port"]
            name = config["name"]
            
            if service_id in self.public_urls:
                status = f"{Colors.GREEN}✓ ONLINE{Colors.END}"
                url = self.public_urls[service_id]
            elif service_id in self.processes:
                if is_port_in_use(port):
                    status = f"{Colors.YELLOW}◐ LOCAL{Colors.END}"
                else:
                    status = f"{Colors.YELLOW}◐ STARTING{Colors.END}"
                url = f"http://localhost:{port}"
            else:
                status = f"{Colors.RED}✗ OFFLINE{Colors.END}"
                url = "-"
            
            print(f"{name:<25} {port:<8} {status:<22} {url}")
        
        print(f"{'='*80}\n")
    
    def save_urls(self):
        """Save public URLs to a file"""
        urls_file = self.root_dir / "public_urls.json"
        data = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "services": {}
        }
        
        for service_id, url in self.public_urls.items():
            config = SERVICES[service_id]
            data["services"][service_id] = {
                "name": config["name"],
                "port": config["port"],
                "public_url": url,
                "description": config["description"]
            }
        
        with open(urls_file, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"{Colors.GREEN}📄 URLs saved to: {urls_file}{Colors.END}")
        
        # Also create a simple text file for easy copying
        txt_file = self.root_dir / "public_urls.txt"
        with open(txt_file, "w") as f:
            f.write("AI-Assistant Public URLs\n")
            f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n\n")
            for service_id, url in self.public_urls.items():
                config = SERVICES[service_id]
                f.write(f"{config['name']}: {url}\n")
        
        print(f"{Colors.GREEN}📄 URLs also saved to: {txt_file}{Colors.END}")
    
    def cleanup(self):
        """Clean up all processes and tunnels"""
        print(f"\n{Colors.YELLOW}🧹 Cleaning up...{Colors.END}")
        
        # Close tunnels
        from pyngrok import ngrok
        try:
            ngrok.kill()
        except:
            pass
        
        # Kill processes
        for service_id, process in self.processes.items():
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except:
                try:
                    process.terminate()
                except:
                    pass
        
        print(f"{Colors.GREEN}✓ Cleanup complete{Colors.END}")
    
    def wait_forever(self):
        """Wait until interrupted"""
        print(f"\n{Colors.GREEN}{'='*80}{Colors.END}")
        print(f"{Colors.GREEN}🎉 All services are running and publicly accessible!{Colors.END}")
        print(f"{Colors.GREEN}{'='*80}{Colors.END}")
        print(f"\n{Colors.YELLOW}Press Ctrl+C to stop all services and close tunnels{Colors.END}\n")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            print(f"\n{Colors.YELLOW}Received interrupt signal...{Colors.END}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy AI-Assistant services publicly")
    parser.add_argument(
        "--services", "-s",
        type=str,
        default="all",
        help="Comma-separated list of services to start (e.g., hub-gateway,chatbot) or 'all'"
    )
    parser.add_argument(
        "--no-tunnel",
        action="store_true",
        help="Start services without creating ngrok tunnels"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available services and exit"
    )
    
    args = parser.parse_args()
    
    print_banner()
    
    if args.list:
        print(f"{Colors.BOLD}Available services:{Colors.END}\n")
        for service_id, config in SERVICES.items():
            print(f"  {Colors.CYAN}{service_id:<25}{Colors.END} Port {config['port']:<6} - {config['description']}")
        print()
        return
    
    # Check/install pyngrok
    if not args.no_tunnel:
        check_pyngrok()
    
    root_dir = get_project_root()
    manager = ServiceManager(root_dir)
    
    # Parse service list
    if args.services.lower() == "all":
        service_list = list(SERVICES.keys())
    else:
        service_list = [s.strip() for s in args.services.split(",")]
    
    # Handle cleanup on exit
    def signal_handler(sig, frame):
        manager.running = False
        manager.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start services
        started, failed = manager.start_all(service_list)
        
        # Print status
        manager.print_status()
        
        # Save URLs
        if manager.public_urls:
            manager.save_urls()
        
        # Print summary
        print(f"\n{Colors.BOLD}Summary:{Colors.END}")
        print(f"  ✓ Started: {len(started)}")
        print(f"  ✗ Failed:  {len(failed)}")
        print(f"  🔗 Tunnels: {len(manager.public_urls)}")
        
        if failed:
            print(f"\n{Colors.RED}Failed services: {', '.join(failed)}{Colors.END}")
            print(f"Check logs in: {root_dir}/logs/")
        
        # Wait for interrupt
        if manager.public_urls or started:
            manager.wait_forever()
        
    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.END}")
        manager.cleanup()
        sys.exit(1)
    finally:
        manager.cleanup()


if __name__ == "__main__":
    main()
