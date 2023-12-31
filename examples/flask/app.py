from flask import Flask, make_response, request
from blest import Router

app = Flask(__name__)

router = Router()

@router.route('hello')
async def hello(params, context):
  return {
    'hello': 'world',
    'bonjour': 'le monde',
    'hola': 'mundo',
    'hallo': 'welt'
  }

@router.route('greet')
async def greet(params, context):
  return {
    'greeting': 'Hi, ' + params.get('name') + '!'
  }

@router.route('fail')
async def fail(params, context):
  raise Exception('Intentional failure')

@app.post('/')
async def index():
  headers = dict(request.headers)
  result, error = await router.handle(request.json, { 'headers': headers })
  if error:
    resp = make_response(error, 500)
    resp.headers['Content-Type'] = 'application/json'
  else:
    resp = make_response(result, 200)
    resp.headers['Content-Type'] = 'application/json'
    return resp