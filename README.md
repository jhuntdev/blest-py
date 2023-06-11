# BLEST Python

The Python reference implementation of BLEST (Batch-able, Lightweight, Encrypted State Transfer), an improved communication protocol for web APIs which leverages JSON, supports request batching and selective returns, and provides a modern alternative to REST. It includes examples for Django, FastAPI, and Flask.

To learn more about BLEST, please refer to the white paper: https://jhunt.dev/BLEST%20White%20Paper.pdf

## Features

- JSON Payloads - Reduce parsing time and overhead
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

Use the `create_request_handler` function to create a request handler suitable for use in a Python application. The following example uses Flask, but you can find examples with other frameworks [here](/examples).

```python
from flask import Flask, make_response, request
from blest import create_request_handler

async def greet(params, context):
  return {
    'geeting': 'Hi, ' + params.get('name') + '!'
  }

router = create_request_handler({
  'greet': greet
})

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
import React from 'react';
import { useBlestRequest, useBlestCommand } from 'blest-react';

// Use the useBlestRequest hook for fetching data
const MyComponent = () => {
  const { data, loading, error } = useBlestRequest('listItems', { limit: 24 });

  // Render your component
  // ...
};

// Use the useBlestCommand hook for sending data
const MyForm = () => {
  const [submitMyForm, { data, loading, error }] = useBlestCommand('submitForm');

  // Render your form
  // ...
};
```

## Contributing

We actively welcome pull requests. Learn how to [contribute](CONTRIBUTING.md) for more information.

## License

This project is licensed under the [MIT License](LICENSE).