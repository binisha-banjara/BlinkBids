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
from rest_framework.decorators import api_view
import json
import base64
import hmac
import hashlib
from django.conf import settings

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
    

def gensignature(order, data_to_sign):
    SECRET_KEY = "8gBm/:&EnhH.1/q"
    key = SECRET_KEY.encode("utf-8")
    message = data_to_sign.encode("utf-8")
    hmac_sha256 = hmac.new(key, message, hashlib.sha256)
    digest = hmac_sha256.digest()
    signature = base64.b64encode(digest).decode("utf-8")

    return signature


@api_view(["POST"])
def pay_with_esewa(request):
    try:
        user = request.user
        cart_items = CartItems.objects.filter(cart__user=user)
        if not cart_items:
            return Response("Your cart is empty", status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.create(user=user,payment_method = "esewa",is_paid= False)

        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                
            )
            cart_item.delete()

        
        data_to_sign = f"total_amount={order.total_price},transaction_uuid={order.id},product_code=EPAYTEST"
        signature = gensignature(order, data_to_sign)
        
        esewa_request = {
            "amount": str(order.total_price),
            "tax_amount": "0",
            "total_amount": str(order.total_price),
            "transaction_uuid": str(order.id),
            "product_code": "EPAYTEST",
            "product_service_charge": "0",
            "product_delivery_charge": "0",
            "success_url": f"{settings.FRONTEND_BASE_URL}/user/payment",
            "failure_url": f"{settings.FRONTEND_BASE_URL}",
            "signed_field_names": "total_amount,transaction_uuid,product_code",
            "signature": str(signature),
        }

        return Response(esewa_request, status=status.HTTP_201_CREATED)

    except Exception as e:
        print(e)
        return Response(status=status.HTTP_400_BAD_REQUEST)


# The following function is very ugly but i have already spent 2h 38 mins on it. Please refactor later let me be happy rn
@api_view(["POST"])
def verify_esewa_payment(request):
    data = request.data
    decoded_data = json.loads(base64.b64decode(data["data"]).decode("utf-8"))

    order = Order.objects.get(pub_id=decoded_data["transaction_uuid"])
    data_to_sign = f"transaction_code={decoded_data['transaction_code']},status={decoded_data['status']},total_amount={str(decoded_data['total_amount']).replace(',','')},transaction_uuid={decoded_data['transaction_uuid']},product_code=NP-ES-FATAFAT,signed_field_names=transaction_code,status,total_amount,transaction_uuid,product_code,signed_field_names"
    order_signature = gensignature(order, data_to_sign)

    if decoded_data["signature"] == order_signature:
        order.is_paid = True
        order.save()
        return Response(status=status.HTTP_200_OK)
    else:
        print("signatures are diff")
        order.delete()
        return Response(
            {"detail": "Could not verify esewa payment"},
            status=status.HTTP_400_BAD_REQUEST,
        )