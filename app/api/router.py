from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.xml_test import router as xml_router
from app.api.routes.listings import router as listings_router

router = APIRouter(prefix="/api/v1")

router.include_router(health_router, prefix="/health", tags=["Health"])
router.include_router(xml_router, prefix="/xml", tags=["XML"])
router.include_router(listings_router, prefix="/listings", tags=["Listings"])