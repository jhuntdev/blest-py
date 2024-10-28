import json
from django.http.response import JsonResponse
from blest import Router

router = Router()

@router.route('hello')
async def hello(body, context):
  return {
    'hello': 'world',
    'bonjour': 'le monde',
    'hola': 'mundo',
    'hallo': 'welt'
  }

@router.route('greet')
async def greet(body, context):
  return {
    'greeting': 'Hi, ' + body.get('name') + '!'
  }

@router.route('fail')
async def fail(body, context):
  raise Exception('Intentional failure')

async def index(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            headers = {}
            for key, value in request.META.items():
              if key.startswith('HTTP_'):
                header_key = key[5:].replace('_', '-').title()
                headers[header_key] = value
            result, error = await router.handle(data, { 'headers': headers })
            if error:
                return JsonResponse(error, status=500)
            else:
                return JsonResponse(result, status=200, safe=False)
        except json.JSONDecodeError:
            return JsonResponse({'message': 'Request body should be valid JSON'}, status=400)
    else:
        return JsonResponse({'message': 'Request should use the POST method'}, status=405)