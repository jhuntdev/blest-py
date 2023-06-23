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

import aiohttp
from aiohttp import web
import asyncio
import uuid
import json
import copy
import os
import re

def create_http_server(request_handler, options=None):
  if options:
    print('The "options" argument is not yet used, but may be used in the future')
  async def post_handler(request):
    try:
      json_data = await request.json()
    except ValueError:
      return web.Response(status=400)
    result, error = await request_handler(json_data, {})
    if error:
      print(error)
      raise web.Response(status=500)
    elif result:
      result_json = json.dumps(result)
      return web.Response(text=result_json, content_type='application/json')
    else:
      print(Exception('Request handler failed to return anything'))
      raise web.Response(status=500)
  app = web.Application()
  app.add_routes([web.post('/', post_handler)])
  def run(port=os.getenv('PORT') or 8080):
    web.run_app(app, port=port)
  return run

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

def create_request_handler(routes, options=None):
  if options:
    print('The "options" argument is not yet used, but may be used in the future.')
  route_regex = r'^[a-zA-Z][a-zA-Z0-9_\-\/]*[a-zA-Z0-9_\-]$'
  async def handler(requests, context={}):
    if not requests or not isinstance(requests, list):
      return handle_error(400, 'Requests should be a list')
    unique_ids = []
    promises = []
    for i in range(len(requests)):
      request = requests[i]
      request_length = len(request)
      if not isinstance(request, list):
        return handleError(400, 'Request item should be an array')
      id = request[0] if len(request) > 0 else None
      route = request[1] if len(request) > 1 else None
      parameters = request[2] if len(request) > 2 else None
      selector = request[3] if len(request) > 3 else None
      if not id or not isinstance(id, str):
        return handleError(400, 'Request item should have an ID')
      if not route or not isinstance(route, str):
        return handleError(400, 'Request items should have a route')
      if not re.match(route_regex, route):
        route_length = len(route)
        if route_length < 2:
          return handleError(400, 'Request item route should be at least two characters long')
        elif route[route_length - 1] == '/':
          return handleError(400, 'Request item route should not end in a forward slash')
        elif not re.match(r'[a-zA-Z]', route[0]):
          return handleError(400, 'Request item route should start with a letter')
        else:
          return handleError(400, 'Request item routes should contain only letters, numbers, dashes, underscores, and forward slashes')
      if parameters and not isinstance(parameters, dict):
        return handle_error(400, 'Request item parameters should be a dict')
      if selector and not isinstance(selector, list):
        return handle_error(400, 'Request item selector should be a list')
      if id in unique_ids:
        return handle_error(400, 'Request items should have unique IDs')
      unique_ids.append(id)
      route_handler = routes.get(route) or route_not_found
      request_object = {
        'id': id,
        'route': route,
        'parameters': parameters,
        'selector': selector
      }
      promises.append(route_reducer(route_handler, request_object, context))
    results = await asyncio.gather(*promises)
    return handle_result(results)
  return handler

def handle_result(result):
  return result, None

def handle_error(code, message, headers=None):
  return None, {
    'code': code,
    'message': message,
    'headers': headers
  }

def route_not_found(*args):
  raise Exception('Route not found')

async def route_reducer(handler, request, context):
  try:
    safe_context = copy.deepcopy(context)
    if isinstance(handler, list):
      for i in range(len(handler)):
        if asyncio.iscoroutinefunction(handler[i]):
          temp_result = await handler[i](request['parameters'], safe_context)
        else:
          temp_result = handler[i](request['parameters'], safe_context)
        if i == len(handler) - 1:
          result = temp_result
        elif temp_result:
          raise Exception('Middleware should not return anything but may mutate context')
    else:
      if asyncio.iscoroutinefunction(handler):
        result = await handler(request['parameters'], safe_context)
      else:
        result = handler(request['parameters'], safe_context)
    if not isinstance(result, dict):
      raise Exception('Result should be a dict')
    if request['selector']:
      result = filter_object(result, request['selector'])
    return [request['id'], request['route'], result, None]
  except Exception as error:
    return [request['id'], request['route'], None, { 'message': str(error) }]

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
  return {}
