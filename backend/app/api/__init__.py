from fastapi import APIRouter

from .admin_routes import router as admin_router
from .auth_routes import router as auth_router
from .feedback_routes import router as feedback_router
from .routes import router as sentiment_router
from .survey_workflow_routes import router as survey_workflow_router
from .teacher_dashboard_routes import router as teacher_dashboard_router
from .users_routes import router as users_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(admin_router)
router.include_router(teacher_dashboard_router)
router.include_router(survey_workflow_router)
router.include_router(feedback_router)
router.include_router(sentiment_router)

__all__ = ["router"]
