from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from mcp_server.routes import router

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("NGOScope MCP Server starting...")
    yield
    print("NGOScope MCP Server shutting down...")


app = FastAPI(
    title="NGOScope MCP Server",
    description="AI-Powered NGO Trust & Transparency Platform - Tool Layer",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve the static frontend last so API routes (/tools, /health) keep precedence.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")