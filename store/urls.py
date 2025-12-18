from django.urls import path
from . import views
urlpatterns = [
    path("", views.index, name="index"),
    path("products/", views.products, name="products"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    path("search/", views.search, name="search"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("cart/", views.cart_view, name="cart"),
    path("checkout/", views.checkout_view, name="checkout"),
    path("api/orders/", views.OrderAPIView.as_view(), name="api_orders"),
]
