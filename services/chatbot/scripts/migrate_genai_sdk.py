"""
Migration script: Update chatbot from google.generativeai to google.genai
This script updates the deprecated SDK to the new one.
"""

import re
from pathlib import Path

def migrate_chatbot_app():
    app_file = Path(__file__).parent.parent / "app.py"
    
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace old genai.configure() with new Client initialization
    # Old: genai.configure(api_key=GEMINI_API_KEY)
    # New: gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Find and replace genai.configure lines
    content = re.sub(
        r'try:\s+genai\.configure\(api_key=GEMINI_API_KEY\)\s+except:\s+genai\.configure\(api_key=GEMINI_API_KEY_2\)',
        '''# Initialize Gemini client (new SDK)
try:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
except:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY_2)''',
        content,
        flags=re.DOTALL
    )
    
    # Replace genai.GenerativeModel with gemini_client.models.generate_content
    # This is complex - need to track all model creations and generations
    
    print("Migration requires manual review due to API differences.")
    print("Key changes needed:")
    print("1. Replace genai.configure() with genai.Client()")
    print("2. Replace model.generate_content() with client.models.generate_content()")
    print("3. Update all model references")
    
    with open(app_file.parent / "app_migrated.py", 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Partial migration saved to: {app_file.parent / 'app_migrated.py'}")
    print("Please review and complete manual migration.")

if __name__ == "__main__":
    migrate_chatbot_app()
