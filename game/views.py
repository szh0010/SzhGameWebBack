from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt  # 必须加这个，否则前端 Axios 请求会报 403 Forbidden
def login_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                return JsonResponse({
                    'status': 'success', 
                    'user': user.username,
                    'msg': '登录成功'
                })
            else:
                return JsonResponse({
                    'status': 'error', 
                    'message': '用户名或密码错误'
                }, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': '仅支持 POST 请求'}, status=405)