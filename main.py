# main.py

import asyncio
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel as PydanticModel

from models.model1 import GroqModels
from models.model2 import HuggingFaceModels
from models.fallback_model1 import GeminiModel

load_dotenv()

PYSITANT_API_KEY_ENV = "PYSITANT_API_KEY"
PYSITANT_SESSION_TIMEOUT_SECONDS_ENV = "PYSITANT_SESSION_TIMEOUT_SECONDS"
LEGACY_PYSITANT_API_KEY_ENV = "PYSITANT_API_KEY"
LEGACY_PYSITANT_SESSION_TIMEOUT_SECONDS_ENV = "PYSITANT_SESSION_TIMEOUT_SECONDS"
DEFAULT_SESSION_TIMEOUT_SECONDS = 30 * 60

active_sessions: Dict[str, float] = {}


def get_session_timeout_seconds() -> int:
    raw_timeout = os.getenv(PYSITANT_SESSION_TIMEOUT_SECONDS_ENV) or os.getenv(
        LEGACY_PYSITANT_SESSION_TIMEOUT_SECONDS_ENV
    )
    if not raw_timeout:
        return DEFAULT_SESSION_TIMEOUT_SECONDS

    try:
        return int(raw_timeout)
    except ValueError:
        return DEFAULT_SESSION_TIMEOUT_SECONDS


def cleanup_expired_sessions() -> None:
    now = time.time()
    timeout = get_session_timeout_seconds()
    expired_tokens = [
        token
        for token, last_seen in active_sessions.items()
        if now - last_seen > timeout
    ]

    for token in expired_tokens:
        active_sessions.pop(token, None)


def get_bearer_token(authorization: Optional[str]) -> Optional[str]:
    prefix = "Bearer "
    if not authorization or not authorization.startswith(prefix):
        return None
    return authorization[len(prefix):].strip()


def verify_api_key(authorization: Optional[str] = Header(default=None)) -> None:
    api_key = os.getenv(PYSITANT_API_KEY_ENV) or os.getenv(LEGACY_PYSITANT_API_KEY_ENV)
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail=f"{PYSITANT_API_KEY_ENV} is not configured on the server.",
        )

    token = get_bearer_token(authorization)
    if not token or not hmac.compare_digest(token, api_key):
        raise HTTPException(status_code=401, detail="Unauthorized")


def verify_session_token(authorization: Optional[str] = Header(default=None)) -> None:
    cleanup_expired_sessions()

    token = get_bearer_token(authorization)
    if not token or token not in active_sessions:
        raise HTTPException(status_code=401, detail="Session expired or unauthorized")

    active_sessions[token] = time.time()


class AskRequest(PydanticModel):
    prompt: str
    context: Dict[str, Any]
    provider: str 
    metadata: Optional[Dict[str, Any]] = None

class AskResponse(PydanticModel):
    answer: str
    provider: str

class SessionResponse(PydanticModel):
    session_token: str
    expires_in: int

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

async def session_cleanup_worker():
    print("[Session Cleanup Worker] Started.")
    while True:
        cleanup_expired_sessions()
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    workers = [asyncio.create_task(worker()) for _ in range(3)]
    outgoing = asyncio.create_task(outgoing_worker())
    session_cleanup = asyncio.create_task(session_cleanup_worker())
    print("[Server] 3 workers + 1 outgoing worker + 1 session cleanup worker started.")
    yield
    for w in workers:
        w.cancel()
    outgoing.cancel()
    session_cleanup.cancel()
    print("[Server] Workers stopped.")


app = FastAPI(title="Pysitant Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    cleanup_expired_sessions()
    return {
        "status": "ok",
        "incoming_queue": incoming_queue.qsize(),
        "outgoing_queue": outgoing_queue.qsize(),
        "active_sessions": len(active_sessions),
    }

@app.post("/api/session", response_model=SessionResponse)
async def create_session(_: None = Depends(verify_api_key)):
    cleanup_expired_sessions()

    session_token = secrets.token_urlsafe(32)
    active_sessions[session_token] = time.time()

    return SessionResponse(
        session_token=session_token,
        expires_in=get_session_timeout_seconds(),
    )

@app.post("/api/ask", response_model=AskResponse)
async def ask(
    request: AskRequest,
    _: None = Depends(verify_session_token),
    
):
    if incoming_queue.full():
        raise HTTPException(status_code=503, detail="Server is busy. Try again shortly.")

    job = Job(request)
    await incoming_queue.put(job)
    
    print(f"API key and session key : {request.context.get('api_key', 'N/A')}, {request.context.get('session_token', 'N/A')}")

    try:
        result = await asyncio.wait_for(job.future, timeout=40.0)
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request timed out.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
