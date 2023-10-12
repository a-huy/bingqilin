from bingqilin import initialize


app = initialize()
if not app:
    raise RuntimeError("FastAPI app not initialized.")


@app.get("/")
async def ping():
    return {"pong": True}
