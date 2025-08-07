from urllib import request
from rest_framework import generics, permissions, filters
from .permissions import IsOwnerOrReadOnly
from .serializers import CartItemSerializer, OrderSerializer, PurchasedRecipeSerializer, RegisterSerializer, RecipeSerializer, CategorySerializer, SubscriptionSerializer
from django.core.cache import cache
import razorpay
from django.conf import settings
from rest_framework.exceptions import NotFound
from django.contrib.auth.models import User
from .models import CartItem, Order, PurchasedRecipe, Recipe, Category, Subscription
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .tasks import notify_new_recipe, send_subscription_welcome_email, send_purchase_email
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.management import call_command
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import user_passes_test
import io


# User registration view
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer


# Pagination config
class RecipePagination(LimitOffsetPagination):
    default_limit = 5
    max_limit = 20


# Categories List API
class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    

class SubscriptionCreateView(generics.CreateAPIView):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [] 
    
    def perform_create(self, serializer):
        subscription = serializer.save()
        send_subscription_welcome_email.delay(subscription.email)

class MyRecipeListView(generics.ListAPIView):
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = RecipePagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['title']
    
    def get_queryset(self):
        return Recipe.objects.filter(created_by = self.request.user).select_related('category', 'created_by')

# Recipe List/Create API — User-specific listing + optional category filter + Redis cache
class RecipeListCreateView(generics.ListCreateAPIView):
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = RecipePagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['title']

    def get_queryset(self):
        """
        Returns only recipes created by current logged-in user.
        Optionally filters by category via ?category=<id>
        """
        queryset = Recipe.objects.all().select_related('category', 'created_by')
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset

    def get(self, request, *args, **kwargs):
        category_id = request.query_params.get('category')
        user_id = request.user.id if request.user.is_authenticated else 'anonymous'
        limit = request.query_params.get('limit', 10)
        offset = request.query_params.get('offset', 0)
        search_query = request.query_params.get('search', '').strip() or 'none'

        cache_key = f'recipe_list_{user_id}_{category_id or "all"}_limit_{limit}_offset_{offset}_search_{search_query}'

        try:
            cached_data = cache.get(cache_key)
            if cached_data:
                print(f"✅ Recipes fetched from Redis cache: {cache_key}", flush=True)
                return Response(cached_data)
        except Exception as e:
            print(f"⚠️ Cache unavailable on GET: {e}", flush=True)

        response = super().get(request, *args, **kwargs)

        try:
            cache.set(cache_key, response.data, timeout=300)
            print(f"✅ Recipes fetched from DB and cached: {cache_key}", flush=True)
        except Exception as e:
            print(f"⚠️ Failed to cache on SET: {e}", flush=True)

        return response

    def perform_create(self, serializer):
        recipe = serializer.save(created_by=self.request.user)
        recipient_email = self.request.user.email  # grab email of recipe creator
        notify_new_recipe.delay(recipe.title, recipe.description, recipient_email)
        cache.delete_pattern(f'recipe_list_{self.request.user.id}_*')
        print(f"🆕 Cache cleared after recipe creation by {self.request.user.username}.", flush=True)


# Recipe detail/update/delete view
class RecipeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Recipe.objects.all().select_related('category', 'created_by')
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_update(self, serializer):
        recipe = serializer.save()
        cache.delete_pattern(f'recipe_list_{recipe.created_by.id}_*')
        print(f"📝 Cache cleared after recipe update by {recipe.created_by.username}.", flush=True)

    def perform_destroy(self, instance):
        created_by = instance.created_by.username
        user_id = instance.created_by.id
        instance.delete()
        cache.delete_pattern(f'recipe_list_{user_id}_*')
        print(f"❌ Cache cleared after recipe delete by {created_by}.", flush=True)


# Custom JWT token serializer to return user details
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username
        }
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class CartListCreateView(generics.ListCreateAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
        
class CartItemDeleteView(generics.DestroyAPIView):
    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class ClearCartView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        CartItem.objects.filter(user=request.user).delete()
        return Response({'message': 'Cart cleared'})

class OrderCreateView(generics.CreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = request.user
        data = request.data

        if isinstance(data, list):
            # Handle bulk order creation
            orders = []
            for item in data:
                item['user'] = user.id
                serializer = self.get_serializer(data=item)
                serializer.is_valid(raise_exception=True)
                order = serializer.save(user=user)
                orders.append(serializer.data)

                # ✅ Create PurchasedRecipe
                PurchasedRecipe.objects.get_or_create(
                    user=user,
                    recipe=order.recipe,
                    defaults={'payment_id': order.payment_id}
                )

                # ✅ Send purchase email via Celery
                send_purchase_email.delay(
                    user.email,
                    order.recipe.title,
                    str(order.recipe.price),
                    order.payment_id
                )

            return Response({'message': 'Orders placed successfully', 'orders': orders}, status=201)

        else:
            # Handle single order creation
            data['user'] = user.id
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            order = serializer.save(user=user)

            # ✅ Create PurchasedRecipe
            PurchasedRecipe.objects.get_or_create(
                user=user,
                recipe=order.recipe,
                defaults={'payment_id': order.payment_id}
            )

            # ✅ Send purchase email via Celery
            send_purchase_email.delay(
                user.email,
                order.recipe.title,
                str(order.recipe.price),
                order.payment_id
            )

            return Response(serializer.data, status=201)


class PurchasedRecipesView(generics.ListAPIView):
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        recipe_ids = PurchasedRecipe.objects.filter(user=self.request.user).values_list('recipe_id', flat=True)
        return Recipe.objects.filter(id__in=recipe_ids)


# Check if a recipe is purchased
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def has_purchased_recipe(request, recipe_id):
    purchased = Order.objects.filter(user=request.user, recipe_id=recipe_id).exists()
    return Response({'purchased': purchased})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment_order(request):
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    amount = request.data.get('amount')

    order = client.order.create({
        "amount": int(amount) * 100,
        "currency": "INR",
        "payment_capture": 1
    })
    return Response({'order_id': order['id']})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cart_count(request):
    count = request.user.cart_items.count()
    return Response({'count': count})

def load_data_view(request):
    if request.method == 'GET':
        out = io.StringIO()
        try:
            call_command('loaddata', 'full_data.json', stdout=out)
            return JsonResponse({'status': 'success', 'output': out.getvalue()})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
