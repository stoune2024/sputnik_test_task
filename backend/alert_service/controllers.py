from src.schemas import AlertItem
from src.service import (
    list_alerts,
)
from backend.alert_service.routers import alert_router


@alert_router.get("/alerts", response_model=list[AlertItem])
async def list_alerts_view():
    return await list_alerts()
