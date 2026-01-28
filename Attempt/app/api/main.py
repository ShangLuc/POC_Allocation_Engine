from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="POC Allocation Engine")

app.include_router(router)
