import json
from django.http.response import JsonResponse
from blest import create_request_handler

async def hello(params, context):
  return {
    'hello': 'world',
    'bonjour': 'le monde',
    'hola': 'mundo',
    'hallo': 'welt'
  }

async def greet(params, context):
  return {
    'greeting': 'Hi, ' + params.get('name') + '!'
  }

async def fail(params, context):
  raise Exception('Intentional failure')

request_handler = create_request_handler({
  'hello': hello,
  'greet': greet,
  'fail': fail
})

async def index(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            result, error = await request_handler(data)
            if error:
                return JsonResponse(error, status=500)
            else:
                return JsonResponse(result, status=200, safe=False)
        except json.JSONDecodeError:
            return JsonResponse({'message': 'Request body should be valid JSON'}, status=400)
    else:
        return JsonResponse({'message': 'Request should use the POST method'}, status=405)