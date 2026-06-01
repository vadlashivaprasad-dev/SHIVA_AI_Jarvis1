from fastapi import FastAPI

app = FastAPI(title="ShivaAI Jarvis - Backend")


@app.get("/health")
def health():
    return {"status": "healthy"}

