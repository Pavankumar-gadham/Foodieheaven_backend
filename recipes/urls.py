from . import views
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import (
    CartItemDeleteView, CategoryListView, ClearCartView, PurchasedRecipesView, RegisterView, RecipeDetailView, RecipeListCreateView, CustomTokenObtainPairView, MyRecipeListView, SubscriptionCreateView,
    CartListCreateView, OrderCreateView, create_payment_order, has_purchased_recipe, load_data_view
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('load-data/', load_data_view), 
    path('register/', RegisterView.as_view()),
    path('login/', CustomTokenObtainPairView.as_view()),
    path('token/refresh', TokenRefreshView.as_view()),
    
    path('recipes/', RecipeListCreateView.as_view()),
    path('my-recipes/', MyRecipeListView.as_view()),
    path('recipes/<int:pk>/', RecipeDetailView.as_view()),
    path('categories/', CategoryListView.as_view()),
    path('subscribe/', SubscriptionCreateView.as_view()),
    
    path('cart/', CartListCreateView.as_view()),   
    path('cart/<int:pk>/', CartItemDeleteView.as_view(), name='remove-cart-item'),
    path('cart/clear/', ClearCartView.as_view(), name='clear-cart'),  
    path('cart/count/', views.cart_count, name='cart-count'), 
    path('orders/', OrderCreateView.as_view()),                     
    path('purchased-recipes/', PurchasedRecipesView.as_view()),      
    path('has-purchased/<int:recipe_id>/', has_purchased_recipe),    
    path('create-payment-order/', create_payment_order), 

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
