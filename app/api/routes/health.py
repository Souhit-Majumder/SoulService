from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def health_check():
    return {
        "service": "SoulService",
        "status": "ok",
        "version": "0.1.0",
    }