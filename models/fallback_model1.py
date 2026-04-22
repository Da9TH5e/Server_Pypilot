import os
from typing import Optional
from google import genai
from dotenv import load_dotenv

load_dotenv()

class GeminiModel:
    def __init__(self) -> None:
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def generate_response(self, prompt: str) -> Optional[str]:
        response = self.client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[prompt]
        )
        return response.text