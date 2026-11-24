from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy import inspect, text
from app.api import admin_comments, auth, public_comments
from app.core.config import settings
from app.db.session import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    comment_columns = {column["name"] for column in inspect(engine).get_columns("comments")}
    if "profile_picture" not in comment_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE comments ADD COLUMN profile_picture TEXT"))
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="IITA @60 public comment wall with ML-assisted moderation.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(public_comments.router)
app.include_router(auth.router)
app.include_router(admin_comments.router)


@app.get("/api/v1/health", tags=["Health"])
def health():
    return {"status": "ok", "service": settings.app_name}
