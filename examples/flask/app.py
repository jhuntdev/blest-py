from flask import Flask, make_response, request
from blest import create_request_handler

app = Flask(__name__)

async def hello(params, context):
  return {
    'hello': 'world',
    'bonjour': 'le monde',
    'hola': 'mundo',
    'hallo': 'welt'
  }

async def greet(params, context):
  return {
    'geeting': 'Hi, ' + params.get('name') + '!'
  }

async def fail(params, context):
  raise Exception('Intentional failure')

request_handler = create_request_handler({
  'hello': hello,
  'greet': greet,
  'fail': fail
})

@app.post('/')
async def index():
  result, error = await request_handler(request.json)
  if error:
    resp = make_response(error, 500)
    resp.headers['Content-Type'] = 'application/json'
  else:
    resp = make_response(result, 200)
    resp.headers['Content-Type'] = 'application/json'
    return resp