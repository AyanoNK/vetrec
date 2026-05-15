from fastapi import FastAPI

app = FastAPI(title="Case Timeline API")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
