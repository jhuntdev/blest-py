import json
from django.http.response import JsonResponse
from . import router

async def index(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            result, error = await router(data)
            if error:
                return JsonResponse(error, status=500)
            else:
                return JsonResponse(result, status=200, safe=False)
        except json.JSONDecodeError:
            return JsonResponse({'message': 'Request body should be valid JSON'}, status=400)
    else:
        return JsonResponse({'message': 'Request should use the POST method'}, status=405)