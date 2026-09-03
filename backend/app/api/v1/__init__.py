from fastapi import APIRouter

from app.api.v1 import (
    health,
    ai,
    meetings,
    search,
    knowledge,
    auth,
    audit,
    bots,
    exports,
    webhooks,
    sso,
    integrations,
    calendar,
    realtime,
    settings,
    members,
    oidc,
    billing,
    stripe_webhooks,
    gdpr,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(meetings.router, prefix="/meetings", tags=["meetings"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(bots.router, prefix="/bots", tags=["bots"])
api_router.include_router(exports.router, prefix="/exports", tags=["exports"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(sso.router, prefix="/sso", tags=["sso"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
api_router.include_router(realtime.router, prefix="/realtime", tags=["realtime"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(members.router, prefix="/members", tags=["members"])
api_router.include_router(oidc.router, prefix="/oidc", tags=["oidc"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(stripe_webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(gdpr.router, prefix="/gdpr", tags=["gdpr"])
