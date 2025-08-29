"""
URL configuration for ProductService project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from .health_views import nacos_health_check

# 启动时注册到 Nacos
try:
    from .nacos_register import register_to_nacos
    register_to_nacos()
except ImportError:
    print("⚠️ Nacos registration module not found")

urlpatterns = [
    # Nacos 健康检查端点
    path('health/', nacos_health_check, name='nacos_health_check'),
    
    # API 端点
    path('api/', include('Product.urls')),
]
