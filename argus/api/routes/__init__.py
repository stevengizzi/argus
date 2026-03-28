"""API route handlers.

Each module defines a router that is aggregated into the main api_router.
All routes are mounted under /api/v1 prefix.
"""

from fastapi import APIRouter

from argus.api.routes.account import router as account_router
from argus.api.routes.ai import router as ai_router
from argus.api.routes.auth import router as auth_router
from argus.api.routes.briefings import router as briefings_router
from argus.api.routes.config import router as config_router
from argus.api.routes.controls import router as controls_router
from argus.api.routes.counterfactual import router as counterfactual_router
from argus.api.routes.dashboard import router as dashboard_router
from argus.api.routes.debrief_search import router as debrief_search_router
from argus.api.routes.documents import router as documents_router
from argus.api.routes.health import router as health_router
from argus.api.routes.intelligence import router as intelligence_router
from argus.api.routes.learning import router as learning_router
from argus.api.routes.journal import router as journal_router
from argus.api.routes.market import router as market_router
from argus.api.routes.orchestrator import router as orchestrator_router
from argus.api.routes.performance import router as performance_router
from argus.api.routes.positions import router as positions_router
from argus.api.routes.quality import router as quality_router
from argus.api.routes.session import router as session_router
from argus.api.routes.strategies import router as strategies_router
from argus.api.routes.trades import router as trades_router
from argus.api.routes.universe import router as universe_router
from argus.api.routes.vix import router as vix_router
from argus.api.routes.watchlist import router as watchlist_router

# Main API router that aggregates all route modules
api_router = APIRouter()

# Mount all route modules
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(account_router, tags=["account"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(positions_router, prefix="/positions", tags=["positions"])
api_router.include_router(trades_router, prefix="/trades", tags=["trades"])
api_router.include_router(performance_router, prefix="/performance", tags=["performance"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(strategies_router, prefix="/strategies", tags=["strategies"])
api_router.include_router(controls_router, prefix="/controls", tags=["controls"])
api_router.include_router(orchestrator_router, prefix="/orchestrator", tags=["orchestrator"])
api_router.include_router(session_router, tags=["session"])
api_router.include_router(watchlist_router, prefix="/watchlist", tags=["watchlist"])
api_router.include_router(market_router, prefix="/market", tags=["market"])
api_router.include_router(config_router, prefix="/config", tags=["config"])
api_router.include_router(briefings_router, prefix="/debrief/briefings", tags=["debrief"])
api_router.include_router(documents_router, prefix="/debrief/documents", tags=["debrief"])
api_router.include_router(journal_router, prefix="/debrief/journal", tags=["debrief"])
api_router.include_router(debrief_search_router, prefix="/debrief", tags=["debrief"])
api_router.include_router(ai_router, prefix="/ai", tags=["ai"])
api_router.include_router(universe_router, prefix="/universe", tags=["universe"])
api_router.include_router(intelligence_router, tags=["intelligence"])
api_router.include_router(quality_router, prefix="/quality", tags=["quality"])
api_router.include_router(
    counterfactual_router, prefix="/counterfactual", tags=["counterfactual"]
)
api_router.include_router(vix_router, prefix="/vix", tags=["vix"])
api_router.include_router(learning_router, prefix="/learning", tags=["learning"])
