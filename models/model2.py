import os
from typing import Optional
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

class HuggingFaceModels:
    def __init__(self) -> None:
        self.client = InferenceClient(api_key=os.environ["HUGGINGFACE_API_KEY"])

    def gen_response(self, prompt: str) -> Optional[str]:
        stream = self.client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct:ovhcloud",
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )

        return (stream.choices[0].message.content)