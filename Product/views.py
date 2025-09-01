import uuid
import logging

from django.db import transaction
from django.db.models import Avg
from rest_framework.parsers import MultiPartParser
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend

from .pagination import StandardResultsSetPagination
from rest_framework.response import Response
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.views import APIView
from .models import (
    Product,
    Category,
    ProductReview,
    Collection,
    ProductMedia,
)
from .serializers import (
    ProductReviewSerializer,
    CategorySerializer,
    CollectionSerializer,
    ProductSerializer,
    ProductMediaSerializer,
)
from .filters import ProductFilter
from ProductService.user_service import user_service

logger = logging.getLogger(__name__)

# 商品相关视图


class ProductListCreateAPIView(ListCreateAPIView):
    serializer_class = ProductSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter

    def get_queryset(
        self,
    ):
        """
        sort_by = 0 表示按创建时间倒序
        sort_by = 1 表示按热度倒序
        sort_by = 2 表示按价格升序
        sort_by = 3 表示按价格降序
        sort_by = 4 表示按评分倒序
        """
        # 如果查询参数sort_by存在，则按指定字段排序
        sort_by = self.request.query_params.get("sort_by")
        if sort_by is not None:
            if sort_by == "0":
                return Product.objects.all().order_by("-created_at")
            elif sort_by == "1":
                return Product.objects.all().order_by("-visit_count")
            elif sort_by == "2":
                return Product.objects.all().order_by("price")
            elif sort_by == "3":
                return Product.objects.all().order_by("-price")
            elif sort_by == "4":
                return Product.objects.all().order_by("-rating_avg")
        return Product.objects.all().order_by("-created_at")

    def perform_create(self, serializer):
        # 获取当前用户ID（来自网关）
        current_user_id = self.request.headers.get('UUID')
        
        # 保存商品基本信息
        product = serializer.save(user_id=current_user_id, status=3)

        # 获取当前创建商品的用户信息
        seller_info = user_service.get_user_by_id(current_user_id)
        
        if seller_info:
            logger.info(f"Product {product.title} created by user {seller_info.get('username')}")
            

        # 处理分类
        if "categories" in self.request.data:
            category_ids = (
                self.request.data.getlist("categories")
                if hasattr(self.request.data, "getlist")
                else self.request.data.get("categories", [])
            )
            if not isinstance(category_ids, list):
                category_ids = [category_ids]

            for category_id in category_ids:
                try:
                    category = Category.objects.get(category_id=category_id)
                    product.categories.add(category)
                except Category.DoesNotExist:
                    pass  # 忽略不存在的分类

        # 处理上传的图片
        if "media" in self.request.FILES:
            media_files = self.request.FILES.getlist("media")

            # 第一张图片设为主图
            is_first = True

            for media_file in media_files:
                # 创建媒体文件记录
                media_file.name = f"{product.product_id}+'_'+{uuid.uuid4().hex}.jpg"
                ProductMedia.objects.create(
                    product=product,
                    media=media_file,
                    is_main=is_first,  # 第一张图片设为主图
                )

                # 更新标志
                if is_first:
                    is_first = False


# 商品图片相关视图
class ProductMediaListView(APIView):
    """
    商品图片列表相关操作

    GET: 获取商品的所有图片
    POST: 为商品添加图片
    """


    def get(self, request, product_id):
        """获取商品的所有图片"""
        try:
            product = Product.objects.get(product_id=product_id)
            media = ProductMedia.objects.filter(product=product)
            serializer = ProductMediaSerializer(media, many=True)
            return Response(serializer.data)
        except Product.DoesNotExist:
            return Response({"detail": "商品不存在"}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, product_id):
        """为商品添加图片"""
        try:
            # 检查商品是否存在
            product = Product.objects.get(product_id=product_id)

            # 处理上传的图片
            if "media" in request.FILES:
                media_files = request.FILES.getlist("media")

                # 检查是否已有主图
                has_main_image = ProductMedia.objects.filter(
                    product=product, is_main=True
                ).exists()
                set_as_main = not has_main_image  # 如果没有主图，则将第一张设为主图

                created_media = []
                for media_file in media_files:
                    media = ProductMedia.objects.create(
                        product=product, media=media_file, is_main=set_as_main
                    )
                    created_media.append(media)

                    # 更新标志
                    if set_as_main:
                        set_as_main = False

                serializer = ProductMediaSerializer(created_media, many=True)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {"detail": "未提供图片"}, status=status.HTTP_400_BAD_REQUEST
                )

        except Product.DoesNotExist:
            return Response({"detail": "商品不存在"}, status=status.HTTP_404_NOT_FOUND)


class ProductMediaDetailView(APIView):
    """
    单个商品图片操作

    GET: 获取单个图片详情
    PUT: 更新图片（如设置为主图）
    DELETE: 删除图片
    """


    def get(self, request, product_id, media_id):
        """获取单个图片详情"""
        try:
            product = Product.objects.get(product_id=product_id)
            media = ProductMedia.objects.get(media_id=media_id, product=product)
            serializer = ProductMediaSerializer(media)
            return Response(serializer.data)
        except Product.DoesNotExist:
            return Response({"detail": "商品不存在"}, status=status.HTTP_404_NOT_FOUND)
        except ProductMedia.DoesNotExist:
            return Response({"detail": "图片不存在"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, product_id, media_id):
        """更新图片信息（如设置为主图）"""
        try:
            # 检查商品是否存在
            product = Product.objects.get(product_id=product_id)

            # 检查用户是否有权限
            current_user_id = self.request.headers.get('UUID')
            if str(current_user_id) != str(product.user_id):
                return Response(
                    {"detail": "您没有权限修改此商品"}, status=status.HTTP_403_FORBIDDEN
                )

            # 获取图片
            media = ProductMedia.objects.get(media_id=media_id, product=product)

            # 处理请求数据
            if "is_main" in request.data and request.data["is_main"]:
                media.is_main = True
                media.save()  # 自动处理其他图片的is_main状态

            serializer = ProductMediaSerializer(media)
            return Response(serializer.data)

        except Product.DoesNotExist:
            return Response({"detail": "商品不存在"}, status=status.HTTP_404_NOT_FOUND)
        except ProductMedia.DoesNotExist:
            return Response({"detail": "图片不存在"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, product_id, media_id):
        """删除商品图片"""
        try:
            # 检查商品是否存在
            product = Product.objects.get(product_id=product_id)

            # 检查用户是否有权限
            current_user_id = self.request.headers.get('UUID')
            if str(current_user_id) != str(product.user_id):
                return Response(
                    {"detail": "您没有权限修改此商品"}, status=status.HTTP_403_FORBIDDEN
                )

            # 删除图片
            try:
                media = ProductMedia.objects.get(media_id=media_id, product=product)
                is_main = media.is_main
                media.delete()

                # 如果删除的是主图，设置新的主图
                if is_main:
                    new_main = ProductMedia.objects.filter(product=product).first()
                    if new_main:
                        new_main.is_main = True
                        new_main.save()

                return Response(status=status.HTTP_204_NO_CONTENT)
            except ProductMedia.DoesNotExist:
                return Response(
                    {"detail": "图片不存在"}, status=status.HTTP_404_NOT_FOUND
                )

        except Product.DoesNotExist:
            return Response({"detail": "商品不存在"}, status=status.HTTP_404_NOT_FOUND)


class ProductMediaBulkUpdateView(APIView):
    """
    批量更新商品图片（替换全部）
    PUT: 删除原有图片，上传新图片
    """

    parser_classes = [MultiPartParser]

    def put(self, request, product_id):
        try:
            # 获取商品对象
            product = Product.objects.get(product_id=product_id)

            # 权限验证
            current_user_id = self.request.headers.get('UUID')
            if str(current_user_id) != str(product.user_id):
                return Response(
                    {"detail": "无权操作此商品"}, status=status.HTTP_403_FORBIDDEN
                )

            # 使用事务保证操作原子性
            with transaction.atomic():
                # 删除所有旧图片
                old_media = ProductMedia.objects.filter(product=product)
                for media in old_media:
                    media.media.delete(save=False)  # 删除物理文件
                old_media.delete()

                # 处理新图片
                media_files = request.FILES.getlist("media", [])
                new_media = []
                is_first = True

                for idx, file in enumerate(media_files):
                    # 生成唯一文件名
                    file.name = f"{product_id}_{uuid.uuid4().hex}"

                    media = ProductMedia(product=product, media=file, is_main=is_first)
                    new_media.append(media)
                    is_first = False

                # 批量创建
                ProductMedia.objects.bulk_create(new_media)

                # 如果没有上传新图片，设置主图为None
                if not new_media:
                    product.main_image = None
                    product.save()

            # 序列化返回结果
            serializer = ProductMediaSerializer(
                ProductMedia.objects.filter(product=product), many=True
            )
            return Response(serializer.data)

        except Product.DoesNotExist:
            return Response({"detail": "商品不存在"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = "product_id"


    def retrieve(self, request, *args, **kwargs):
        """获取商品详情并增加访问次数"""
        instance = self.get_object()
        # 增加访问次数
        # 如果是自己的商品则不增加
        current_user_id = self.request.headers.get('UUID')
        if current_user_id and str(instance.user_id) != str(current_user_id):
            instance.visit_count += 1
            instance.save(update_fields=["visit_count"])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_update(self, serializer):
        # 保存商品基本信息
        product = serializer.save(status=3)

        # 处理分类
        if "categories" in self.request.data:
            category_ids = (
                self.request.data.getlist("categories")
                if hasattr(self.request.data, "getlist")
                else self.request.data.get("categories", [])
            )
            if not isinstance(category_ids, list):
                category_ids = [category_ids]

            # 清除现有分类
            product.categories.clear()

            # 添加新分类
            for category_id in category_ids:
                try:
                    category = Category.objects.get(category_id=category_id)
                    product.categories.add(category)
                except Category.DoesNotExist:
                    pass  # 忽略不存在的分类


# 商品评价相关视图
class ProductReviewListCreateAPIView(ListCreateAPIView):
    serializer_class = ProductReviewSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """获取特定商品的所有评价，按时间倒序排列"""
        product_id = self.kwargs.get("product_id")
        return ProductReview.objects.filter(product_id=product_id).order_by(
            "-created_at"
        )

    def perform_create(self, serializer):
        product_id = self.kwargs.get("product_id")
        product = Product.objects.get(product_id=product_id)

        # 检查用户是否已经评论过该商品
        # if ProductReview.objects.filter(product=product, user_id=self.request.user.user_id).exists():
        #     from rest_framework.exceptions import ValidationError
        #     raise ValidationError({"detail": "您已经评论过该商品"})

        # 保存评论
        current_user_id = self.request.headers.get('UUID')
        serializer.save(user_id=current_user_id, product=product)

        # 更新商品平均评分
        rating_avg = ProductReview.objects.filter(product=product).aggregate(
            Avg("rating")
        )["rating__avg"]
        product.rating_avg = round(rating_avg, 1) if rating_avg else 0.0
        product.save(update_fields=["rating_avg"])


class ProductReviewDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = ProductReviewSerializer
    lookup_field = "review_id"

    def get_queryset(self):
        product_id = self.kwargs.get("product_id")
        return ProductReview.objects.filter(product_id=product_id)

    def perform_update(self, serializer):
        """更新评论时，重新计算商品的平均评分"""
        review = serializer.save()

        # 获取评论对应的商品
        product = review.product

        # 重新计算平均评分
        rating_avg = ProductReview.objects.filter(product=product).aggregate(
            Avg("rating")
        )["rating__avg"]
        product.rating_avg = round(rating_avg, 1) if rating_avg else 0.0
        product.save(update_fields=["rating_avg"])

    def perform_destroy(self, instance):
        """删除评论时，重新计算商品的平均评分"""
        product = instance.product
        super().perform_destroy(instance)

        # 重新计算平均评分
        rating_avg = ProductReview.objects.filter(product=product).aggregate(
            Avg("rating")
        )["rating__avg"]
        product.rating_avg = round(rating_avg, 1) if rating_avg else 0.0
        product.save(update_fields=["rating_avg"])


# 收藏相关视图
class UserCollectionListAPIView(ListAPIView):
    """获取用户收藏的商品列表"""

    serializer_class = CollectionSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        current_user_id = self.request.headers.get('UUID')
        return Collection.objects.filter(collecter=current_user_id).order_by(
            "-create_at"
        )


class ProductCollectionView(APIView):
    """
    商品收藏相关操作的统一视图

    GET: 检查商品是否已被当前用户收藏
    POST: 收藏商品
    DELETE: 取消收藏
    """

    def get(self, request, product_id):
        """检查商品是否已被当前用户收藏"""
        current_user_id = request.headers.get('UUID')
        is_collected = Collection.objects.filter(
            collection__product_id=product_id, collecter=current_user_id
        ).exists()

        return Response({"is_collected": is_collected})

    def post(self, request, product_id):
        """收藏商品"""
        current_user_id = request.headers.get('UUID')
        
        # 检查商品是否存在
        try:
            product = Product.objects.get(product_id=product_id)
        except Product.DoesNotExist:
            return Response({"detail": "商品不存在"}, status=status.HTTP_404_NOT_FOUND)

        # 检查是否已收藏
        if Collection.objects.filter(
            collection__product_id=product_id, collecter=current_user_id
        ).exists():
            return Response(
                {"detail": "您已收藏过此商品"}, status=status.HTTP_400_BAD_REQUEST
            )

        # 创建收藏
        collection = Collection.objects.create(
            collection=product, collecter=current_user_id
        )
        serializer = CollectionSerializer(collection)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, product_id):
        """取消收藏"""
        current_user_id = request.headers.get('UUID')
        
        try:
            collection = Collection.objects.get(
                collection__product_id=product_id, collecter=current_user_id
            )
            collection.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Collection.DoesNotExist:
            return Response(
                {"detail": "您尚未收藏此商品"}, status=status.HTTP_404_NOT_FOUND
            )


class CategoryListCreateAPIView(ListCreateAPIView):
    """获取所有分类或创建新分类"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer



class CategoryDetailAPIView(RetrieveUpdateDestroyAPIView):
    """获取、更新或删除单个分类"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = "category_id"


class ProductByCategoryAPIView(ListAPIView):
    """获取指定分类下的所有商品"""

    serializer_class = ProductSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter

    def get_queryset(self):
        """
        sort_by = 0 表示按创建时间倒序
        sort_by = 1 表示按热度倒序
        sort_by = 2 表示按价格升序
        sort_by = 3 表示按价格降序
        sort_by = 4 表示按评分倒序
        """
        category_id = self.kwargs.get("category_id")
        # 如果查询参数sort_by存在，则按指定字段排序
        sort_by = self.request.query_params.get("sort_by")
        if sort_by is not None:
            if sort_by == "0":
                return Product.objects.filter(
                    categories__category_id=category_id
                ).order_by("-created_at")
            elif sort_by == "1":
                return Product.objects.filter(
                    categories__category_id=category_id
                ).order_by("-visit_count")
            elif sort_by == "2":
                return Product.objects.filter(
                    categories__category_id=category_id
                ).order_by("price")
            elif sort_by == "3":
                return Product.objects.filter(
                    categories__category_id=category_id
                ).order_by("-price")
            elif sort_by == "4":
                return Product.objects.filter(
                    categories__category_id=category_id
                ).order_by("-rating_avg")
        return Product.objects.filter(categories__category_id=category_id).order_by(
            "-created_at"
        )

class ProductPublishListAPIView(ListAPIView):
    """获取用户自己发布的商品列表或创建新商品"""
    
    serializer_class = ProductSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter

    def get_queryset(self):
       current_user_id = self.request.headers.get('UUID')
       return Product.objects.filter(user_id=current_user_id)


class ProductUpdateStockAPIView(APIView):
    """更新商品库存API"""
    
    def post(self, request, product_id):
        """
        更新商品库存
        支持增加（正数）或减少（负数）库存
        用于订单创建（减少）或取消（恢复）时更新库存
        """
        try:
            # 获取商品
            product = Product.objects.get(product_id=product_id)
            
            # 获取要更新的数量
            quantity = request.data.get('quantity')
            
            if quantity is None:
                return Response({
                    'success': False,
                    'error': '缺少quantity参数'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 验证数量类型
            if not isinstance(quantity, int):
                return Response({
                    'success': False,
                    'error': '库存数量必须为整数'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 检查0值
            if quantity == 0:
                return Response({
                    'success': False,
                    'error': '库存变更数量不能为0'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 计算新的库存
            old_stock = product.stock
            new_stock = old_stock + quantity
            
            # 检查库存是否会变为负数
            if new_stock < 0:
                return Response({
                    'success': False,
                    'error': f'库存不足，当前库存：{old_stock}，请求变更：{quantity}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 更新库存
            product.stock = new_stock
            product.save(update_fields=['stock'])
            
            # 记录日志
            action = "增加" if quantity > 0 else "减少"
            logger.info(f"Stock updated for product {product_id}: {action}{abs(quantity)} (old: {old_stock} -> new: {new_stock})")
            
            return Response({
                'success': True,
                'message': '库存更新成功',
                'data': {
                    'product_id': str(product_id),
                    'quantity_changed': quantity,
                    'old_stock': old_stock,
                    'current_stock': new_stock
                }
            }, status=status.HTTP_200_OK)
            
        except Product.DoesNotExist:
            return Response({
                'success': False,
                'error': '商品不存在'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating stock for product {product_id}: {e}")
            return Response({
                'success': False,
                'error': '库存更新失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)