from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.project import router as project_router
from app.routers.document import router as document_router

app = FastAPI(
    title="RAG Platform API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(project_router)
app.include_router(document_router)

@app.get("/health")
def health():
    return {
        "status": "ok",
    }