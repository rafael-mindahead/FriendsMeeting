from fastapi import FastAPI

app = FastAPI(
    title = "FriendsMeeting API",
    description = "API de gerenciamento de usuarios e amizades",
    version = "0.1.0"
)
@app.get("/api/v1/health")
def health_check():
    return {
        "status": "ok",
        "service" : "FriendsMeeting",
        "version" : "0.1.0"
    }