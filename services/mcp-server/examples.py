"""
Example usage of AI-Assistant MCP Server
Ví dụ sử dụng MCP Server
"""

import json
from typing import Dict, Any

# ==================== VÍ DỤ 1: TÌM FILES ====================

def example_search_files():
    """
    Ví dụ: Claude sẽ gọi tool search_files
    
    User hỏi: "Tìm giúp tôi tất cả file Python liên quan đến chatbot"
    
    Claude gọi: search_files(query="chatbot", file_type="py", max_results=10)
    """
    # Response mẫu từ tool
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


# ==================== VÍ DỤ 2: ĐỌC FILE ====================

def example_read_file():
    """
    Ví dụ: Claude đọc nội dung file
    
    User hỏi: "Đọc file README.md cho tôi"
    
    Claude gọi: read_file_content(file_path="README.md", max_lines=100)
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


# ==================== VÍ DỤ 3: LIỆT KÊ THƯ MỤC ====================

def example_list_directory():
    """
    Ví dụ: Liệt kê nội dung thư mục
    
    User hỏi: "Có những gì trong folder services?"
    
    Claude gọi: list_directory(dir_path="services")
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


# ==================== VÍ DỤ 4: PROJECT INFO ====================

def example_project_info():
    """
    Ví dụ: Lấy thông tin project
    
    User hỏi: "Cho tôi biết thông tin về project AI-Assistant"
    
    Claude gọi: get_project_info()
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


# ==================== VÍ DỤ 5: SEARCH LOGS ====================

def example_search_logs():
    """
    Ví dụ: Tìm kiếm logs
    
    User hỏi: "Kiểm tra logs của chatbot, có lỗi gì không?"
    
    Claude gọi: search_logs(service="chatbot", level="error", last_n_lines=50)
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


# ==================== VÍ DỤ 6: CALCULATE ====================

def example_calculate():
    """
    Ví dụ: Tính toán
    
    User hỏi: "Tính sqrt(144) giúp tôi"
    
    Claude gọi: calculate(expression="sqrt(144)")
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
    Ví dụ các cuộc hội thoại thực tế với Claude Desktop
    """
    
    print("\n" + "="*60)
    print("CONVERSATION EXAMPLES - VÍ DỤ HỘI THOẠI")
    print("="*60)
    
    examples = [
        {
            "user": "Tìm tất cả các file Python liên quan đến chatbot",
            "claude_thinks": "Cần gọi tool search_files với query='chatbot', file_type='py'",
            "claude_calls": "search_files(query='chatbot', file_type='py')",
            "result": "Tìm thấy 3 files: app.py, chatbot_service.py, utils.py trong services/chatbot/"
        },
        {
            "user": "Đọc file services/chatbot/app.py và giải thích cho tôi",
            "claude_thinks": "Cần gọi tool read_file_content để đọc file",
            "claude_calls": "read_file_content(file_path='services/chatbot/app.py')",
            "result": "File này chứa FastAPI application cho chatbot service, có các endpoints..."
        },
        {
            "user": "Project AI-Assistant có những services gì?",
            "claude_thinks": "Cần lấy thông tin tổng quan về project",
            "claude_calls": "get_project_info()",
            "result": "Project có 8 services: chatbot, text2sql, document-intelligence..."
        },
        {
            "user": "Kiểm tra logs của chatbot trong 50 dòng cuối, có lỗi không?",
            "claude_thinks": "Cần tìm logs với filter level=error",
            "claude_calls": "search_logs(service='chatbot', level='error', last_n_lines=50)",
            "result": "Tìm thấy 2 lỗi: Connection timeout và Database error"
        },
        {
            "user": "Tính sqrt(144) + pow(2, 8)",
            "claude_thinks": "Cần dùng tool calculate",
            "claude_calls": "calculate(expression='sqrt(144) + pow(2, 8)')",
            "result": "Kết quả: 268.0"
        }
    ]
    
    for i, ex in enumerate(examples, 1):
        print(f"\n--- Example {i} ---")
        print(f"👤 User: {ex['user']}")
        print(f"🤔 Claude thinks: {ex['claude_thinks']}")
        print(f"🔧 Claude calls: {ex['claude_calls']}")
        print(f"✅ Result: {ex['result']}")


# ==================== MAIN ====================

if __name__ == "__main__":
    print("="*60)
    print("AI-ASSISTANT MCP SERVER - EXAMPLES")
    print("="*60)
    
    # Chạy tất cả ví dụ
    example_search_files()
    example_read_file()
    example_list_directory()
    example_project_info()
    example_search_logs()
    example_calculate()
    
    # Ví dụ hội thoại
    conversation_examples()
    
    print("\n" + "="*60)
    print("✅ Examples completed!")
    print("="*60)
