import google.generativeai as genai

genai.configure(api_key='AIzaSyB0h_O7rVZTcSqh1iPHvuRwEE5PsCgvK18')

print("Available Gemini models:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"  {m.name}")
