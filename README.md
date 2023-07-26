# BLEST Python

The Python reference implementation of BLEST (Batch-able, Lightweight, Encrypted State Transfer), an improved communication protocol for web APIs which leverages JSON, supports request batching and selective returns, and provides a modern alternative to REST. It includes examples for Django, FastAPI, and Flask.

To learn more about BLEST, please refer to the white paper: https://jhunt.dev/BLEST%20White%20Paper.pdf

For a front-end implementation in React, please visit https://github.com/jhuntdev/blest-react

## Features

- Built on JSON - Reduce parsing time and overhead
- Request Batching - Save bandwidth and reduce load times
- Compact Payloads - Save more bandwidth
- Selective Returns - Save even more bandwidth
- Single Endpoint - Reduce complexity and improve data privacy
- Fully Encrypted - Improve data privacy

## Installation

Install BLEST Python from PyPI.

```bash
python3 -m pip install blest
```

## Usage

This default export of this library is an API very similar to Flask or FastAPI. For convenience it also provides a `create_request_handler` function to create a request handler suitable for use in an existing application, a `create_http_server` function to create a standalone HTTP server, and a `create_http_client` function to create a BLEST HTTP client.


```python
from blest import Blest

app = new Blest({ 'timeout': 1000 })

@app.before_request
async def auth_middleware(params, context):
  if params.get('name'):
    context['user'] = {
      'name': params['name']
    }
  else:
    raise Exception('Unauthorized')

@app.route('greet')
async def greet_controller(params, context):
  return {
    'greeting': f"Hi, {context['user']['name']}!"
  }

if __name__ == '__main__':
  app.listen(8080)
```

### create_request_handler

The following example uses Flask, but you can find examples with other frameworks [here](examples).

```python
from flask import Flask, make_response, request
from blest import create_request_handler

# Create some middleware (optional)
async def auth_middleware(params, context):
  if params['name']:
    context['user'] = {
      'name': params['name']
    }
  else:
    raise Exception('Unauthorized')

# Create a route controller
async def greet_controller(params, context):
  return {
    'greeting': f"Hi, {context['user']['name']}!"
  }

# Create a request_handler
request_handler = create_request_handler({
  'greet': [auth_middleware, greet_controller]
})

app = Flask(__name__)

# Use the request handler
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
```

### create_http_server

```python
from blest import create_http_server, create_request_handler

# Create some middleware (optional)
async def auth_middleware(params, context):
  if params['name']:
    context['user'] = {
      'name': params['name']
    }
  else:
    raise Exception('Unauthorized')

# Create a route controller
async def greet_controller(params, context):
  return {
    'greeting': f"Hi, {context['user']['name']}!"
  }

# Create a request_handler
request_handler = create_request_handler({
  'greet': [auth_middleware, greet_controller]
})

run = create_http_server(request_handler)

if __name__ == '__main__':
  run()
```

### create_http_client

```python
from blest import create_http_client

# Create a client
request = create_http_client('http://localhost:8080')

async def main():
  # Send a request
  try:
    result = await request('greet', { 'name': 'Steve' }, ['greeting'])
    # Do something with the result
  except Exception as error:
    # Do something in case of error
```

## License

This project is licensed under the [MIT License](LICENSE).