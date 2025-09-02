"""
简单的 Nacos 服务注册
"""
import os
import socket
import time
from nacos import NacosClient


def register_to_nacos():
    """注册服务到 Nacos"""
    try:
        # 等待网络连接就绪
        time.sleep(3)
        
        # Nacos 配置
        nacos_server = os.getenv('NACOS_SERVER', '123.57.145.79:8848')
        service_name = 'ProductService'
        environment = os.getenv('ENVIRONMENT', 'development')
        
        print(f"🌍 Current environment: {environment}")
        
        # 获取容器IP
        hostname = socket.gethostname()
        container_ip = socket.gethostbyname(hostname)
        
        # 在Kubernetes环境中，其他服务需要通过NodePort或者集群IP访问
        if environment == 'production':
            # 生产环境：硬编码使用服务器公网IP和NodePort
            service_ip = '101.132.163.45'  # 硬编码服务器公网IP
            service_port = 30800  # 硬编码NodePort端口
        else:
            # 开发环境：使用容器IP
            service_ip = container_ip
            service_port = int(os.getenv('SERVICE_PORT', '8000'))
        
        print(f"🔄 Connecting to Nacos server: {nacos_server}")
        print(f"🔄 Service will be registered as: {service_ip}:{service_port}")
        
        # 尝试连接 Nacos - 先尝试不使用认证
        client = None
        nacos_username = os.getenv('NACOS_USERNAME')
        nacos_password = os.getenv('NACOS_PASSWORD')
        
        try:
            if nacos_username and nacos_password:
                print(f"🔐 Attempting authenticated connection with user: {nacos_username}")
                client = NacosClient(
                    server_addresses=nacos_server, 
                    namespace='public',
                    username=nacos_username,
                    password=nacos_password
                )
            else:
                print("🔓 Attempting connection without authentication")
                client = NacosClient(
                    server_addresses=nacos_server, 
                    namespace='public'
                )
        except Exception as auth_error:
            print(f"⚠️ Authentication failed: {auth_error}")
            if nacos_username and nacos_password:
                print("🔄 Retrying without authentication...")
                client = NacosClient(
                    server_addresses=nacos_server, 
                    namespace='public'
                )
            else:
                raise auth_error
        
        print(f"🔄 Registering service: {service_name} at {service_ip}:{service_port}")
        
        # 注册服务 - 添加健康检查端点信息
        client.add_naming_instance(
            service_name=service_name,
            ip=service_ip,
            port=service_port,
            metadata={
                'version': '1.0.0',
                'environment': environment,
                'service_type': 'django-rest-api',
                'health_check_url': f'http://{service_ip}:{service_port}/health/',
                'instance_id': f'{service_name}-{service_ip}-{service_port}'
            },
            # 设置权重
            weight=1.0
        )
        
        print(f"✅ Service registered: {service_name} at {service_ip}:{service_port}")
        
        # 验证注册
        instances = client.list_naming_instance(service_name)
        print(f"📋 Found {len(instances.get('hosts', []))} instances for {service_name}")
        
        # 启动健康监控
        try:
            from .nacos_health import start_nacos_health_monitoring
            start_nacos_health_monitoring()
            print("💓 Nacos health monitoring started")
        except ImportError:
            print("⚠️ Health monitoring module not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to register service: {e}")
        import traceback
        traceback.print_exc()
        return False
