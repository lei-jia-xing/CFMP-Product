from django.db import models
from minio_storage import MinioMediaStorage
import uuid
# Product数据表：Product, ProductMedia, Category, ProductReview, Collection


# NOTE:
# 关键表：多次被外键引用需要添加UUID，以便于跨服务通信
class Product(models.Model):
    """Product

    Attributes:
        product_id: primary_key(not nessary)
        user: model
        title: CharField
        description: TextField
        price: DecimalField
        status:  default=0 (0 = 上架, 1 = 下架)
        created_at: DateTimeField(not nessary)
        categories: model(related_name="products")
    """

    ON_SALE = 0
    OFF_SALE = 1
    SALED = 2
    UN_CHECK = 3
    STATUS_CHOICES = [
        (ON_SALE, "上架"),
        (OFF_SALE, "封禁"),
        (SALED, "已出售"),
        (UN_CHECK, "未审核"),
    ]
    FUNCTION_CHOICES = [
        (0, "包邮"),
        (1, "自提"),
    ]

    product_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # FIX:
    # 高耦合，改成事件通知
    user_id = models.UUIDField()
    title = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=ON_SALE)
    created_at = models.DateTimeField(auto_now_add=True)
    categories = models.ManyToManyField("Category", related_name="products")
    function = models.SmallIntegerField(choices=FUNCTION_CHOICES, default=0)
    visit_count = models.PositiveIntegerField(default=0)
    rating_avg = models.DecimalField(
        max_digits=2, decimal_places=1, default=0.0, help_text="平均评分"
    )
    stock = models.PositiveIntegerField(default=1, help_text="库存数量")

    class Meta:
        db_table = "product"


class ProductMedia(models.Model):
    """ProductMedia

    Attributes:
        media_id: primary_key(not nessary)
        product: model(related_name="media")
        media: ImageField
        is_main: 是否为主图
        created_at: 创建时间
    """

    media_id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="media")
    media = models.ImageField(
        upload_to="product_media/",
        storage=MinioMediaStorage(),
        null=True,
        blank=True,
    )
    is_main = models.BooleanField(default=False)  # 是否为主图
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "product_media"
        ordering = ["-is_main", "created_at"]  # 主图优先，然后按时间排序

    def save(self, *args, **kwargs):
        # 如果设置为主图，则将该产品的其他图片设为非主图
        if self.is_main:
            ProductMedia.objects.filter(product=self.product, is_main=True).update(
                is_main=False
            )
        super().save(*args, **kwargs)


class Category(models.Model):
    """Category

    Attributes:
        category_id: primary_key(not nessary)
        name: CharField
    """

    category_id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)

    class Meta:
        db_table = "category"


class ProductReview(models.Model):
    """ProductReview

    Attributes:
        review_id: primary_key(not nessary)
        product: model(related_name="reviews")
        user: model
        rating: 1-5
        comment: TextField
        created_at: DateTimeField(not nessary)
    """

    review_id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    user_id = models.UUIDField()
    rating = models.PositiveSmallIntegerField()  # 1-5 星
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "product_review"


class Collection(models.Model):
    """Collection

    Attributes:
        collection: model(related_name="collections")
        collecter: model
        create_at: DateTimeField(not nessary)
    """

    collection = models.ForeignKey(Product, on_delete=models.CASCADE)
    # FIX:
    # 高耦合，需要使用UUID发送事件以便于User app接收
    collecter = models.UUIDField()
    create_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "collection"
        unique_together = ("collection", "collecter")
