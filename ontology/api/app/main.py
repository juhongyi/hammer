from fastapi import FastAPI

from app.routers import router

app = FastAPI(title="Hammer Ontology API")
app.include_router(router)
