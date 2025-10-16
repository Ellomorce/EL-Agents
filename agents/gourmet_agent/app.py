import os
from contextlib import asynccontextmanager
from typing import Optional
from pathlib import Path
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from dotenv import load_dotenv

load_dotenv()

# Get Current Directory
AGENTS_DIR = str(Path(__file__).parent.resolve())

# Load Params
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "4201"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ALLOW_ORIGINS = os.getenv("ALLOW_ORIGINS", "*").split(",") if os.getenv("ALLOW_ORIGINS") else ["*"]

# 可選的服務 URI 配置
SESSION_SERVICE_URI = os.getenv("SESSION_SERVICE_URI")
ARTIFACT_SERVICE_URI = os.getenv("ARTIFACT_SERVICE_URI")
MEMORY_SERVICE_URI = os.getenv("MEMORY_SERVICE_URI")
TRACE_TO_CLOUD = os.getenv("TRACE_TO_CLOUD", "false").lower() == "true"

#
if SESSION_SERVICE_URI == "":
    SESSION_SERVICE_URI = None
if ARTIFACT_SERVICE_URI == "":
    ARTIFACT_SERVICE_URI = None
if MEMORY_SERVICE_URI == "":
    MEMORY_SERVICE_URI = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期管理
    可以在這裡添加啟動時的初始化邏輯和關閉時的清理邏輯
    """
    # 啟動時執行
    print(f"🚀 Starting ADK Agent API Server...")
    print(f"📁 Agents Directory: {AGENTS_DIR}")
    print(f"🌐 Host: {HOST}:{PORT}")
    
    yield
    
    # 關閉時執行
    print("👋 Shutting down ADK Agent API Server...")

# 
app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    session_service_uri=SESSION_SERVICE_URI,
    artifact_service_uri=ARTIFACT_SERVICE_URI,
    memory_service_uri=MEMORY_SERVICE_URI,
    allow_origins=ALLOW_ORIGINS,
    web=False,
    trace_to_cloud=False,
    lifespan=lifespan,
)

#
# @app.get("/health")
# async def health_check():
#     """健康檢查端點"""
#     return {
#         "status": "healthy",
#         "agents_dir": AGENTS_DIR,
#         "service": "ADK Agent API"
#     }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level=LOG_LEVEL.lower()
    )