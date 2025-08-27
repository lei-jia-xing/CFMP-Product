from rest_framework import serializers
from .models import (
    Product,
    Category,
    ProductReview,
    Collection,
    ProductMedia,
)


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
    # 使用不敏感的序列化方式
    # user = PublicUserSerializer(read_only=True)
    # 反向引用外键，需要使用related_name
    media = ProductMediaSerializer(many=True, read_only=True)

    class Meta:  # type: ignore
        model = Product
        fields = [
            "product_id",
            "user_id",
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
        ]


class ProductReviewSerializer(serializers.ModelSerializer):
    # user = PublicUserSerializer(read_only=True)
    product = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:  # type: ignore
        model = ProductReview
        fields = [
            "review_id",
            "product",
            "user_id",
            "rating",
            "comment",
            "created_at",
        ]


class CollectionSerializer(serializers.ModelSerializer):
    # collecter = PublicUserSerializer(read_only=True)
    collection = ProductSerializer(read_only=True)

    class Meta:  # type: ignore
        model = Collection
        fields = ["collection", "collecter", "create_at"]
