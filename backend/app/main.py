from fastapi import FastAPI


app = FastAPI(title="AI Nutrition Coach API")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
