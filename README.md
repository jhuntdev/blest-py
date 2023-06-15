# BLEST Python

The Python reference implementation of BLEST (Batch-able, Lightweight, Encrypted State Transfer), an improved communication protocol for web APIs which leverages JSON, supports request batching and selective returns, and provides a modern alternative to REST. It includes examples for Django, FastAPI, and Flask.

To learn more about BLEST, please refer to the white paper: https://jhunt.dev/BLEST%20White%20Paper.pdf

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
pip install blest
```

## Usage

### Server-side

Use the `create_server` function to create a standalone HTTP server, or use the `create_request_handler` function to create a request handler suitable for use in an existing Python application. Both functions allow you to define middleware in your router.

### create_server

```python
from blest import create_server

# Create some middleware (optional)
def auth_middleware(params, context):
  if params.name:
    context.user = {
      'name': params.name
    }
  else:
    raise Exception('Unauthorized')

# Create a route controller
def greet_controller(params, context):
  return {
    'greeting': f'Hi, {context.user.name}!'
  }

# Define your router
router = {
  'greet': [auth_middleware, greet_controller]
}

run = create_server(router)

if __name__ == '__main__':
  run()
```

### create_request_handler

The following example uses Flask, but you can find examples with other frameworks [here](examples).

```python
from flask import Flask, make_response, request
from blest import create_request_handler

async def greet(params, context):
  return {
    'geeting': 'Hi, ' + params.get('name') + '!'
  }

routes = {
  'greet': greet
}

router = create_request_handler(routes)

app = Flask(__name__)

@app.post('/')
async def index():
  result, error = await router(request.json)
  if error:
    resp = make_response(error, 500)
    resp.headers['Content-Type'] = 'application/json'
  else:
    resp = make_response(result, 200)
    resp.headers['Content-Type'] = 'application/json'
    return resp
```

### Client-side

Client-side libraries assist in batching and processing requests and commands. Currently available for React with other frameworks coming soon.

#### React

```javascript
import React from 'react'
import { useBlestRequest, useBlestCommand } from 'blest-react'

// Use the useBlestRequest hook for fetching data
const MyComponent = () => {
  const { data, loading, error } = useBlestRequest('listItems', { limit: 24 })

  return (
    // Render your component
  )
}

// Use the useBlestCommand hook for sending data
const MyForm = () => {
  const [submitMyForm, { data, loading, error }] = useBlestCommand('submitForm')
  
  const handleSubmit = (values) => {
    return submitMyForm(values)
  }

  return (
    // Render your form
  )
}
```

## Contributing

We actively welcome pull requests. Learn how to [contribute](CONTRIBUTING.md) for more information.

## License

This project is licensed under the [MIT License](LICENSE).