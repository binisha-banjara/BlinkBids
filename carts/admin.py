from django.contrib import admin
from .models import  Cart, CartItems, Order, OrderItem
# Register your models here.

admin.site.register(Cart)
admin.site.register(CartItems)
admin.site.register(Order)
admin.site.register(OrderItem)