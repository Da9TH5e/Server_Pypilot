import os
from typing import Optional
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class GroqModels:
    def __init__(self) -> None:
        self.client = Groq(api_key=os.environ["GROQ_API_KEY"])
        
    def generate_response(self, prompt: str) -> Optional[str]:
        completion = self.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content