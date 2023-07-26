# -------------------------------------------------------------------------------------------------
# BLEST (Batch-able, Lightweight, Encrypted State Transfer) - A modern alternative to REST
# (c) 2023 JHunt <blest@jhunt.dev>
# License: MIT
# -------------------------------------------------------------------------------------------------
# Sample Request [id, route, parameters (optional), selector (optional)]
# [
#   [
#     "abc123",
#     "math",
#     {
#       "operation": "divide",
#       "dividend": 22,
#       "divisor": 7
#     },
#     ["status",["result",["quotient"]]]
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
from aiohttp import web
import asyncio
import uuid
import json
import copy
import os
import re
import time
import threading
from datetime import datetime

class Router:

  def __init__(self, options=None):
    self._middleware = []
    self._afterware = []
    self._errorhandler = None
    self._introspection = False
    self._timeout = 5000
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
        'parameters': None,
        'result': None,
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

  def errorhandler(self):
    def decorator(errorhandler):
      self._errorhandler = errorhandler
    return decorator

  def describe(self, route: str, config: dict):
    if route not in self.routes:
      raise ValueError('Route does not exist')
    elif not isinstance(config, dict):
      raise ValueError('Configuration should be an object')

    if 'description' in config:
      if config['description'] is not None and not isinstance(config['description'], str):
        raise ValueError('Description should be a str')
      self.routes[route]['description'] = config['description']

    if 'parameters' in config:
      if config['parameters'] is not None and not isinstance(config['parameters'], dict):
        raise ValueError('Parameters should be a dict')
      self.routes[route]['parameters'] = config['parameters']

    if 'result' in config:
      if config['result'] is not None and not isinstance(config['result'], dict):
        raise ValueError('Result should be a dict')
      self.routes[route]['result'] = config['result']

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



class Blest(Router):

  def __init__(self, router_options=None, server_options=None):
    self.server_options = server_options
    super().__init__(router_options)

  def listen(self, **args):
    request_handler = create_request_handler(self.routes, self._errorhandler)
    server = create_http_server(request_handler, self.server_options)
    server(*args)



def create_http_server(request_handler, options=None):
  if options:
    options_error = validate_server_options(options)
    if options_error:
      raise ValueError(options_error)

  url = options['url'] if options and 'url' in options else '/'

  http_headers = {
    'access-control-allow-origin': options['accessControlAllowOrigin'] if options and 'accessControlAllowOrigin' in options else ('*' if options and 'cors' in options and (isinstance(options['cors'], str) or options['cors'] is True) else ''),
    'content-security-policy': options['contentSecurityPolicy'] if options and 'contentSecurityPolicy' in options else "default-src 'self';base-uri 'self';font-src 'self' https: data:;form-action 'self';frame-ancestors 'self';img-src 'self' data:;object-src 'none';script-src 'self';script-src-attr 'none';style-src 'self' https: 'unsafe-inline';upgrade-insecure-requests",
    'cross-origin-opener-policy': options['crossOriginOpenerPolicy'] if options and 'crossOriginOpenerPolicy' in options else 'same-origin',
    'cross-origin-resource-policy': options['crossOriginResourcePolicy'] if options and 'crossOriginResourcePolicy' in options else 'same-origin',
    'origin-agent-cluster': options['originAgentCluster'] if options and 'originAgentCluster' in options else '?1',
    'referrer-policy': options['referrerPolicy'] if options and 'referrerPolicy' in options else 'no-referrer',
    'strict-transport-security': options['strictTransportSecurity'] if options and 'strictTransportSecurity' in options else 'max-age=15552000; includeSubDomains',
    'x-content-type-options': options['xContentTypeOptions'] if options and 'xContentTypeOptions' in options else 'nosniff',
    'x-dns-prefetch-control': options['xDnsPrefetchOptions'] if options and 'xDnsPrefetchOptions' in options else 'off',
    'x-download-options': options['xDownloadOptions'] if options and 'xDownloadOptions' in options else 'noopen',
    'x-frame-options': options['xFrameOptions'] if options and 'xFrameOptions' in options else 'SAMEORIGIN',
    'x-permitted-cross-domain-policies': options['xPermittedCrossDomainPolicies'] if options and 'xPermittedCrossDomainPolicies' in options else 'none',
    'x-xss-protection': options['xXssProtection'] if options and 'xXssProtection' in options else '0'
  }

  async def handle_req(request):
    if request.path == url:
      if request.method == 'POST':
        try:
          json_data = await request.json()
        except json.JSONDecodeError as error:
          return web.Response(status=400, headers=http_headers, text=str(error))
        try:
          context = {'headers': {key: value for key, value in request.headers.items()}}
          result, error = await request_handler(json_data, context)
          if error:
            return web.Response(status=error['status'] if hasattr(error, 'status') else 500, headers=http_headers, text=str(error))
          elif result:
            json_result = json.dumps(result)
            return web.Response(text=json_result, status=200, headers={ 'Content-Type': 'application/json', **http_headers })
          else:
            return web.Response(status=500, headers=http_headers)
        except Exception as error:
          print(error)
          return web.Response(status=500, headers=http_headers, text=str(error))
      elif request.method == 'OPTIONS':
        return web.Response(status=204, headers=http_headers)
      else:
        return web.Response(status=405, headers=http_headers)
    else:
      return web.Response(status=404, headers=http_headers)

  app = web.Application()
  app.router.add_route('*', '/{tail:.*}', handle_req)
  
  def run(port=os.getenv('PORT') or 8080, host=os.getenv('HOST') or 'localhost'):
    web.run_app(app, port=port, host=host)

  return run



def validate_server_options(options):
  if not options:
    return None
  elif not isinstance(options, dict):
    return 'Options should be an object'
  else:
    if 'url' in options:
      if not isinstance(options['url'], str):
        return '"url" option should be a str'
      elif not options['url'].startswith('/'):
        return '"url" option should begin with a forward slash'
    if 'cors' in options:
      if not isinstance(options['cors'], (str, bool)):
        return '"cors" option should be a str or bool'
  return None



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



def create_http_client(url, options=None):
  if options:
    print('The "options" argument is not yet used, but may be used in the future')
  max_batch_size = 100
  queue = []
  timer = None
  emitter = EventEmitter()
  async def process():
    nonlocal queue
    nonlocal timer
    new_queue = queue[:max_batch_size]
    del queue[:max_batch_size]
    if not queue:
      timer = None
    else:
      timer = asyncio.create_task(process())
    async with aiohttp.ClientSession() as session:
      try:
        response = await session.post(url, json=new_queue, headers={'Accept': 'application/json', 'Content-Type': 'application/json'})
        response.raise_for_status()
        response_json = await response.json()
        for r in response_json:
          emitter.emit(r[0], r[2], r[3])
      except aiohttp.ClientError as e:
        for q in new_queue:
          emitter.emit(q[0], None, response_json)
  async def request(route, params=None, selector=None):
    nonlocal timer
    if not route:
      raise ValueError('Route is required')
    elif params and not isinstance(params, dict):
      raise ValueError('Params should be a dict')
    elif selector and not isinstance(selector, list):
      raise ValueError('Selector should be a list')
    id = str(uuid.uuid4())
    future = asyncio.Future()
    def callback(result, error):
      if error:
        future.set_exception(Exception(error['message']))
      else:
        future.set_result(result)
    emitter.once(id, callback)
    queue.append([id, route, params, selector])
    if not timer:
      timer = asyncio.create_task(process())
    return await future
  return request



def create_request_handler(routes, error_handler=None):
  route_keys = list(routes.keys())
  my_routes = {}

  for i in range(len(route_keys)):
    key = route_keys[i]
    route_error = validate_route(key)
    if route_error:
      raise Exception(f'{route_error}: {key}')

    route = routes.get(key)
    
    if isinstance(route, list):
      if not route:
        raise Exception(f'Route has no handlers: {key}')
      
      for j in range(len(route)):
        if not callable(route[j]):
          raise Exception(f'All route handlers must be functions: {key}')
        
      my_routes[key] = {'handler': route}
    
    elif isinstance(route, dict):
      if 'handler' not in route:
        raise Exception(f'Route has no handlers: {key}')
      
      if not isinstance(route['handler'], list):
        if not callable(route['handler']):
          raise Exception(f'Route handler is not valid: {key}')
        my_routes[key] = {
          **route,
          'handler': [route['handler']]
        }
      else:
        for j in range(len(route['handler'])):
          if not callable(route['handler'][j]):
            raise Exception(f'All route handlers must be functions: {key}')    
        my_routes[key] = route.copy()
    
    elif callable(route):
      my_routes[key] = {'handler': [route]}
    
    else:
      raise Exception(f'Route is missing handler: {key}')

  async def handler(requests, context={}):
    return await handle_request(my_routes, requests, context, error_handler)

  return handler



route_regex = r"^[a-zA-Z][a-zA-Z0-9_\-\/]*[a-zA-Z0-9]$"

def validate_route(route):
    if not route:
        return 'Route is required'
    elif not re.match(route_regex, route):
        routeLength = len(route)
        if routeLength < 2:
            return 'Route should be at least two characters long'
        elif route[-1] == '/':
            return 'Route should not end in a forward slash'
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



async def handle_request(routes, requests, context, error_handler=None):
  if not requests or not isinstance(requests, list):
    return handle_error(400, 'Requests should be a list')
  unique_ids = []
  promises = []
  for i in range(len(requests)):
    request = requests[i]
    request_length = len(request)
    if not isinstance(request, list):
      return handle_error(400, 'Request item should be an array')
    id = request[0] if len(request) > 0 else None
    route = request[1] if len(request) > 1 else None
    parameters = request[2] if len(request) > 2 else None
    selector = request[3] if len(request) > 3 else None
    if not id or not isinstance(id, str):
      return handle_error(400, 'Request item should have an ID')
    if not route or not isinstance(route, str):
      return handle_error(400, 'Request items should have a route')
    if parameters and not isinstance(parameters, dict):
      return handle_error(400, 'Request item parameters should be a dict')
    if selector and not isinstance(selector, list):
      return handle_error(400, 'Request item selector should be a list')
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
      'parameters': parameters or {},
      'selector': selector
    }
    my_context = {
      'requestId': id,
      'routeName': route,
      'selector': selector,
      'requestTime': int(datetime.now().timestamp()),
      **(context or {})
    }
    promises.append(route_reducer(route_handler, request_object, my_context, this_route.get('timeout') if this_route else None, error_handler))
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



async def route_reducer(handler, request, context, timeout=None, error_handler=None):
  
  safe_context = copy.deepcopy(context)
  route = request['route']
  result = None

  async def target():
    nonlocal result
    if isinstance(handler, list):
      for i in range(len(handler)):
        temp_result = None
        if asyncio.iscoroutinefunction(handler[i]):
          temp_result = await handler[i](request['parameters'], safe_context)
        else:
          temp_result = handler[i](request['parameters'], safe_context)
        if temp_result and temp_result is not None:
          if result and result is not None:
            print(f'Multiple handlers on the route "{route}" returned results')
            return [request['id'], request['route'], None, { 'message': 'Internal Server Error', 'status': 500 }]
          else:
            result = temp_result
    else:
      if asyncio.iscoroutinefunction(handler):
        result = await handler(request['parameters'], safe_context)
      elif callable(handler):
        result = handler(request['parameters'], safe_context)
      else:
        print(f'Tried to resolve route "{route}" with handler of type "{type(handler)}')
        return [request['id'], request['route'], None, {'message': 'Internal Server Error', 'status': 500}]
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
    if request['selector']:
      result = filter_object(result, request['selector'])
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
