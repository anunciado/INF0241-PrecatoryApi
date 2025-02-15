from fastapi import APIRouter

from router.v1 import automacao, ia

router = APIRouter(
    prefix="/api/v1"
)

router.include_router(automacao.router)
router.include_router(ia.router)