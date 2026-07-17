import asyncio
import contextlib
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from .config import DATABASE_URL
from .db import Base, engine
from .routes import notifications, tasks
from .services import notify


@asynccontextmanager
async def lifespan(app: FastAPI):
    if DATABASE_URL.startswith("sqlite"):
        Path(DATABASE_URL.rpartition("///")[2]).parent.mkdir(
            parents=True, exist_ok=True
        )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    reminder_task = (
        asyncio.create_task(notify.reminder_loop()) if notify.enabled() else None
    )
    yield
    if reminder_task is not None:
        reminder_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await reminder_task
    await engine.dispose()


app = FastAPI(title="Tend", lifespan=lifespan)

api = FastAPI(title="Tend API")
api.include_router(tasks.router)
api.include_router(notifications.router)


@api.get("/health")
async def health():
    return {"status": "ok"}


app.mount("/api", api)
