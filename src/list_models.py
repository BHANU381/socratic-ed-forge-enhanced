from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

print("--- Available Models ---")
# Using the correct SDK method for listing models
for model in client.models.list():
    print(f"Name: {model.name}")
