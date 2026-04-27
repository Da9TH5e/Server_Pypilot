# main.py

import asyncio
import json
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel as PydanticModel

from models.model1 import GroqModels
from models.model2 import HuggingFaceModels
from models.fallback_model1 import GeminiModel

class AskRequest(PydanticModel):
    prompt: str
    context: Dict[str, Any]
    provider: str 
    metadata: Optional[Dict[str, Any]] = None

class AskResponse(PydanticModel):
    answer: str
    provider: str

class Job:
    def __init__(self, request: AskRequest):
        self.request = request
        self.future: asyncio.Future = asyncio.get_event_loop().create_future()

incoming_queue: asyncio.Queue[Job] = asyncio.Queue(maxsize=100)
outgoing_queue: asyncio.Queue[Job] = asyncio.Queue(maxsize=100)

class ModelScheduler:
    def __init__(self) -> None:
        self.models = {
            "light": GroqModels(),
            "heavy": HuggingFaceModels(),
            "gemini": GeminiModel()
        }
        
    async def _call(self, provider: str, fullprompt: str, timeout: float) -> str:
        loop = asyncio.get_event_loop()
        model = self.models[provider]  # ← simple direct lookup
        fn = model.generate_response if hasattr(model, "generate_response") else model.gen_response
        return await asyncio.wait_for(
            loop.run_in_executor(None, fn, fullprompt),
            timeout=timeout
        )
        
    async def schedule(self, job: Job) -> None:
        prompt = job.request.prompt
        context = job.request.context
        provider = job.request.provider
        answer = None
        used_provider = "none"
        
        fullprompt = (
            "You are Pysitant, an AI assistant that helps developers debug and manage their projects.\n"
            "You have full knowledge of the user's project structure below.\n\n"
            "PROJECT FILE STRUCTURE:\n"
            "------------------------\n"
            f"{json.dumps(context, indent=2)}\n\n"
            "USER QUESTION:\n"
            "--------------\n"
            f"{prompt}"
        )

        timeouts = {
            "light": 10.0,
            "heavy": 15.0,
            "gemini": 15.0
        }

        print(f"[Scheduler] Provider: {provider}")

        try:
            answer = await self._call(provider, fullprompt, timeout=timeouts[provider])
            used_provider = provider
        except (asyncio.TimeoutError, Exception) as e:
            print(f"[Scheduler] {provider} failed: {e} → Gemini fallback")
            try:
                answer = await self._call("gemini", fullprompt, timeout=15.0)
                used_provider = "gemini"
            except (asyncio.TimeoutError, Exception) as e:
                print(f"[Scheduler] Gemini failed: {e}")

        if answer:
            job.future.set_result(AskResponse(answer=answer, provider=used_provider))
        else:
            job.future.set_result(AskResponse(
                answer="Servers are busy, please try again later.",
                provider="none"
            ))
            
scheduler = ModelScheduler()

async def worker():
    print("[Worker] Started.")
    while True:
        job: Job = await incoming_queue.get()
        try:
            await scheduler.schedule(job)
        except Exception as e:
            job.future.set_result(AskResponse(
                answer="Servers are busy, please try again later.",
                provider="none"
            ))
        finally:
            await outgoing_queue.put(job)
            incoming_queue.task_done()
            
async def outgoing_worker():
    print("[Outgoing Worker] Started.")
    while True:
        job: Job = await outgoing_queue.get()
        outgoing_queue.task_done()

@asynccontextmanager
async def lifespan(app: FastAPI):
    workers = [asyncio.create_task(worker()) for _ in range(3)]
    outgoing = asyncio.create_task(outgoing_worker())
    print("[Server] 3 workers + 1 outgoing worker started.")
    yield
    for w in workers:
        w.cancel()
    outgoing.cancel()
    print("[Server] Workers stopped.")


app = FastAPI(title="PyPilot Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "incoming_queue": incoming_queue.qsize(),
        "outgoing_queue": outgoing_queue.qsize(),
    }

@app.post("/api/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    if incoming_queue.full():
        raise HTTPException(status_code=503, detail="Server is busy. Try again shortly.")

    job = Job(request)
    await incoming_queue.put(job)

    try:
        result = await asyncio.wait_for(job.future, timeout=40.0)
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request timed out.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))