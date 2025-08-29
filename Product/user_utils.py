"""
用户相关的序列化器和工具类
用于处理从用户服务获取的用户数据
"""
from rest_framework import serializers
from ProductService.user_service import user_service


class UserInfoSerializer(serializers.Serializer):
    """用户信息序列化器（用于显示从用户服务获取的数据）"""
    user_id = serializers.UUIDField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.CharField(read_only=True, required=False)
    avatar = serializers.URLField(read_only=True, required=False)
    status = serializers.IntegerField(read_only=True, required=False)  # 0=正常, 1=封禁
    privilege = serializers.IntegerField(read_only=True, required=False)  # 权限级别
    address = serializers.CharField(read_only=True, required=False)
    created_at = serializers.DateTimeField(read_only=True, required=False)


def get_user_info(user_id):
    """
    获取用户信息的辅助函数
    
    Args:
        user_id: 用户ID
        
    Returns:
        dict: 用户信息字典，如果获取失败返回基本信息
    """
    if not user_id:
        return None
        
    user_info = user_service.get_user_by_id(user_id)
    if user_info:
        return {
            'user_id': user_info.get('user_id'),
            'username': user_info.get('username', 'Unknown User'),
            'avatar': user_info.get('avatar'),
            'email': user_info.get('email'),
            'status': user_info.get('status', 0),
            'privilege': user_info.get('privilege', 0),
            'address': user_info.get('address')
        }
    else:
        # 如果用户服务不可用，返回基本信息
        return {
            'user_id': user_id,
            'username': 'Unknown User',
            'avatar': None,
            'email': None,
            'status': 0,
            'privilege': 0,
            'address': None
        }
