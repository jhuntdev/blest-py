from fastapi import FastAPI, HTTPException, Request
from blest import create_request_handler

app = FastAPI()

async def hello(params, context):
  return {
    'hello': 'world',
    'bonjour': 'le monde',
    'hola': 'mundo',
    'hallo': 'welt'
  }

async def greet(params, context):
  return {
    'greeting': 'Hi, ' + params.get('name') + '!'
  }

async def fail(params, context):
  raise Exception('Intentional failure')

request_handler = create_request_handler({
  'hello': hello,
  'greet': greet,
  'fail': fail
})

@app.post('/')
async def index(request: Request):
  data = await request.json()
  result, error = await request_handler(data)
  if error:
    raise HTTPException(status_code=500, detail=error['message'])
  else:
    return result