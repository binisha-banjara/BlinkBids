from django.db import models
from account.models import User
from product.models import Product

# Create your models here.
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ordered = models.BooleanField(default=False)
    

    def __str__(self):
        return self.user.email
    
    @property
    def total_price(self):
        return sum(item.price * item.quantity for item in self.cart_items.all())

    @property
    def cart_items(self):
        return str(item for item in self.cart_items.all())
    
class CartItems(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE,related_name="cart_items")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.product.title}[{self.quantity}] - {self.user.email}"


import uuid
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=50)
    is_paid = models.BooleanField(default=False)
    pub_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    @property
    def total_price(self):
        return sum(item.total_price for item in self.order_items.all())
    
    @property
    def order_items(self):
        return str(item for item in self.order_items.all())

    def __str__(self):
        return self.user.email
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE,related_name="order_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def total_price(self):
        return self.quantity * self.product.price

    def __str__(self):
        return f"{self.product.title}[{self.quantity}] - {self.order.user.email}"