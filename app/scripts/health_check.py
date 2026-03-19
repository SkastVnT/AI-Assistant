#!/usr/bin/env python3
"""
AI-Assistant Service Health Check
Tests all services and reports their status.

Usage:
    python scripts/health_check.py
"""

import os
import sys
import time
import socket
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ServiceStatus:
    """Status of a service."""
    name: str
    port: int
    status: str  # 'running', 'stopped', 'error', 'import_ok'
    message: str
    import_test: bool = False
    

def check_port(port: int, host: str = 'localhost', timeout: float = 2.0) -> bool:
    """Check if a port is listening."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def test_import(module_path: str, test_code: str) -> Tuple[bool, str]:
    """Test if a module can be imported."""
    try:
        exec(test_code)
        return True, "Import OK"
    except Exception as e:
        return False, str(e)


def check_hub_gateway() -> ServiceStatus:
    """Check Hub Gateway service."""
    name = "Hub Gateway"
    port = 3000
    
    # Test import
    try:
        sys.path.insert(0, str(PROJECT_ROOT / 'services' / 'hub-gateway'))
        from hub import app
        import_ok = True
        msg = "Import OK"
    except Exception as e:
        import_ok = False
        msg = str(e)
    
    # Test port
    if check_port(port):
        return ServiceStatus(name, port, 'running', f"Running on port {port}", import_ok)
    
    if import_ok:
        return ServiceStatus(name, port, 'import_ok', msg, import_ok)
    else:
        return ServiceStatus(name, port, 'error', msg, import_ok)


def check_chatbot() -> ServiceStatus:
    """Check ChatBot service."""
    name = "ChatBot"
    port = 5000
    
    # Test import (using the fixed run.py approach)
    try:
        chatbot_dir = PROJECT_ROOT / 'services' / 'chatbot'
        sys.path.insert(0, str(chatbot_dir))
        
        import importlib.util
        app_py = chatbot_dir / 'app.py'
        
        # Just check syntax
        import ast
        with open(app_py, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        
        import_ok = True
        msg = "Syntax OK"
    except Exception as e:
        import_ok = False
        msg = str(e)[:100]
    
    if check_port(port):
        return ServiceStatus(name, port, 'running', f"Running on port {port}", import_ok)
    
    if import_ok:
        return ServiceStatus(name, port, 'import_ok', msg, import_ok)
    else:
        return ServiceStatus(name, port, 'error', msg, import_ok)


def check_document_intelligence() -> ServiceStatus:
    """Check Document Intelligence service."""
    name = "Document Intelligence"
    port = 5003
    
    try:
        doc_dir = PROJECT_ROOT / 'services' / 'document-intelligence'
        sys.path.insert(0, str(doc_dir))
        
        from src.utils.advanced_features import ProcessingHistory, QuickActions
        import_ok = True
        msg = "Import OK"
    except Exception as e:
        import_ok = False
        msg = str(e)[:100]
    
    if check_port(port):
        return ServiceStatus(name, port, 'running', f"Running on port {port}", import_ok)
    
    if import_ok:
        return ServiceStatus(name, port, 'import_ok', msg, import_ok)
    else:
        return ServiceStatus(name, port, 'error', msg, import_ok)


def check_speech2text() -> ServiceStatus:
    """Check Speech2Text service."""
    name = "Speech2Text"
    port = 5001
    
    try:
        s2t_dir = PROJECT_ROOT / 'services' / 'speech2text' / 'app'
        sys.path.insert(0, str(s2t_dir))
        
        from core.models import WhisperClient, check_cudnn_available
        import_ok = True
        msg = "Core models import OK"
    except Exception as e:
        import_ok = False
        msg = str(e)[:100]
    
    if check_port(port):
        return ServiceStatus(name, port, 'running', f"Running on port {port}", import_ok)
    
    if import_ok:
        return ServiceStatus(name, port, 'import_ok', msg, import_ok)
    else:
        return ServiceStatus(name, port, 'error', msg, import_ok)


def check_edit_image() -> ServiceStatus:
    """Check Edit Image service."""
    name = "Edit Image"
    port = 8100
    
    try:
        edit_dir = PROJECT_ROOT / 'services' / 'edit-image'
        sys.path.insert(0, str(edit_dir))
        
        from app.core import Settings, get_settings
        import_ok = True
        msg = "Core config import OK"
    except Exception as e:
        import_ok = False
        msg = str(e)[:100]
    
    if check_port(port):
        return ServiceStatus(name, port, 'running', f"Running on port {port}", import_ok)
    
    if import_ok:
        return ServiceStatus(name, port, 'import_ok', msg, import_ok)
    else:
        return ServiceStatus(name, port, 'error', msg, import_ok)


def check_mcp_server() -> ServiceStatus:
    """Check MCP Server service."""
    name = "MCP Server"
    port = 0  # MCP uses stdio
    
    try:
        mcp_dir = PROJECT_ROOT / 'services' / 'mcp-server'
        sys.path.insert(0, str(mcp_dir))
        
        import mcp
        from server import mcp as mcp_server
        import_ok = True
        msg = "MCP library and server import OK"
    except Exception as e:
        import_ok = False
        msg = str(e)[:100]
    
    if import_ok:
        return ServiceStatus(name, port, 'import_ok', msg, import_ok)
    else:
        return ServiceStatus(name, port, 'error', msg, import_ok)


def check_stable_diffusion() -> ServiceStatus:
    """Check Stable Diffusion service."""
    name = "Stable Diffusion"
    port = 7861
    
    try:
        import torch
        import_ok = torch.cuda.is_available()
        msg = f"PyTorch OK, CUDA: {import_ok}"
    except Exception as e:
        import_ok = False
        msg = str(e)[:100]
    
    if check_port(port):
        return ServiceStatus(name, port, 'running', f"Running on port {port}", import_ok)
    
    if import_ok:
        return ServiceStatus(name, port, 'import_ok', msg, import_ok)
    else:
        return ServiceStatus(name, port, 'error', msg, import_ok)


def print_report(services: List[ServiceStatus]) -> None:
    """Print service status report."""
    print("\n" + "=" * 70)
    print("🏥 AI-ASSISTANT SERVICE HEALTH CHECK REPORT")
    print("=" * 70 + "\n")
    
    # Group by status
    running = [s for s in services if s.status == 'running']
    ready = [s for s in services if s.status == 'import_ok']
    failed = [s for s in services if s.status == 'error']
    
    # Running services
    if running:
        print("🟢 RUNNING SERVICES:")
        for s in running:
            print(f"   ✅ {s.name:25s} Port {s.port:5d} - {s.message}")
        print()
    
    # Ready to start
    if ready:
        print("🟡 READY TO START (imports OK):")
        for s in ready:
            port_str = f"Port {s.port:5d}" if s.port > 0 else "stdio    "
            print(f"   ⏸️  {s.name:25s} {port_str} - {s.message}")
        print()
    
    # Failed
    if failed:
        print("🔴 FAILED SERVICES:")
        for s in failed:
            print(f"   ❌ {s.name:25s} - {s.message}")
        print()
    
    # Summary
    total = len(services)
    print("=" * 70)
    print(f"SUMMARY: {len(running)}/{total} running, {len(ready)}/{total} ready, {len(failed)}/{total} failed")
    print("=" * 70 + "\n")


def main():
    """Run all health checks."""
    logger.info("Starting AI-Assistant health check...")
    
    services = [
        check_hub_gateway(),
        check_chatbot(),
        check_document_intelligence(),
        check_speech2text(),
        check_edit_image(),
        check_mcp_server(),
        check_stable_diffusion(),
    ]
    
    print_report(services)
    
    # Return exit code
    failed = [s for s in services if s.status == 'error']
    return len(failed)


if __name__ == '__main__':
    sys.exit(main())
