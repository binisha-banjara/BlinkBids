from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Cart, CartItems
from .serializers import CartItemsSerializer
from product.models import Product
from account.models import User
from .models import Order, OrderItem
from .serializers import OrderSerializer
from rest_framework.generics import ListAPIView


class AddToCartView(APIView):
    def patch(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_authenticated:
            return Response("You are not logged in", status=status.HTTP_403_FORBIDDEN)

        product_id = request.data.get("product_id")
        if not product_id:
            return Response("Product ID is required", status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response("Product not found", status=status.HTTP_404_NOT_FOUND)

        cart, created = Cart.objects.get_or_create(user=user)
        cart_item, item_created = CartItems.objects.get_or_create(cart=cart, product=product, user=user)

        if not item_created:
            cart_item.quantity += 1
            cart_item.save()

        return Response("Product added to cart", status=status.HTTP_200_OK)
    

class RemoveFromCartView(APIView):
    def delete(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_authenticated:
            return Response("You are not logged in", status=status.HTTP_403_FORBIDDEN)
        
        product_id = request.data.get("product_id")
        print(product_id)
        if not product_id:
            return Response(
                "Product ID is required", status=status.HTTP_400_BAD_REQUEST
            )

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response("Product not found", status=status.HTTP_404_NOT_FOUND)

        
        print(product)
        cart_item = CartItems.objects.filter(id = product_id).first()
       
        
        if not cart_item:
            return Response(
                "Product not found in your cart", status=status.HTTP_404_NOT_FOUND
            )

        cart_item.delete()
        return Response("Product removed from cart", status=status.HTTP_200_OK)
    
class UpdateCartItemView(APIView):
    def patch(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_authenticated:
            return Response("You are not logged in", status=status.HTTP_403_FORBIDDEN)

        product_id = request.data.get("product_id")
        quantity = request.data.get("quantity")

        if not product_id or not quantity:
            return Response(
                "Product ID and quantity are required",
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response("Product not found", status=status.HTTP_404_NOT_FOUND)

        cart, _ = Cart.objects.get_or_create(user=user)
        cart_item, created = CartItems.objects.get_or_create(
            cart=cart, product=product, user=user
        )

        if int(quantity) <= 0:
            cart_item.delete()
            return Response("Product removed from cart", status=status.HTTP_200_OK)
        else:
            cart_item.quantity = quantity
            cart_item.save()
            return Response("Quantity updated in cart", status=status.HTTP_200_OK)

class CartDetailView(APIView):
    def get(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_authenticated:
            return Response("You are not logged in", status=status.HTTP_403_FORBIDDEN)

        cart_items = CartItems.objects.filter(user=user)
        serializer = CartItemsSerializer(cart_items, many=True)
        print(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CheckoutView(APIView):
    def post(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_authenticated:
            return Response("You are not logged in", status=status.HTTP_403_FORBIDDEN)

        cart_items = CartItems.objects.filter(cart__user=user)
        if not cart_items:
            return Response("Your cart is empty", status=status.HTTP_400_BAD_REQUEST)

        
        order = Order.objects.create(user=user,payment_method = "cod",is_paid= False)

        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                
            )
            cart_item.delete()

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    


class GetUserOrders(ListAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        queryset = Order.objects.filter(user_id=self.request.user.id)

        return queryset
    
