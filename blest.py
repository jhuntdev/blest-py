# -------------------------------------------------------------------------------------------------
# BLEST (Batch-able, Lightweight, Encrypted State Transfer) - A modern alternative to REST
# (c) 2023-2024 JHunt <hello@jhunt.dev>
# License: MIT
# -------------------------------------------------------------------------------------------------
# Sample Request [id, route, body (optional), headers (optional)]
# [
#   [
#     "abc123",
#     "math",
#     {
#       "operation": "divide",
#       "dividend": 22,
#       "divisor": 7
#     },
#     {
#       "_s": ["result"]
#     }
#   ]
# ]
# -------------------------------------------------------------------------------------------------
# Sample Response [id, route, result, error (optional)]
# [
#   [
#     "abc123",
#     "math",
#     {
#       "status": "Successfully divided 22 by 7",
#       "result": {
#         "quotient": 3.1415926535
#       }
#     },
#     {
#       "message": "If there was an error you would see it here"
#     }
#   ]
# ]
# -------------------------------------------------------------------------------------------------

import traceback
import aiohttp
import asyncio
from uuid import uuid1 as uuid
import copy
import re

class Router:

  def __init__(self, options=None):
    self._middleware = []
    self._afterware = []
    self._timeout = 5000
    self._introspection = False
    self.routes = {}
    if options:
      self._timeout = options['timeout'] if options and 'timeout' in options else 5000
      self._introspection = options['introspection'] if options and 'introspection' in options else False

  def route(self, route):
    def decorator(handler):
      route_error = validate_route(route)
      if route_error:
        raise ValueError(route_error)
      elif route in self.routes:
        raise ValueError('Route already exists')
      elif not handler or not callable(handler):
        raise ValueError('Handler should be a function')
      self.routes[route] = {
        'handler': [*self._middleware, handler, *self._afterware],
        'description': None,
        'schema': None,
        'visible': self._introspection,
        'validate': False,
        'timeout': self._timeout
      }
    return decorator

  def before_request(self):
    def decorator(middleware):
      self._middleware.append(middleware)
    return decorator
  middleware = before_request
  before = before_request

  def add_middleware(self, middleware):
    self._middleware.append(middleware)

  def after_request(self):
    def decorator(afterware):
      self._afterware.append(afterware)
    return decorator
  afterware = after_request
  after = after_request

  def describe(self, route: str, config: dict):
    if route not in self.routes:
      raise ValueError('Route does not exist')
    elif not isinstance(config, dict):
      raise ValueError('Configuration should be an object')

    if 'description' in config:
      if config['description'] is not None and not isinstance(config['description'], str):
        raise ValueError('Description should be a str')
      self.routes[route]['description'] = config['description']

    if 'schema' in config:
      if config['schema'] is not None and not isinstance(config['schema'], dict):
        raise ValueError('Schema should be a dict')
      self.routes[route]['schema'] = config['schema']

    if 'visible' in config:
      if config['visible'] is not None and config['visible'] not in [True, False]:
        raise ValueError('Visible should be True or False')
      self.routes[route]['visible'] = config['visible']

    if 'validate' in config:
      if config['validate'] is not None and config['validate'] not in [True, False]:
        raise ValueError('Validate should be True or False')
      self.routes[route]['validate'] = config['validate']

    if 'timeout' in config:
      if config['timeout'] is not None and not isinstance(config['timeout'], int) or config['timeout'] <= 0:
        raise ValueError('Timeout should be a positive int')
      self.routes[route]['timeout'] = config['timeout']

  def merge(self, router):
    if not router or not isinstance(router, Router):
      raise ValueError('Router is required')

    new_routes = list(router.routes.keys())
    existing_routes = list(self.routes.keys())

    if not new_routes:
      raise ValueError('No routes to merge')

    for route in new_routes:
      if route in existing_routes:
        raise ValueError('Cannot merge duplicate routes: ' + route)
      else:
        self.routes[route] = {
          **router.routes[route],
          'handler': self._middleware + router.routes[route]['handler'] + self._afterware,
          'timeout': router.routes[route].get('timeout', self._timeout)
        }

  def namespace(self, prefix, router):
    if not router or not isinstance(router, type(self)):
      raise ValueError('Router is required')

    prefix_error = validate_route(prefix)
    if prefix_error:
      raise ValueError(prefix_error)

    new_routes = list(router.routes.keys())
    existing_routes = list(self.routes.keys())

    if not new_routes:
      raise ValueError('No routes to namespace')

    for route in new_routes:
      ns_route = f"{prefix}/{route}"
      if ns_route in existing_routes:
        raise ValueError('Cannot merge duplicate routes: ' + ns_route)
      else:
        self.routes[ns_route] = {
          **router.routes[route],
          'handler': self._middleware + router.routes[route]['handler'] + self._afterware,
          'timeout': router.routes[route].get('timeout', self._timeout)
        }

  async def handle(self, request, context=None):
    return await handle_request(self.routes, request, context)



class EventEmitter:
  def __init__(self):
    self.listeners = {}
  def once(self, name, listener):
    if name not in self.listeners:
      self.listeners[name] = []
    self.listeners[name].append(listener)
  def emit(self, name, *args):
    if name in self.listeners:
      for listener in self.listeners[name]:
        listener(*args)
      del self.listeners[name]



class BlestError(Exception):
  def __init__(self, message='Internal Server Error', status=500, code=None, data=None):
    self.message = message
    self.status = status
    self.code = code
    self.data = data
    super().__init__(self.message)



class HttpClient:
  def __init__(self, url, max_batch_size=25, batch_delay=10, http_headers={}):
    self._url = url
    self._max_batch_size = max_batch_size
    self._batch_delay = batch_delay
    self._http_headers = http_headers
    self._timer = False
    self._queue = []
    self._emitter = EventEmitter()

  async def _delay(self, func, time):
    await asyncio.sleep(time / 1000)
    await func()

  async def _process(self):
    new_queue = self._queue[:self._max_batch_size]
    del self._queue[:self._max_batch_size]
    if len(self._queue) == 0:
      self._timer = False
    else:
      self._timer = True
      asyncio.create_task(self._delay(self._process, self._batch_delay))
    async with aiohttp.ClientSession() as session:
      try:
        response = await session.post(self._url, json=new_queue, headers=self._http_headers.update({'Accept': 'application/json', 'Content-Type': 'application/json'}))
        response.raise_for_status()
        response_json = await response.json()
        for r in response_json:
          self._emitter.emit(r[0], r[2], r[3])
      except aiohttp.ClientError as e:
        for q in new_queue:
          self._emitter.emit(q[0], None, response_json)
  
  async def request(self, route, body=None, headers=None):
    if not route:
      raise ValueError('Route is required')
    elif body and not isinstance(body, dict):
      raise ValueError('Body should be a dict')
    elif headers and not isinstance(headers, dict):
      raise ValueError('Headers should be a dict')
    id = str(uuid())
    future = asyncio.Future()
    def callback(result, error):
      if error:
        future.set_exception(Exception(error['message']))
      else:
        future.set_result(result)
    self._emitter.once(id, callback)
    self._queue.append([id, route, body, headers])
    if self._timer == False:
      self._timer = True
      asyncio.create_task(self._delay(self._process, self._batch_delay))
    result = await future
    return result



route_regex = r"^[a-zA-Z][a-zA-Z0-9_\-\/]*[a-zA-Z0-9]$"
system_route_regex = r"^_[a-zA-Z][a-zA-Z0-9_\-\/]*[a-zA-Z0-9]$"

def validate_route(route, system=False):
    if not route:
        return 'Route is required'
    elif system and not re.match(system_route_regex, route):
        routeLength = len(route)
        if routeLength < 3:
            return 'System route should be at least three characters long'
        elif route[0] != '_':
            return 'System route should start with an underscore'
        elif not re.match(r"[a-zA-Z0-9]", route[-1]):
            return 'System route should end with a letter or a number'
        else:
            return 'System route should contain only letters, numbers, dashes, underscores, and forward slashes'
    elif not system and not re.match(route_regex, route):
        routeLength = len(route)
        if routeLength < 2:
            return 'Route should be at least two characters long'
        elif not re.match(r"[a-zA-Z]", route[0]):
            return 'Route should start with a letter'
        elif not re.match(r"[a-zA-Z0-9]", route[-1]):
            return 'Route should end with a letter or a number'
        else:
            return 'Route should contain only letters, numbers, dashes, underscores, and forward slashes'
    elif re.search(r"\/[^a-zA-Z]", route):
        return 'Sub-routes should start with a letter'
    elif re.search(r"[^a-zA-Z0-9]\/", route):
        return 'Sub-routes should end with a letter or a number'
    elif re.search(r"\/[a-zA-Z0-9_\-]{0,1}\/", route):
        return 'Sub-routes should be at least two characters long'
    elif re.search(r"\/[a-zA-Z0-9_\-]$", route):
        return 'Sub-routes should be at least two characters long'
    elif re.search(r"^[a-zA-Z0-9_\-]\/", route):
        return 'Sub-routes should be at least two characters long'
    return None



async def handle_request(routes, requests, context):
  if not requests or not isinstance(requests, list):
    return handle_error(400, 'Request should be an array')
  batch_id = uuid()
  unique_ids = []
  promises = []
  for i in range(len(requests)):
    request = requests[i]
    # request_length = len(request)
    if not isinstance(request, list):
      return handle_error(400, 'Request item should be an array')
    id = request[0] if len(request) > 0 else None
    route = request[1] if len(request) > 1 else None
    body = request[2] if len(request) > 2 else None
    headers = request[3] if len(request) > 3 else None
    if not id or not isinstance(id, str):
      return handle_error(400, 'Request item should have an ID')
    if not route or not isinstance(route, str):
      return handle_error(400, 'Request items should have a route')
    if body and not isinstance(body, dict):
      return handle_error(400, 'Request item body should be an object')
    if headers and not isinstance(headers, list):
      return handle_error(400, 'Request item headers should be an object')
    if id in unique_ids:
      return handle_error(400, 'Request items should have unique IDs')
    unique_ids.append(id)
    this_route = routes.get(route)
    route_handler = None
    if isinstance(this_route, dict):
      route_handler = this_route.get('handler') or route_not_found
    else:
      route_handler = this_route or route_not_found
    request_object = {
      'id': id,
      'route': route,
      'body': body or {},
      'headers': headers
    }
    my_context = {
      **(context or {}),
      'batch_id': batch_id,
      'request_id': id,
      'route': route,
      'headers': headers
    }
    promises.append(route_reducer(route_handler, request_object, my_context, this_route.get('timeout') if this_route else None))
  results = await asyncio.gather(*promises)
  return handle_result(results)



def handle_result(result):
  return result, None



def handle_error(status, message):
  return None, {
    'status': status,
    'message': message
  }



def route_not_found(*args):
  raise BlestError('Not Found', status=404)



async def route_reducer(handler, request, context, timeout=None):
  
  safe_context = copy.deepcopy(context)
  safe_body = request['body'] or {}
  route = request['route']
  result = None

  async def target():
    nonlocal result
    if isinstance(handler, list):
      for i in range(len(handler)):
        temp_result = None
        if asyncio.iscoroutinefunction(handler[i]):
          temp_result = await handler[i](safe_body, safe_context)
        elif callable(handler[i]):
          loop = asyncio.get_event_loop()
          temp_result = await loop.run_in_executor(None, handler[i], safe_body, safe_context)
        else:
          print(f'Tried to resolve route "{route}" with handler of type "{type(handler[i])}"')
          return [request['id'], request['route'], None, { 'message': 'Internal Server Error', 'status': 500 }]
        if temp_result and temp_result is not None:
          if result and result is not None:
            print(f'Multiple handlers on the route "{route}" returned results')
            return [request['id'], request['route'], None, { 'message': 'Internal Server Error', 'status': 500 }]
          else:
            result = temp_result
    else:
      if asyncio.iscoroutinefunction(handler):
        result = await handler(safe_body, safe_context)
      elif callable(handler):
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, handler, safe_body, safe_context)
      else:
        print(f'Tried to resolve route "{route}" with handler of type "{type(handler)}"')
        return [request['id'], request['route'], None, { 'message': 'Internal Server Error', 'status': 500 }]
    return result

  try:
    if timeout is not None and timeout > 0:
      try:
        timeout_ms = timeout / 1000
        await asyncio.wait_for(target(), timeout=timeout_ms)
      except asyncio.exceptions.TimeoutError:
        print(f'The route "{route}" timed out after {timeout} milliseconds')
        return [request['id'], request['route'], None, {'message': 'Internal Server Error', 'status': 500}]
    else:
      await target()

    if result is None or not isinstance(result, dict):
      print(f'The route "{route}" did not return a result object')
      return [request['id'], request['route'], None, { 'message': 'Internal Server Error', 'status': 500 }]
    if request.get('headers') and request['headers'].get('_s'):
      result = filter_object(result, request['headers']['_s'])
    return [request['id'], request['route'], result, None]
  except Exception as error:
    traceback.print_exc()
    responseError = {
      'message': str(error) or 'Internal Server Error',
      'status': error.status or 500 if hasattr(error, 'status') else 500
    }
    if hasattr(error, 'code') and isinstance(error.code, str):
      responseError['code'] = error.code
    if hasattr(error, 'data') and isinstance(error.data, dict):
      responseError['data'] = error.data
    return [request['id'], request['route'], None, responseError]



async def execute_async_functions(functions):
  results = []
  for function in functions:
    result = await function()
    results.append(result)
  return results



def filter_object(obj, arr):
  if isinstance(arr, list):
    filtered_obj = {}
    for i in range(len(arr)):
      key = arr[i]
      if isinstance(key, str):
        if key in obj:
          filtered_obj[key] = obj[key]
      elif isinstance(key, list):
        nested_obj = obj[key[0]]
        nested_arr = key[1]
        if isinstance(nested_obj, list):
          filtered_arr = []
          for j in range(len(nested_obj)):
            filtered_nested_obj = filter_object(nested_obj[j], nested_arr)
            if len(filtered_nested_obj) > 0:
              filtered_arr.append(filtered_nested_obj)
          if len(filtered_arr) > 0:
            filtered_obj[key[0]] = filtered_arr
        elif isinstance(nested_obj, dict):
          filtered_nested_obj = filter_object(nested_obj, nested_arr)
          if len(filtered_nested_obj) > 0:
            filtered_obj[key[0]] = filtered_nested_obj
    return filtered_obj
  return obj
