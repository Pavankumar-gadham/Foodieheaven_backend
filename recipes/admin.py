from django.contrib import admin
from .models import Category, Recipe, Subscription, PurchasedRecipe, Order, CartItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['email', 'subscribed_at']
    
admin.site.register(PurchasedRecipe)
admin.site.register(Order)
admin.site.register(CartItem)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'category', 'created_by', 'created_at']
    list_filter = ['category', 'created_by']
    search_fields = ['title', 'description']
