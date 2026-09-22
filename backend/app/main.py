"""
SecureQuery Track C - FastAPI Core Gateway
Endpoints:
- POST /auth/login, /auth/me, /auth/test-dpdp, /auth/test-risk, /auth/audit-log
- POST /query/ask (real per-user JWT query pipeline)
- POST /api/query (dashboard query pipeline)
- GET /api/analytics/trends (Historical multi-hospital trends)
- GET /api/analytics/hospital-comparison (Condition breakdown across nodes)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="SecureQuery API",
    description="Privacy-Preserving Cross-Hospital Clinical Data Analytics Framework",
    version="3.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Mount real database-backed routers
# -----------------------------------------------------------------------------
from app.routers.auth import router as auth_router
from app.routers.query import router as query_router
from app.routers.dashboard import router as dashboard_router

app.include_router(auth_router)
app.include_router(query_router)
app.include_router(dashboard_router)

app.mount("/dashboard", StaticFiles(directory="app/static_dashboard", html=True), name="static_dashboard")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)