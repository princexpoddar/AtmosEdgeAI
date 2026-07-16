from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.endpoints import router

app = FastAPI(title="AtmosEdgeAI API", version="1.0.0")

# Enable CORS for frontend dashboard connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to the AtmosEdgeAI API. Visit /docs for documentation."}
