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

from aiohttp import web
import asyncio
import json
import copy
import os

def create_server(routes, options=None):
  request_handler = create_request_handler(routes, options)
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

def create_request_handler(routes, options=None):
  if options:
    print('The "options" argument is not yet used, but may be used in the future.')
  async def handler(requests, context={}):
    if not requests or not isinstance(requests, list):
      return handle_error(400, 'Request body should be a JSON array')
    dedupe = []
    promises = []
    for i in range(len(requests)):
      request = requests[i]
      if not isinstance(request, list) or len(request) < 2 or not isinstance(request[0], str) or not isinstance(request[1], str):
        return handle_error(400, 'Request items should be an array with a unique ID and an route')
      if len(request) > 2 and request[2] and not isinstance(request[2], dict):
        return handle_error(400, 'Request item parameters should be a JSON object')
      if len(request) > 3 and request[3] and not isinstance(request[3], list):
        return handle_error(400, 'Request item selector should be a JSON array')
      if request[0] in dedupe:
        return handle_error(400, 'Request items should have unique IDs')
      dedupe.append(request[0])
      request_object = {
        'id': request[0],
        'route': request[1],
        'params': request[2] if (len(request) > 2) else None,
        'selector': request[3] if (len(request) > 3) else None
      }
      route_handler = routes.get(request[1]) or route_not_found
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
    if type(handler) is list:
      for i in range(len(handler)):
        if asyncio.iscoroutinefunction(handler[i]):
          temp_result = await handler[i](request['params'], safe_context)
        else:
          temp_result = handler[i](request['params'], safe_context)
        if i == len(handler) - 1:
          result = temp_result
        elif temp_result:
          raise Exception('Middleware should not return anything but may mutate context')
    else:
      if asyncio.iscoroutinefunction(handler):
        result = await handler(request['params'], safe_context)
      else:
        result = handler(request['params'], safe_context)
    if not isinstance(result, dict):
      raise Exception('Result should be a JSON object')
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
