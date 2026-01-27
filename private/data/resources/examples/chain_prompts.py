# Example: Service Routing with Chain Prompts

"""
This example shows how to chain multiple services together.
For example: Speech2Text → ChatBot → Text2SQL
"""

import requests
import json
import time


HUB_URL = "http://localhost:3000"
CHATBOT_URL = "http://localhost:5000"
SPEECH2TEXT_URL = "http://localhost:5001"
TEXT2SQL_URL = "http://localhost:5002"


def chain_speech_to_chatbot(audio_file_path):
    """
    Example workflow:
    1. Convert audio to text using Speech2Text
    2. Send text to ChatBot for analysis
    """
    print("=" * 60)
    print("Chain Example: Speech2Text → ChatBot")
    print("=" * 60)
    
    # Step 1: Speech to Text
    print("\n📤 Step 1: Converting audio to text...")
    # Note: Actual implementation depends on Speech2Text API
    # This is a placeholder
    transcribed_text = "Tôi cảm thấy mệt mỏi và stress với công việc"
    print(f"✅ Transcribed: {transcribed_text}")
    
    # Step 2: Send to ChatBot
    print("\n📤 Step 2: Analyzing with ChatBot...")
    # Note: Actual implementation depends on ChatBot API
    # This is a placeholder
    chatbot_response = {
        "response": "Tôi hiểu bạn đang cảm thấy áp lực. Hãy thử nghỉ ngơi và sắp xếp công việc hợp lý hơn.",
        "model": "gemini"
    }
    print(f"✅ ChatBot response: {chatbot_response['response']}")
    
    print("\n✅ Chain completed!")
    return chatbot_response


def chain_chatbot_to_sql(user_query):
    """
    Example workflow:
    1. User asks question to ChatBot
    2. ChatBot generates SQL query
    3. Text2SQL validates and executes
    """
    print("=" * 60)
    print("Chain Example: ChatBot → Text2SQL")
    print("=" * 60)
    
    # Step 1: ChatBot processes query
    print(f"\n📤 Step 1: User query: {user_query}")
    
    # Step 2: Generate SQL
    print("\n📤 Step 2: Generating SQL query...")
    # This is a placeholder
    sql_query = "SELECT * FROM users WHERE status = 'active'"
    print(f"✅ Generated SQL: {sql_query}")
    
    # Step 3: Validate with Text2SQL
    print("\n📤 Step 3: Validating SQL...")
    print("✅ SQL validated!")
    
    print("\n✅ Chain completed!")
    return sql_query


def get_service_info_from_hub(service_name):
    """Get service information from Hub."""
    response = requests.get(f"{HUB_URL}/api/services/{service_name}")
    if response.status_code == 200:
        return response.json()
    return None


if __name__ == "__main__":
    print("\n🔗 AI Assistant Hub - Service Chaining Example\n")
    
    # Example 1: Speech to ChatBot
    print("\n" + "="*60)
    print("Example 1: Speech to ChatBot Chain")
    print("="*60)
    chain_speech_to_chatbot("example_audio.wav")
    
    # Example 2: ChatBot to SQL
    print("\n" + "="*60)
    print("Example 2: ChatBot to SQL Chain")
    print("="*60)
    chain_chatbot_to_sql("Cho tôi xem danh sách người dùng đang hoạt động")
    
    # Get service info
    print("\n" + "="*60)
    print("Getting Service Information from Hub")
    print("="*60)
    try:
        for service_name in ['chatbot', 'speech2text', 'text2sql']:
            info = get_service_info_from_hub(service_name)
            if info:
                print(f"\n{info['icon']} {info['name']}: {info['url']}")
    except Exception as e:
        print(f"Note: Hub must be running to fetch service info")
    
    print("\n✅ Examples completed!")
    print("\n💡 Note: These are placeholder examples.")
    print("   Actual implementation requires running services with proper APIs.")
