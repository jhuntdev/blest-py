from flask import Flask, make_response, request
import router

app = Flask(__name__)

@app.post('/')
async def index():
  result, error = await router.router(request.json)
  if error:
    resp = make_response(error, 500)
    resp.headers['Content-Type'] = 'application/json'
  else:
    resp = make_response(result, 200)
    resp.headers['Content-Type'] = 'application/json'
    return resp