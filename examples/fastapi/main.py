import random
from fastapi import FastAPI, HTTPException, Request
from blest import Router

app = FastAPI()

router = Router()

@router.route('hello')
async def hello(body, context):
  return random.choice([
    { 'hello': 'world' },
    { 'bonjour': 'le monde' },
    { 'hola': 'mundo' },
    { 'hallo': 'welt' }
  ])

@router.route('greet')
async def greet(body, context):
  return {
    'greeting': 'Hi, ' + body.get('name') + '!'
  }

@router.route('fail')
async def fail(body, context):
  raise Exception('Intentional failure')

@app.post('/')
async def index(request: Request):
  data = await request.json()
  headers = dict(request.headers)
  result, error = await router.handle(data, { 'headers': headers })
  if error:
    raise HTTPException(status_code=500, detail=error['message'])
  else:
    return result