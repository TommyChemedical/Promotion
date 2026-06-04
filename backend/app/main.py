from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import sources as sources_router
from app.api import search as search_router
from app.api import summarize as summarize_router
from app.api import export as export_router

app = FastAPI(title="LiteraturKI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sources_router.router)
app.include_router(search_router.router)
app.include_router(summarize_router.router)
app.include_router(export_router.router)


@app.on_event("startup")
def startup():
    from app.database import init_db
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}
