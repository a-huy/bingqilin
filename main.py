from fastapi import FastAPI

from bingqilin import initialize


app = FastAPI()

initialize(app)


@app.get("/")
async def ping():
    return {"pong": True}
