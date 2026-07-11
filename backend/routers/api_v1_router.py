from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.alert_service.routers import alert_router
from backend.file_service.routers import file_router


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alert_router)
app.include_router(file_router)
