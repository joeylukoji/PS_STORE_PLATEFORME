from django.urls import path

from . import account_views, views

app_name = "store"

urlpatterns = [
    path("compte/connexion/", account_views.CustomerLoginView.as_view(), name="login"),
    path("compte/inscription/", account_views.signup, name="signup"),
    path("compte/deconnexion/", account_views.CustomerLogoutView.as_view(), name="logout"),
    path("compte/", account_views.account, name="account"),
    path("compte/mot-de-passe/", account_views.CustomerPasswordChangeView.as_view(), name="password"),
    path("compte/commandes/<str:reference>/", account_views.account_order, name="account_order"),
    path("", views.home, name="home"),
    path("produits/", views.product_list, name="products"),
    path("categorie/<slug:slug>/", views.product_list, name="category"),
    path("produit/<slug:slug>/", views.product_detail, name="product"),
    path("panier/", views.cart_detail, name="cart"),
    path("panier/ajouter/<int:pk>/", views.cart_add, name="cart_add"),
    path("panier/modifier/<int:pk>/", views.cart_update, name="cart_update"),
    path("panier/retirer/<int:pk>/", views.cart_remove, name="cart_remove"),
    path("commande/", views.checkout, name="checkout"),
    path("commande/confirmation/<str:reference>/", views.confirmation, name="confirmation"),
    path("suivi/", views.tracking, name="tracking"),
]
