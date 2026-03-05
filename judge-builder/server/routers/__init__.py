"""API routers package."""

from fastapi import APIRouter

from .alignment import router as alignment_router
from .cache import router as cache_router
from .experiments import router as experiments_router
from .judge_builders import router as judge_builders_router
from .judges import router as judges_router
from .labeling import router as labeling_router
from .serving_endpoints import router as serving_endpoints_router
from .users import router as users_router

router = APIRouter()

router.include_router(judge_builders_router, prefix='/judge-builders', tags=['judge-builders'])
router.include_router(judges_router, prefix='/judges', tags=['judges'])
router.include_router(labeling_router, prefix='/labeling', tags=['labeling'])
router.include_router(alignment_router, prefix='/alignment', tags=['alignment'])
router.include_router(users_router, prefix='/users', tags=['users'])
router.include_router(experiments_router, prefix='/experiments', tags=['experiments'])
router.include_router(cache_router, prefix='/cache', tags=['cache'])
router.include_router(serving_endpoints_router, prefix='/serving-endpoints', tags=['serving-endpoints'])
