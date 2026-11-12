from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "backoffice"

urlpatterns = [
    path("connexion/", views.LoginView.as_view(), name="login"),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("produits/", views.product_list, name="products"),
    path("produits/nouveau/", views.product_form, name="product_new"),
    path("produits/<int:pk>/", views.product_form, name="product_edit"),
    path("produits/<int:pk>/publication/", views.product_toggle, name="product_toggle"),
    path("produits/<int:pk>/images/", views.image_add, name="image_add"),
    path("images/<int:pk>/supprimer/", views.image_delete, name="image_delete"),
    path("stock/", views.stock, name="stock"),
    path("commandes/", views.order_list, name="orders"),
    path("commandes/<str:reference>/", views.order_detail, name="order_detail"),
    path("rapports/", views.reports, name="reports"),
    path("utilisateurs/", views.users, name="users"),
    path("utilisateurs/<int:pk>/role/", views.user_role, name="user_role"),
]
