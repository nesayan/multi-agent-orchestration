
import logging
from typing import Optional

from pydantic import BaseModel
from langgraph.errors import GraphRecursionError

from core.config import settings
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import StreamingResponse

from agents import load_all_agents
from agents.master import invoke_master_agent, stream_master_agent
from agents.masterV2 import invoke_masterV2_agent, stream_masterV2_agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(module)s] %(levelname)s: %(message)s")
logging.getLogger("httpx").propagate = False
logging.getLogger("openai").propagate = False
logging.getLogger("httpcore").propagate = False
logging.getLogger("langchain").propagate = False
logging.getLogger("langsmith").propagate = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up the application...")

    await load_all_agents()
    
    yield

    print("Shutting down the application...")

app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Health check endpoint

@app.get("/health")
async def health_check():
    return JSONResponse(content={"status": "ok"})


# 2. API endpoint to run the master agent

class QueryRequest(BaseModel):
    query: str
    thread_id: Optional[str] = "default"
    
@app.post("/query")
async def run_master_agent_endpoint(request: QueryRequest):
    query = request.query
    thread_id = request.thread_id
    if not query:
        return JSONResponse(content={"error": "Query is required"}, status_code=400)
    
    # result = await invoke_master_agent(query, thread_id)
    result = await invoke_masterV2_agent(query, thread_id)
    return JSONResponse(content={"result": result})


# 3. Streaming endpoint (SSE) — master V1

@app.post("/query/stream")
async def stream_agent_endpoint(request: QueryRequest):
    query = request.query
    thread_id = request.thread_id
    if not query:
        return JSONResponse(content={"error": "Query is required"}, status_code=400)

    async def event_generator():
        try:
            # async for token in stream_master_agent(query, thread_id):
            async for token in stream_masterV2_agent(query, thread_id):
                yield f"data: {token}\n\n"
        except GraphRecursionError:
            yield f"data: I'm having trouble processing this query. Could you provide more specific details so I can help you better?\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    port = int(settings.port)
    uvicorn.run(app, host="0.0.0.0", port=port)