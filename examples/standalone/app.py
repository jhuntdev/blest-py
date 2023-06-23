from blest import create_request_handler, create_http_server

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

server = create_http_server(request_handler)

server.run()