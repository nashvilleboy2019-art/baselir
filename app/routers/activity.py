from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.utils import require_login, paginate
from app.templates_config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def activity_log(request: Request, db: Session = Depends(get_db), page: int = 1):
    user = require_login(request, db)
    query = db.query(models.ActivityLog).order_by(models.ActivityLog.timestamp.desc())
    paged = paginate(query, page, per_page=100)
    return templates.TemplateResponse(request, "activity/log.html", {
        "user": user,
        "active": "activity",
        "paged": paged,
    })
