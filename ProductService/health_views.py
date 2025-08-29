"""
健康检查视图 - 专门用于 Nacos 心跳检查
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import time
import os


@csrf_exempt
@require_http_methods(["GET"])
def nacos_health_check(request):
    """
    Nacos 健康检查端点 - 简单的心跳检查
    返回服务的健康状态，用于 Nacos 的心跳机制
    """
    try:
        return JsonResponse({
            'status': 'UP',
            'timestamp': int(time.time() * 1000),
            'service': 'ProductService',
            'message': 'Service is healthy'
        }, status=200)
    except Exception as e:
        return JsonResponse({
            'status': 'DOWN',
            'timestamp': int(time.time() * 1000),
            'service': 'ProductService',
            'error': str(e)
        }, status=503)