from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, DestroyAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Product, Category
from .serializers import (
    ProductSerializer,
    ProductCreateSerializer,
    ProductUpdateSerializer,
    CategorySerializer,
    HomePageCategorySerializer,
    ProductSearchSerializer

)
import os
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from BlinkBids.pagination import PageNumberPaginationWithCount

from rest_framework.decorators import api_view
import json
import base64
import hmac
import hashlib
from django.conf import settings
from carts.models import CartItems, Order, OrderItem

def upload_images(images,product_id):
    if not os.path.exists(f"media/{product_id}"):
        os.makedirs(f"media/{product_id}")
    image_names = []
    for image in images:
        image_name = image.name
        image_names.append(image_name)
        with open(os.path.join(f"media/{product_id}", image_name), "wb+") as f:
            for chunk in image.chunks():
                f.write(chunk)
    return image_names

class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

class HomepageProducts(ListAPIView):
    serializer_class = HomePageCategorySerializer

    def get_queryset(self):
        # Get the last 5 categories
        last_categories = Category.objects.order_by('-id')[:8]

        # Prepare data structure to hold categories and their products
        categories_data = []

        for category in last_categories:
            category_data = CategorySerializer(category).data
            products = Product.objects.filter(category=category)[:10]
            products_data = ProductSerializer(products, many=True).data
            category_data['category_products'] = products_data
            categories_data.append(category_data)

        return categories_data

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response(queryset)


# Product CRUD
class ProductList(ListAPIView):
    serializer_class = ProductSerializer
    pagination_class = PageNumberPaginationWithCount

    def get_queryset(self):
        category_name = self.request.query_params.get("category")
        if category_name:
            category = get_object_or_404(Category, name=category_name)
            return Product.objects.filter(category=category)
        return Product.objects.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    


class ProductCreate(APIView):
    queryset = Product.objects.all()
    serializer_class = ProductCreateSerializer

    def post(self, request, *args, **kwargs):
        data = request.data
        images = request.FILES.getlist("new_images", [])
        
        category_name = data.get("category_name")

        try:
            category = Category.objects.get(name=category_name)
        except Category.DoesNotExist:
            raise ValidationError(
                f"Category with name '{category_name}' does not exist."
            )
        data["category"] = category.id

        serializer = ProductCreateSerializer(data=data)
        if serializer.is_valid():
            product = serializer.save()
            
            image_names = upload_images(images, product.id)
            product.images.clear()
            product.images.set(image_names)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductUpdate(UpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductUpdateSerializer


class ProductDelete(DestroyAPIView):
    queryset = Product.objects.all()

class ProductDetail(RetrieveAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'slug'

class ProductSearch(ListAPIView):
    serializer_class = ProductSearchSerializer
    pagination_class = PageNumberPaginationWithCount
    def get_queryset(self):
        search = self.request.query_params.get("query", None)
        if search:
            queryset = Product.objects.filter(title__icontains=search)
        else:
            queryset = Product.objects.all()
       
        return queryset
#Category CRUD
class CategoryList(ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    

class CategoryCreate(CreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class CategoryUpdate(UpdateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class CategoryDelete(DestroyAPIView):
    queryset = Category.objects.all()

# Product filter

# class ProductFilter(APIView):
#     def get(self, request):
#         category = self.request.query_params.get("name", None)
#         if category:
#             queryset = Product.objects.filter(category__name=category)
#         else:
#             queryset = Product.objects.all()
#         serializer = ProductSerializer(queryset, many=True)
            
#         return Response({"count": len(serializer.data), 'data': serializer.data})  



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