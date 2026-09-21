from fastapi import FastAPI
from app.routers import auth, query

app = FastAPI(title="SecureQuery API")
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for local dev/demo; restrict in real deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(query.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "SecureQuery Track A"}