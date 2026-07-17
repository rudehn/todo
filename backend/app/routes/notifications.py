from fastapi import APIRouter, HTTPException

from .. import config
from ..schemas import NotificationStatus
from ..services import notify

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/status", response_model=NotificationStatus)
async def status():
    return NotificationStatus(
        enabled=notify.enabled(),
        url=config.NTFY_URL,
        topic=config.NTFY_TOPIC,
        timezone=config.TIMEZONE,
    )


@router.post("/test")
async def send_test():
    if not notify.enabled():
        raise HTTPException(
            status_code=400,
            detail="Notifications are not configured; set NTFY_TOPIC on the backend",
        )
    try:
        await notify.publish(
            title="Tend test notification",
            message="Reminders are working. You'll get a ping when a task is coming up.",
            tags="white_check_mark",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ntfy publish failed: {exc}")
    return {"ok": True}
