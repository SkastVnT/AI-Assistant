from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY_1')

# Create client (API key can be set via GEMINI_API_KEY env var or explicitly)
client = genai.Client(api_key=GEMINI_API_KEY)

print("Available Gemini models:")
for m in client.models.list():
    if 'generateContent' in m.supported_generation_methods:
        print(f"  {m.name}")
