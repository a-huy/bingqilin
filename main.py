from fastapi import FastAPI

from bingqilin import initialize


app = initialize()


@app.get("/")
async def ping():
    return {"pong": True}
