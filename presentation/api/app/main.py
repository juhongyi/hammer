from fastapi import FastAPI

from app.routers import router

app = FastAPI(title="Presentation API")
app.include_router(router)
