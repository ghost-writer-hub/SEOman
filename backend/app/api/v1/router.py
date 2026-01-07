"""
API v1 router aggregating all endpoints.
"""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.sites import router as sites_router
from app.api.v1.audits import router as audits_router
from app.api.v1.keywords import router as keywords_router
from app.api.v1.plans import router as plans_router
from app.api.v1.content import router as content_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.analyze import router as analyze_router
from app.api.v1.audit_v2 import router as audit_v2_router

api_router = APIRouter()

api_router.include_router(analyze_router)
api_router.include_router(audit_v2_router)
api_router.include_router(auth_router)
api_router.include_router(tenants_router)
api_router.include_router(sites_router)
api_router.include_router(audits_router)
api_router.include_router(keywords_router)
api_router.include_router(plans_router)
api_router.include_router(content_router)
api_router.include_router(dashboard_router)
