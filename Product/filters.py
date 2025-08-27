import django_filters
from django.db.models import Q
from .models import Product

class ProductFilter(django_filters.FilterSet):
    """
    商品过滤器
    提供对商品的高级过滤功能
    """
    # 标题模糊搜索
    title = django_filters.CharFilter(field_name='title', lookup_expr='icontains')
    
    # 描述模糊搜索
    description = django_filters.CharFilter(field_name='description', lookup_expr='icontains')
    
    # 价格范围过滤
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    
    # 分类过滤
    category = django_filters.NumberFilter(field_name='categories__category_id')
    
    # 状态过滤
    status = django_filters.NumberFilter(field_name='status')
    user_status = django_filters.NumberFilter(field_name='user__status')
    # 搜索字段 (同时搜索标题和描述)
    search = django_filters.CharFilter(method='filter_search')
    
    def filter_search(self, queryset, name, value):
        """
        搜索方法：同时在标题和描述中搜索关键词
        """
        return queryset.filter(
            Q(title__icontains=value) | 
            Q(description__icontains=value)
        )
    
    class Meta:
        model = Product
        fields = ['title', 'description', 'min_price', 'max_price', 'category', 'status', 'search','user_status']
