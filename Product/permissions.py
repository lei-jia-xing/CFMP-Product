from rest_framework.permissions import BasePermission, SAFE_METHODS
from ProductService.user_service import user_service


class IsOwnerOrReadOnly(BasePermission):
    """
    通用权限类：对于GET等只读操作允许任何人访问
    对于修改和删除操作，只允许资源的拥有者
    支持网关认证（从请求头获取user_id，兼容查询参数）
    """

    message = "您没有权限执行此操作"

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        # 从网关获取当前用户ID
        current_user_id = request.META.get('HTTP_X_USER_UUID')
        if not current_user_id:
            return False

        # 判断资源属于谁
        if hasattr(obj, "user_id"):
            return str(obj.user_id) == str(current_user_id)
        elif hasattr(obj, "collecter"):
            return str(obj.collecter) == str(current_user_id)

        return False


class IsAdmin(BasePermission):
    """
    自定义管理员权限类：只允许管理员用户访问
    通过用户服务检查用户的privilege字段判断是否是管理员
    支持网关认证（从请求头获取user_id）
    """

    message = "只有管理员可以执行此操作"

    def has_permission(self, request, view):
        # 从网关获取当前用户ID
        current_user_id = request.META.get('HTTP_X_USER_UUID')
        if not current_user_id:
            return False
            
        # 通过用户服务检查用户权限
        privilege = user_service.check_user_privilege(current_user_id)
        return privilege == 1


class IsAuthenticatedViaGateway(BasePermission):
    """
    网关认证权限类：要求请求必须通过网关认证
    检查查询参数中是否包含有效的user_id
    """
    
    message = "需要通过网关认证"
    
    def has_permission(self, request, view):
        current_user_id = request.META.get('HTTP_X_USER_UUID')
        return current_user_id is not None
