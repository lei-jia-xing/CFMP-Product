from rest_framework import serializers
from .models import (
    Product,
    Category,
    ProductReview,
    Collection,
    ProductMedia,
)
from .user_utils import get_user_info


class CategorySerializer(serializers.ModelSerializer):
    class Meta:  # type: ignore
        model = Category
        fields = ["category_id", "name"]


class ProductMediaSerializer(serializers.ModelSerializer):
    class Meta:  # type: ignore
        model = ProductMedia
        fields = ["media_id", "media", "is_main", "created_at"]


class ProductSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    # 反向引用外键，需要使用related_name
    media = ProductMediaSerializer(many=True, read_only=True)
    # 用户信息字段，通过方法字段从用户服务获取
    user_info = serializers.SerializerMethodField()

    class Meta:  # type: ignore
        model = Product
        fields = [
            "product_id",
            "user_info",
            "title",
            "description",
            "price",
            "status",
            "created_at",
            "categories",
            "media",
            "function",
            "visit_count",
            "rating_avg",
            "stock",
        ]

    def get_user_info(self, obj):
        """获取用户信息"""
        return get_user_info(obj.user_id)


class ProductReviewSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(read_only=True)
    # 用户信息字段，通过方法字段从用户服务获取
    user_info = serializers.SerializerMethodField()

    class Meta:  # type: ignore
        model = ProductReview
        fields = [
            "review_id",
            "product",
            "user_info",
            "rating",
            "comment",
            "created_at",
        ]

    def get_user_info(self, obj):
        """获取用户信息"""
        return get_user_info(obj.user_id)


class CollectionSerializer(serializers.ModelSerializer):
    collection = ProductSerializer(read_only=True)
    # 用户信息字段，通过方法字段从用户服务获取
    collecter_info = serializers.SerializerMethodField()

    class Meta:  # type: ignore
        model = Collection
        fields = ["collection", "collecter_info", "create_at"]

    def get_collecter_info(self, obj):
        """获取收藏者信息"""
        return get_user_info(obj.collecter)
