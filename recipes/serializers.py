from rest_framework import serializers
from django.contrib.auth.models import User
from .models import CartItem, Category, Order, PurchasedRecipe, Recipe, Subscription


#user registartion serializers

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user
    
#category and recipe serializers

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'
        
class RecipeSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False)
    created_by = serializers.ReadOnlyField(source='created_by.username')
    category_name = serializers.ReadOnlyField(source='category.name') 
    process = serializers.CharField(allow_blank=True, required=False, default="")
    
    class Meta:
        model = Recipe
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at']
        
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
    
class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['email']
        
class PurchasedRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchasedRecipe
        fields = '__all__'
        read_only_fields = ['user', 'created_at']
        
class CartItemSerializer(serializers.ModelSerializer):
    recipe = RecipeSerializer(read_only=True)  # nested for GET
    recipe_id = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.all(),
        source='recipe',
        write_only=True
    )

    class Meta:
        model = CartItem
        fields = ['id', 'user', 'recipe', 'recipe_id']
        read_only_fields = ['user']

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['user', 'recipe', 'payment_id', 'created_at']
        read_only_fields = ['user', 'created_at']
