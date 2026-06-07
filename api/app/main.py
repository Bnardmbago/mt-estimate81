from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin.rate_cards import router as admin_rate_cards_router
from app.auth.router import router as auth_router
from app.documents.router import router as documents_router
from app.estimates.router import router as estimates_router
from app.exports.router import router as exports_router

app = FastAPI(title="AI Estimate API", version="0.1.0")

app.include_router(auth_router)
app.include_router(estimates_router)
app.include_router(documents_router)
app.include_router(admin_rate_cards_router)
app.include_router(exports_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
