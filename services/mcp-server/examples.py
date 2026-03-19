"""
Example usage of AI-Assistant MCP Server
VÃ­ dá»¥ sá»­ dá»¥ng MCP Server
"""

import json
from typing import Dict, Any

# ==================== VÃ Dá»¤ 1: TÃŒM FILES ====================

def example_search_files():
    """
    VÃ­ dá»¥: Claude sáº½ gá»i tool search_files
    
    User há»i: "TÃ¬m giÃºp tÃ´i táº¥t cáº£ file Python liÃªn quan Ä‘áº¿n chatbot"
    
    Claude gá»i: search_files(query="chatbot", file_type="py", max_results=10)
    """
    # Response máº«u tá»« tool
    response = {
        "query": "chatbot",
        "file_type": "py",
        "total_found": 3,
        "results": [
            {
                "filename": "app.py",
                "path": "services/chatbot/app.py",
                "size": 15420
            },
            {
                "filename": "chatbot_service.py",
                "path": "services/chatbot/chatbot_service.py",
                "size": 8932
            }
        ]
    }
    print("Example 1: Search Files")
    print(json.dumps(response, indent=2, ensure_ascii=False))


# ==================== VÃ Dá»¤ 2: Äá»ŒC FILE ====================

def example_read_file():
    """
    VÃ­ dá»¥: Claude Ä‘á»c ná»™i dung file
    
    User há»i: "Äá»c file README.md cho tÃ´i"
    
    Claude gá»i: read_file_content(file_path="README.md", max_lines=100)
    """
    response = {
        "file_path": "README.md",
        "total_lines": 150,
        "lines_read": 100,
        "truncated": True,
        "content": "# AI-Assistant\n\nMulti-service AI application...\n"
    }
    print("\nExample 2: Read File")
    print(json.dumps(response, indent=2, ensure_ascii=False))


# ==================== VÃ Dá»¤ 3: LIá»†T KÃŠ THÆ¯ Má»¤C ====================

def example_list_directory():
    """
    VÃ­ dá»¥: Liá»‡t kÃª ná»™i dung thÆ° má»¥c
    
    User há»i: "CÃ³ nhá»¯ng gÃ¬ trong folder services?"
    
    Claude gá»i: list_directory(dir_path="services")
    """
    response = {
        "directory": "services",
        "total_items": 8,
        "folders": [
            {"name": "chatbot", "size": None, "modified": "2024-01-15T10:30:00"},
            {"name": "text2sql", "size": None, "modified": "2024-01-15T10:30:00"}
        ],
        "files": [
            {"name": "README.md", "size": 2048, "modified": "2024-01-15T10:30:00"}
        ]
    }
    print("\nExample 3: List Directory")
    print(json.dumps(response, indent=2, ensure_ascii=False))


# ==================== VÃ Dá»¤ 4: PROJECT INFO ====================

def example_project_info():
    """
    VÃ­ dá»¥: Láº¥y thÃ´ng tin project
    
    User há»i: "Cho tÃ´i biáº¿t thÃ´ng tin vá» project AI-Assistant"
    
    Claude gá»i: get_project_info()
    """
    response = {
        "project_name": "AI-Assistant",
        "base_directory": "C:\\Users\\Asus\\Downloads\\Compressed\\AI-Assistant",
        "services": [
            "chatbot",
            "text2sql",
            "document-intelligence",
            "image-upscale",
            "stable-diffusion"
        ],
        "structure": {
            "config": True,
            "services": True,
            "tests": True,
            "docs": True
        },
        "description": "Multi-service AI application"
    }
    print("\nExample 4: Project Info")
    print(json.dumps(response, indent=2, ensure_ascii=False))


# ==================== VÃ Dá»¤ 5: SEARCH LOGS ====================

def example_search_logs():
    """
    VÃ­ dá»¥: TÃ¬m kiáº¿m logs
    
    User há»i: "Kiá»ƒm tra logs cá»§a chatbot, cÃ³ lá»—i gÃ¬ khÃ´ng?"
    
    Claude gá»i: search_logs(service="chatbot", level="error", last_n_lines=50)
    """
    response = {
        "service_filter": "chatbot",
        "level_filter": "error",
        "logs_found": 1,
        "data": [
            {
                "service": "chatbot",
                "file": "chatbot.log",
                "total_lines": 1000,
                "entries": [
                    "2024-01-15 10:30:15 ERROR - Connection timeout",
                    "2024-01-15 10:31:20 ERROR - Database error"
                ]
            }
        ]
    }
    print("\nExample 5: Search Logs")
    print(json.dumps(response, indent=2, ensure_ascii=False))


# ==================== VÃ Dá»¤ 6: CALCULATE ====================

def example_calculate():
    """
    VÃ­ dá»¥: TÃ­nh toÃ¡n
    
    User há»i: "TÃ­nh sqrt(144) giÃºp tÃ´i"
    
    Claude gá»i: calculate(expression="sqrt(144)")
    """
    response = {
        "expression": "sqrt(144)",
        "result": 12.0,
        "type": "float"
    }
    print("\nExample 6: Calculate")
    print(json.dumps(response, indent=2, ensure_ascii=False))


# ==================== CONVERSATION EXAMPLES ====================

def conversation_examples():
    """
    VÃ­ dá»¥ cÃ¡c cuá»™c há»™i thoáº¡i thá»±c táº¿ vá»›i Claude Desktop
    """
    
    print("\n" + "="*60)
    print("CONVERSATION EXAMPLES - VÃ Dá»¤ Há»˜I THOáº I")
    print("="*60)
    
    examples = [
        {
            "user": "TÃ¬m táº¥t cáº£ cÃ¡c file Python liÃªn quan Ä‘áº¿n chatbot",
            "claude_thinks": "Cáº§n gá»i tool search_files vá»›i query='chatbot', file_type='py'",
            "claude_calls": "search_files(query='chatbot', file_type='py')",
            "result": "TÃ¬m tháº¥y 3 files: app.py, chatbot_service.py, utils.py trong services/chatbot/"
        },
        {
            "user": "Äá»c file services/chatbot/app.py vÃ  giáº£i thÃ­ch cho tÃ´i",
            "claude_thinks": "Cáº§n gá»i tool read_file_content Ä‘á»ƒ Ä‘á»c file",
            "claude_calls": "read_file_content(file_path='services/chatbot/app.py')",
            "result": "File nÃ y chá»©a FastAPI application cho chatbot service, cÃ³ cÃ¡c endpoints..."
        },
        {
            "user": "Project AI-Assistant cÃ³ nhá»¯ng services gÃ¬?",
            "claude_thinks": "Cáº§n láº¥y thÃ´ng tin tá»•ng quan vá» project",
            "claude_calls": "get_project_info()",
            "result": "Project cÃ³ 8 services: chatbot, text2sql, document-intelligence..."
        },
        {
            "user": "Kiá»ƒm tra logs cá»§a chatbot trong 50 dÃ²ng cuá»‘i, cÃ³ lá»—i khÃ´ng?",
            "claude_thinks": "Cáº§n tÃ¬m logs vá»›i filter level=error",
            "claude_calls": "search_logs(service='chatbot', level='error', last_n_lines=50)",
            "result": "TÃ¬m tháº¥y 2 lá»—i: Connection timeout vÃ  Database error"
        },
        {
            "user": "TÃ­nh sqrt(144) + pow(2, 8)",
            "claude_thinks": "Cáº§n dÃ¹ng tool calculate",
            "claude_calls": "calculate(expression='sqrt(144) + pow(2, 8)')",
            "result": "Káº¿t quáº£: 268.0"
        }
    ]
    
    for i, ex in enumerate(examples, 1):
        print(f"\n--- Example {i} ---")
        print(f"ðŸ‘¤ User: {ex['user']}")
        print(f"ðŸ¤” Claude thinks: {ex['claude_thinks']}")
        print(f"ðŸ”§ Claude calls: {ex['claude_calls']}")
        print(f"âœ… Result: {ex['result']}")


# ==================== MAIN ====================

if __name__ == "__main__":
    print("="*60)
    print("AI-ASSISTANT MCP SERVER - EXAMPLES")
    print("="*60)
    
    # Cháº¡y táº¥t cáº£ vÃ­ dá»¥
    example_search_files()
    example_read_file()
    example_list_directory()
    example_project_info()
    example_search_logs()
    example_calculate()
    
    # VÃ­ dá»¥ há»™i thoáº¡i
    conversation_examples()
    
    print("\n" + "="*60)
    print("âœ… Examples completed!")
    print("="*60)
