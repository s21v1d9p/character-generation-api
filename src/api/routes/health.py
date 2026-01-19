from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/")
async def root() -> dict[str, str]:
    return {"message": "Character Generation API", "version": "0.1.0"}
