# BLEST Python

The Python reference implementation of BLEST (Batch-able, Lightweight, Encrypted State Transfer), an improved communication protocol for web APIs which leverages JSON, supports request batching by default, and provides a modern alternative to REST. It includes examples for Django, FastAPI, and Flask.

To learn more about BLEST, please visit the website: https://blest.jhunt.dev

For a front-end implementation in React, please visit https://github.com/jhuntdev/blest-react

## Features

- Built on JSON - Reduce parsing time and overhead
- Request Batching - Save bandwidth and reduce load times
- Compact Payloads - Save even more bandwidth
- Single Endpoint - Reduce complexity and facilitate introspection
- Fully Encrypted - Improve data privacy

## Installation

Install BLEST Python from PyPI.

```bash
python3 -m pip install blest
```

## Usage

### Router

The following example uses Flask, but you can find examples with other frameworks [here](examples).

```python
from flask import Flask, make_response, request
from blest import Router

# Instantiate the Router
router = Router({ 'timeout': 1000 })

# Create some middleware (optional)
@router.before_request
async def user_middleware(body, context):
  context['user'] = {
    # user info for example
  }
  return

# Create a route controller
@router.route('greet')
async def greet_controller(body, context):
  return {
    'greeting': f"Hi, {body['name']}!"
  }

# Instantiate a Flask application
app = Flask(__name__)

# Handle BLEST requests
@app.post('/')
async def index():
  result, error = await router.handle(request.json, { 'headers': request.headers })
  if error:
    resp = make_response(error, error.status or 500)
    resp.headers['Content-Type'] = 'application/json'
  else:
    resp = make_response(result, 200)
    resp.headers['Content-Type'] = 'application/json'
    return resp
```

### HttpClient

```python
from blest import HttpClient

async def main():
  # Create a client
  client = HttpClient('http://localhost:8080', {
    'max_batch_size': 25,
    'buffer_delay': 10,
    'http_headers': {
      'Authorization': 'Bearer token'
    }
  })

  # Send a request
  try:
    result = await client.request('greet', { 'name': 'Steve' })
    # Do something with the result
  except Exception as error:
    # Do something in case of error
```

## License

This project is licensed under the [MIT License](LICENSE).