"""
用户服务客户端
通过 Nacos 服务发现调用 UserService 获取用户信息
"""
import requests
import logging
from nacos import NacosClient
import os
from datetime import datetime
logger = logging.getLogger(__name__)


class UserServiceClient:
    """用户服务客户端"""
    
    def __init__(self):
        self.service_name = 'UserService'
        self.nacos_client = None
        self._init_nacos_client()
    
    def _init_nacos_client(self):
        """初始化 Nacos 客户端"""
        try:
            nacos_server = os.getenv('NACOS_SERVER', '123.57.145.79:8848')
            self.nacos_client = NacosClient(
                server_addresses=nacos_server, 
                namespace='public',
                username=os.getenv('NACOS_USERNAME', 'nacos'),
                password=os.getenv('NACOS_PASSWORD', 'no5groupnacos')
            )
            logger.info(f"Initialized Nacos client for UserService discovery: {nacos_server}")
        except Exception as e:
            logger.error(f"Failed to initialize Nacos client: {e}")
    
    def _get_service_url(self):
        """获取用户服务的 URL"""
        if not self.nacos_client:
            return None
            
        try:
            instances = self.nacos_client.list_naming_instance(self.service_name)
            hosts = instances.get('hosts', [])
            
            # 找到健康的实例
            healthy_hosts = [host for host in hosts if host.get('healthy', False)]
            if not healthy_hosts:
                logger.warning(f"No healthy instances found for {self.service_name}")
                return None
                
            # 简单的负载均衡：使用第一个健康的实例
            host = healthy_hosts[0]
            return f"http://{host['ip']}:{host['port']}"
            
        except Exception as e:
            logger.error(f"Failed to get service URL for {self.service_name}: {e}")
            return None
    
    def get_user_by_id(self, user_id):
        """根据用户ID获取用户信息"""
        service_url = self._get_service_url()
        if not service_url:
            logger.error("UserService not available")
            return None
        
        try:
            # 使用实际的 API 路径
            url = f"{service_url}/api/v1/user/{user_id}/"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    def get_followers(self, user_id):
        """获取用户的关注者列表（关注该用户的人）"""
        service_url = self._get_service_url()
        if not service_url:
            logger.error("UserService not available")
            return []
        
        try:
            # 获取关注者列表 - 使用 followee 接口（该用户作为被关注者）
            url = f"{service_url}/api/v1/user/followee/"
            # 需要传递用户认证信息，这里假设有某种方式获取认证令牌
            # 实际使用时需要根据认证方式调整
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            # 过滤出关注指定用户的关注者
            all_follows = response.json()
            followers = []
            for follow_relation in all_follows:
                if str(follow_relation.get('followee')) == str(user_id):
                    # 获取关注者的用户信息
                    follower_info = self.get_user_by_id(follow_relation.get('follower'))
                    if follower_info:
                        followers.append(follower_info)
            
            return followers
        except Exception as e:
            logger.error(f"Failed to get followers for user {user_id}: {e}")
            return []
    
    def check_user_privilege(self, user_id):
        """检查用户权限级别"""
        user_info = self.get_user_by_id(user_id)
        if user_info:
            return user_info.get('privilege', 0)
        return 0


# 全局用户服务客户端实例
user_service = UserServiceClient()
