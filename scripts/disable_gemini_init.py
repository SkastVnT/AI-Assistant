import re

file_path = r"C:\Users\Asus\Downloads\Compressed\AI-Assistant\services\chatbot\app.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to match the Gemini initialization block
pattern = r'# Initialize Gemini client.*?try:.*?if GEMINI_API_KEY:.*?gemini_client = genai\.Client\(api_key=GEMINI_API_KEY\).*?logger\.info\(".*?Gemini API initialized with primary key"\).*?except Exception as e:.*?logger\.warning\(f".*?Primary Gemini key failed:.*?try:.*?if GEMINI_API_KEY_2:.*?gemini_client = genai\.Client\(api_key=GEMINI_API_KEY_2\).*?logger\.info\(".*?Gemini API initialized with backup key"\).*?except Exception as e2:.*?logger\.warning\(f".*?Backup Gemini key failed:.*?logger\.warning\(".*?Gemini API not available - Chat functionality will be limited"\)'

replacement = '''# ⛔ GEMINI DISABLED - Quota exhausted, use GROK/DeepSeek/OpenAI instead
# Initialize Gemini client with new SDK (optional - fallback to None if no key)
gemini_client = None
# try:
#     if GEMINI_API_KEY:
#         gemini_client = genai.Client(api_key=GEMINI_API_KEY)
#         logger.info("✅ Gemini API initialized with primary key")
# except Exception as e:
#     logger.warning(f"⚠️ Primary Gemini key failed: {e}")
#     try:
#         if GEMINI_API_KEY_2:
#             gemini_client = genai.Client(api_key=GEMINI_API_KEY_2)
#             logger.info("✅ Gemini API initialized with backup key")
#     except Exception as e2:
#         logger.warning(f"⚠️ Backup Gemini key failed: {e2}")
#         logger.warning("⚠️ Gemini API not available - Chat functionality will be limited")
logger.warning("⚠️ Gemini API DISABLED to avoid quota errors")'''

# Replace with DOTALL flag to match across newlines
new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Done! Gemini initialization disabled successfully")
