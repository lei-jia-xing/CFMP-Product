from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from user.models import User
from .models import Product, Category, ProductReview, ProductMedia, Collection
from PIL import Image
import io
from decimal import Decimal
from unittest.mock import patch


def create_test_image(name='test.jpg'):
    """创建测试图片"""
    # 创建一个测试用图片文件
    file = io.BytesIO()
    image = Image.new('RGB', (100, 100), color='red')
    image.save(file, 'JPEG')
    file.name = name
    file.seek(0)
    return file


class ProductModelTest(TestCase):
    """测试商品模型"""

    def setUp(self):
        # 创建测试用户
        self.user = User.objects.create(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

        # 创建测试分类
        self.category = Category.objects.create(name="测试分类")

        # 创建测试商品
        self.product = Product.objects.create(
            user=self.user,
            title="测试商品",
            description="这是一个测试商品的描述",
            price=99.99,
            status=2  # 已上架
        )
        self.product.categories.add(self.category)

    def test_product_creation(self):
        """测试商品创建是否成功"""
        self.assertEqual(self.product.title, "测试商品")
        self.assertEqual(self.product.user, self.user)
        self.assertEqual(self.product.price, 99.99)
        self.assertEqual(self.product.status, 2)
        self.assertTrue(self.category in self.product.categories.all())


class ProductMediaModelTest(TestCase):
    """测试商品图片模型"""

    @patch('django_minio_backend.MinioBackend._save', return_value='test.jpg')
    @patch('django_minio_backend.MinioBackend.exists', return_value=False)
    @patch('django_minio_backend.MinioBackend.url', return_value='http://minio-server/test.jpg')
    def setUp(self, mock_url, mock_exists, mock_save):
        # 创建测试用户
        self.user = User.objects.create(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )

        # 创建测试商品
        self.product = Product.objects.create(
            user=self.user,
            title="测试商品",
            description="这是一个测试商品的描述",
            price=99.99,
            status=2
        )

        # 创建测试图片
        test_image = create_test_image()
        self.media = ProductMedia.objects.create(
            product=self.product,
            media=SimpleUploadedFile(
                name=test_image.name,
                content=test_image.read(),
                content_type='image/jpeg'
            ),
            is_main=True
        )

    def test_product_media_creation(self):
        """测试商品图片创建是否成功"""
        self.assertEqual(self.media.product, self.product)
        self.assertTrue(self.media.is_main)

    @patch('django_minio_backend.MinioBackend._save', return_value='test2.jpg')
    @patch('django_minio_backend.MinioBackend.exists', return_value=False)
    @patch('django_minio_backend.MinioBackend.url', return_value='http://minio-server/test2.jpg')
    def test_product_media_main_image_uniqueness(self, mock_url, mock_exists, mock_save):
        """测试一个商品只能有一张主图"""
        # 创建第二张图片并设置为主图
        test_image = create_test_image(name='test2.jpg')
        media2 = ProductMedia.objects.create(
            product=self.product,
            media=SimpleUploadedFile(
                name=test_image.name,
                content=test_image.read(),
                content_type='image/jpeg'
            ),
            is_main=True
        )

        # 重新获取第一张图片
        self.media.refresh_from_db()

        # 第一张图片应该不再是主图
        self.assertFalse(self.media.is_main)
        # 第二张图片应该是主图
        self.assertTrue(media2.is_main)


class ProductAPITest(APITestCase):
    """测试商品基本API"""

    def setUp(self):
        # 创建测试用户
        self.user = User.objects.create(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        # 确保用户有正确的认证属性
        self.user.is_authenticated = True
        self.user.save()

        # 创建客户端并使用force_authenticate绕过JWT认证
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # 创建测试分类
        self.category = Category.objects.create(name="测试分类")

        # 创建测试商品
        self.product = Product.objects.create(
            user=self.user,
            title="测试商品",
            description="这是一个测试商品的描述",
            price=99.99,
            status=2  # 已上架
        )
        self.product.categories.add(self.category)

    def test_get_product_list(self):
        """测试获取商品列表"""
        url = reverse("product-list-create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], "测试商品")

    def test_get_product_detail(self):
        """测试获取商品详情"""
        url = reverse("product-detail", kwargs={"product_id": self.product.product_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "测试商品")
        self.assertEqual(response.data['price'], "99.99")

    def test_create_product(self):
        """测试创建商品"""
        url = reverse("product-list-create")
        data = {
            "title": "新商品",
            "description": "这是一个新的测试商品",
            "price": "199.99",
            "status": 0,
            "categories": [self.category.category_id]
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], "新商品")
        self.assertEqual(Product.objects.count(), 2)

    def test_update_product(self):
        """测试更新商品"""
        url = reverse("product-detail", kwargs={"product_id": self.product.product_id})
        data = {
            "title": "更新后的商品",
            "description": "这是更新后的商品描述",
            "price": 299.99,
            "status": 1,
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.title, "更新后的商品")
        self.assertEqual(self.product.price, Decimal('299.99'))

    def test_delete_product(self):
        """测试删除商品"""
        url = reverse("product-detail", kwargs={"product_id": self.product.product_id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Product.objects.count(), 0)


class ProductMediaAPITest(APITestCase):
    """测试商品图片API"""

    @patch('django_minio_backend.MinioBackend._save', return_value='test.jpg')
    @patch('django_minio_backend.MinioBackend.exists', return_value=False)
    @patch('django_minio_backend.MinioBackend.url', return_value='http://minio-server/test.jpg')
    def setUp(self, mock_url, mock_exists, mock_save):
        # 创建测试用户
        self.user = User.objects.create(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        # 确保用户有正确的认证属性
        self.user.is_authenticated = True
        self.user.save()

        # 创建另一个用户用于测试权限
        self.other_user = User.objects.create(
            username="otheruser",
            email="other@example.com",
            password="testpass123"
        )
        # 确保另一个用户也有正确的认证属性
        self.other_user.is_authenticated = True
        self.other_user.save()

        # 创建客户端并登录
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # 创建测试商品
        self.product = Product.objects.create(
            user=self.user,
            title="测试商品",
            description="这是一个测试商品的描述",
            price=99.99,
            status=2
        )

        # 创建测试图片
        test_image = create_test_image()
        self.media = ProductMedia.objects.create(
            product=self.product,
            media=SimpleUploadedFile(
                name=test_image.name,
                content=test_image.read(),
                content_type='image/jpeg'
            ),
            is_main=True
        )

    def test_get_media_list(self):
        """测试获取商品图片列表"""
        url = reverse("product-media-list", kwargs={"product_id": self.product.product_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @patch('django_minio_backend.MinioBackend._save', return_value='upload_test.jpg')
    @patch('django_minio_backend.MinioBackend.exists', return_value=False)
    @patch('django_minio_backend.MinioBackend.url', return_value='http://minio-server/upload_test.jpg')
    def test_upload_media(self, mock_url, mock_exists, mock_save):
        """测试上传商品图片"""
        url = reverse("product-media-list", kwargs={"product_id": self.product.product_id})

        # 创建测试图片
        image = create_test_image(name="upload_test.jpg")

        data = {
            "media": SimpleUploadedFile(
                name=image.name,
                content=image.read(),
                content_type='image/jpeg'
            )
        }

        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProductMedia.objects.filter(product=self.product).count(), 2)

    def test_upload_media_permission_denied(self):
        """测试非商品所有者上传图片权限拒绝"""
        # 切换到另一个用户
        self.client.force_authenticate(user=self.other_user)

        url = reverse("product-media-list", kwargs={"product_id": self.product.product_id})

        # 创建测试图片
        image = create_test_image(name="upload_test.jpg")

        data = {
            "media": SimpleUploadedFile(
                name=image.name,
                content=image.read(),
                content_type='image/jpeg'
            )
        }

        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('django_minio_backend.MinioBackend._save', return_value='second.jpg')
    @patch('django_minio_backend.MinioBackend.exists', return_value=False)
    @patch('django_minio_backend.MinioBackend.url', return_value='http://minio-server/second.jpg')
    def test_set_main_image(self, mock_url, mock_exists, mock_save):
        """测试设置主图"""
        # 先创建第二张图片
        test_image = create_test_image(name="second.jpg")
        second_media = ProductMedia.objects.create(
            product=self.product,
            media=SimpleUploadedFile(
                name=test_image.name,
                content=test_image.read(),
                content_type='image/jpeg'
            ),
            is_main=False
        )

        # 设置第二张图片为主图
        url = reverse("product-media-detail", kwargs={
            "product_id": self.product.product_id,
            "media_id": second_media.media_id
        })

        data = {
            "is_main": True
        }

        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 刷新数据库数据
        self.media.refresh_from_db()
        second_media.refresh_from_db()

        # 验证第一张不再是主图，第二张变为主图
        self.assertFalse(self.media.is_main)
        self.assertTrue(second_media.is_main)

    def test_delete_media(self):
        """测试删除图片"""
        url = reverse("product-media-detail", kwargs={
            "product_id": self.product.product_id,
            "media_id": self.media.media_id
        })

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ProductMedia.objects.filter(product=self.product).count(), 0)

    @patch('django_minio_backend.MinioBackend._save', return_value='second.jpg')
    @patch('django_minio_backend.MinioBackend.exists', return_value=False)
    @patch('django_minio_backend.MinioBackend.url', return_value='http://minio-server/second.jpg')
    def test_delete_main_image_and_set_new_main(self, mock_url, mock_exists, mock_save):
        """测试删除主图并自动设置新主图"""
        # 先创建第二张图片
        test_image = create_test_image(name="second.jpg")
        second_media = ProductMedia.objects.create(
            product=self.product,
            media=SimpleUploadedFile(
                name=test_image.name,
                content=test_image.read(),
                content_type='image/jpeg'
            ),
            is_main=False
        )

        # 删除第一张(主)图
        url = reverse("product-media-detail", kwargs={
            "product_id": self.product.product_id,
            "media_id": self.media.media_id
        })

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # 刷新第二张图片数据
        second_media.refresh_from_db()

        # 验证第二张图片已变为主图
        self.assertTrue(second_media.is_main)


class CategoryAPITest(APITestCase):
    """测试分类API"""

    def setUp(self):
        # 创建管理员用户
        self.admin_user = User.objects.create(
            username="admin",
            email="admin@example.com",
            password="password123",
            privilege=1  # 设置为管理员权限
        )

        # 创建普通用户
        self.regular_user = User.objects.create(
            username="regular",
            email="regular@example.com",
            password="password123",
            privilege=0  # 设置为普通用户权限
        )

        # 创建测试分类
        self.category = Category.objects.create(
            name="测试分类"
        )

        # 创建客户端
        self.client = APIClient()

    def test_get_category_list(self):
        """测试获取分类列表"""
        response = self.client.get('/api/product/category/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # 应该有一个分类

    def test_create_category_as_admin(self):
        """测试管理员创建分类"""
        self.client.force_authenticate(user=self.admin_user)
        data = {
            "name": "新分类"
        }
        response = self.client.post('/api/product/category/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.count(), 2)  # 应该有两个分类

    def test_create_category_as_regular_user(self):
        """测试普通用户创建分类（应该被拒绝）"""
        self.client.force_authenticate(user=self.regular_user)
        data = {
            "name": "新分类"
        }
        response = self.client.post('/api/product/category/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Category.objects.count(), 1)  # 分类数量应该不变

    def test_update_category(self):
        """测试更新分类"""
        self.client.force_authenticate(user=self.admin_user)
        data = {
            "name": "更新的分类"
        }
        response = self.client.put(f'/api/product/category/{self.category.category_id}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, "更新的分类")

    def test_delete_category(self):
        """测试删除分类"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(f'/api/product/category/{self.category.category_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Category.objects.count(), 0)  # 应该没有分类了


class ProductByCategoryAPITest(APITestCase):
    """测试按分类查询商品API"""

    def setUp(self):
        # 创建测试用户
        self.user = User.objects.create(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        # 确保用户有正确的认证属性
        self.user.is_authenticated = True
        self.user.save()

        # 创建两个测试分类
        self.category1 = Category.objects.create(name="分类1")
        self.category2 = Category.objects.create(name="分类2")

        # 创建测试商品
        self.product1 = Product.objects.create(
            user=self.user,
            title="商品1",
            description="这是商品1的描述",
            price=99.99,
            status=2
        )
        self.product1.categories.add(self.category1)

        self.product2 = Product.objects.create(
            user=self.user,
            title="商品2",
            description="这是商品2的描述",
            price=199.99,
            status=2
        )
        self.product2.categories.add(self.category2)

        self.product3 = Product.objects.create(
            user=self.user,
            title="商品3",
            description="这是商品3的描述",
            price=299.99,
            status=2
        )
        self.product3.categories.add(self.category1, self.category2)

        # 创建客户端
        self.client = APIClient()

    def test_get_products_by_category(self):
        """测试按分类获取商品列表"""
        url = reverse("category-products", kwargs={"category_id": self.category1.category_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

        # 验证商品1和商品3在分类1下
        product_ids = [item['product_id'] for item in response.data['results']]
        self.assertIn(self.product1.product_id, product_ids)
        self.assertIn(self.product3.product_id, product_ids)
        self.assertNotIn(self.product2.product_id, product_ids)

        # 测试分类2
        url = reverse("category-products", kwargs={"category_id": self.category2.category_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

        # 验证商品2和商品3在分类2下
        product_ids = [item['product_id'] for item in response.data['results']]
        self.assertIn(self.product2.product_id, product_ids)
        self.assertIn(self.product3.product_id, product_ids)
        self.assertNotIn(self.product1.product_id, product_ids)


class ProductReviewAPITest(APITestCase):
    """测试商品评论API"""

    def setUp(self):
        # 创建测试用户
        self.user = User.objects.create(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        # 确保用户有正确的认证属性
        self.user.is_authenticated = True
        self.user.save()

        # 创建另一个用户
        self.other_user = User.objects.create(
            username="otheruser",
            email="other@example.com",
            password="testpass123"
        )
        # 确保另一个用户也有正确的认证属性
        self.other_user.is_authenticated = True
        self.other_user.save()

        # 创建测试商品
        self.product = Product.objects.create(
            user=self.user,
            title="测试商品",
            description="这是一个测试商品的描述",
            price=99.99,
            status=2
        )

        # 创建测试评论
        self.review = ProductReview.objects.create(
            product=self.product,
            user=self.user,
            rating=5,
            comment="非常好用的商品！"
        )

        # 创建客户端并登录
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_review_list(self):
        """测试获取商品评论列表"""
        url = reverse("product-review-list-create", kwargs={"product_id": self.product.product_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['comment'], "非常好用的商品！")

    def test_create_review(self):
        """测试创建评论"""
        # 切换到另一个用户，因为每个用户只能对同一商品评论一次
        self.client.force_authenticate(user=self.other_user)

        url = reverse("product-review-list-create", kwargs={"product_id": self.product.product_id})
        data = {
            "rating": 4,
            "comment": "不错的商品，但有点贵"
        }
        response = self.client.post(url, data, format="json")

        # 如果失败，打印详细错误信息
        if response.status_code != status.HTTP_201_CREATED:
            print("评论创建失败:", response.data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['comment'], "不错的商品，但有点贵")
        self.assertEqual(ProductReview.objects.count(), 2)

    def test_update_review(self):
        """测试更新评论"""
        url = reverse("product-review-detail", kwargs={
            "product_id": self.product.product_id,
            "review_id": self.review.review_id
        })
        data = {
            "rating": 3,
            "comment": "更新后的评论"
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 3)
        self.assertEqual(self.review.comment, "更新后的评论")

    def test_delete_review(self):
        """测试删除评论"""
        url = reverse("product-review-detail", kwargs={
            "product_id": self.product.product_id,
            "review_id": self.review.review_id
        })
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ProductReview.objects.count(), 0)


class CollectionAPITest(APITestCase):
    """测试收藏API"""

    def setUp(self):
        # 创建测试用户
        self.user = User.objects.create(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        # 确保用户有正确的认证属性
        self.user.is_authenticated = True
        self.user.save()

        # 创建另一个用户
        self.other_user = User.objects.create(
            username="otheruser",
            email="other@example.com",
            password="testpass123"
        )
        # 确保另一个用户也有正确的认证属性
        self.other_user.is_authenticated = True
        self.other_user.save()

        # 创建测试商品
        self.product1 = Product.objects.create(
            user=self.user,
            title="商品1",
            description="这是商品1的描述",
            price=99.99,
            status=2
        )

        self.product2 = Product.objects.create(
            user=self.user,
            title="商品2",
            description="这是商品2的描述",
            price=199.99,
            status=2
        )

        # 创建测试收藏
        self.collection = Collection.objects.create(
            collection=self.product1,
            collecter=self.user
        )

        # 创建客户端并登录
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_collection_list(self):
        """测试获取用户收藏列表"""
        url = reverse("user-collections")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['collection']['title'], "商品1")

    def test_check_collection_status(self):
        """测试检查商品收藏状态"""
        # 已收藏的商品
        url = reverse("product-collection", kwargs={"product_id": self.product1.product_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_collected'])

        # 未收藏的商品
        url = reverse("product-collection", kwargs={"product_id": self.product2.product_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_collected'])

    def test_create_collection(self):
        """测试创建收藏"""
        url = reverse("product-collection", kwargs={"product_id": self.product2.product_id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Collection.objects.count(), 2)

        # 验证收藏已创建
        collection = Collection.objects.filter(collection=self.product2, collecter=self.user).first()
        self.assertIsNotNone(collection)

    def test_create_duplicate_collection(self):
        """测试重复收藏被拒绝"""
        url = reverse("product-collection", kwargs={"product_id": self.product1.product_id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Collection.objects.count(), 1)

    def test_delete_collection(self):
        """测试取消收藏"""
        url = reverse("product-collection", kwargs={"product_id": self.product1.product_id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Collection.objects.count(), 0)
