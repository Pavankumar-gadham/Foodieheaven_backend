from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name
    
class Recipe(models.Model):
    title = models.CharField(max_length=100, db_index=True)
    image = models.ImageField(upload_to='recipes/', null=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    preparation_time = models.PositiveIntegerField(null=True, blank=True, help_text="Time in minutes to prepare the ingredients")
    cooking_time = models.PositiveIntegerField(null=True, blank=True, help_text="Time in minutes to cook the recipe")
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, help_text="Average rating out of 5.0")
    process = models.TextField(help_text="Step-by-step process to prepare the recipe", null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=7, decimal_places=2, default=100)
    is_public = models.BooleanField(default=False)

    
    def __str__(self):
        return self.title
    
class Subscription(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
    
class PurchasedRecipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'recipe')

    def __str__(self):
        return f"{self.user.username} purchased {self.recipe.title}"


class CartItem(models.Model):
    #user = models.ForeignKey(User, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
