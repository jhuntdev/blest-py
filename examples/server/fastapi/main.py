from fastapi import FastAPI, HTTPException, Request
from . import router

app = FastAPI()

@app.post('/')
async def index(request: Request):
  data = await request.json()
  result, error = await router.router(data)
  if error:
    raise HTTPException(status_code=500, detail=error['message'])
  else:
    return result