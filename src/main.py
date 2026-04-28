from fastapi import FastAPI

app = FastAPI(title="Pose API", version="1.0.0")

@app.get("/")
def read_root():
    return {"message": "Welcome to Pose API"}

@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}
