from django.urls import path
from . import views

urlpatterns = [
    # 商品相关路由
    path(
        "product/", views.ProductListCreateAPIView.as_view(), name="product-list-create"
    ),
    path(
        "product/<uuid:product_id>/",
        views.ProductDetailAPIView.as_view(),
        name="product-detail",
    ),
    # 商品图片相关路由
    path(
        "product/<uuid:product_id>/media/",
        views.ProductMediaListView.as_view(),
        name="product-media-list",
    ),
    path(
        "product/<uuid:product_id>/media/<int:media_id>/",
        views.ProductMediaDetailView.as_view(),
        name="product-media-detail",
    ),
    path(
        "product/<uuid:product_id>/media/bulk/",
        views.ProductMediaBulkUpdateView.as_view(),
        name="product-media-bulk-update",
    ),
    # 商品评价相关路由
    path(
        "product/<uuid:product_id>/reviews/",
        views.ProductReviewListCreateAPIView.as_view(),
        name="product-review-list-create",
    ),
    path(
        "product/<uuid:product_id>/reviews/<int:review_id>/",
        views.ProductReviewDetailAPIView.as_view(),
        name="product-review-detail",
    ),
    # 收藏相关路由
    path(
        "product/collections/",
        views.UserCollectionListAPIView.as_view(),
        name="user-collections",
    ),
    path(
        "product/<uuid:product_id>/collection/",
        views.ProductCollectionView.as_view(),
        name="product-collection",
    ),
    # 分类相关路由
    path(
        "product/category/",
        views.CategoryListCreateAPIView.as_view(),
        name="category-list-create",
    ),
    path(
        "product/category/<int:category_id>/",
        views.CategoryDetailAPIView.as_view(),
        name="category-detail",
    ),
    path(
        "product/category/<int:category_id>/products/",
        views.ProductByCategoryAPIView.as_view(),
        name="category-products",
    ),
    path(
        "product/publish/",
        views.ProductPublishListAPIView.as_view(),
        name="product-publish-list",
    )
]
