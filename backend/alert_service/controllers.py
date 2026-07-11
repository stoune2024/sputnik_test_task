from backend.alert_service.models import AlertItem
from backend.alert_service.service import (
    list_alerts,
)
from backend.alert_service.routers import alert_router
from backend.repository import SessionDep


@alert_router.get("/alerts", response_model=list[AlertItem])
async def list_alerts_view(session: SessionDep):
    return await list_alerts(session)
