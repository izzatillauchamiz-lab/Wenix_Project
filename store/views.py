from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import Product, Category, Order, OrderItem
from .forms import RegisterForm
import requests 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import OrderSerializer

def index(request):
    items = Product.objects.all().order_by("-created_at")[:8]
    return render(request, "store/index.html", {"items": items})

def products(request):
    cat = request.GET.get("cat")
    cats = Category.objects.all()
    if cat:
        items = Product.objects.filter(category_id=cat)
    else:
        items = Product.objects.all()
    return render(request, "store/products.html", {"items": items, "cats": cats})

def search(request):
    q = request.GET.get("q", "").strip()
    results = Product.objects.none()
    if q:
        results = Product.objects.filter(title__icontains=q) | Product.objects.filter(description__icontains=q)
    return render(request, "store/search.html", {"q": q, "results": results})

def product_detail(request, pk):
    p = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        # allow anonymous users to add items to the session-based cart
        qty = int(request.POST.get("qty", 1))
        cart = request.session.get("cart", {})
        cart[str(p.id)] = cart.get(str(p.id), 0) + qty
        request.session["cart"] = cart
        request.session.modified = True
        return redirect("cart")
    return render(request, "store/product_detail.html", {"p": p})

def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("index")
    else:
        form = RegisterForm()
    return render(request, "store/register.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("index")
        else:
            return render(request, "store/login.html", {"error": "Invalid credentials"})
    return render(request, "store/login.html")

def logout_view(request):
    logout(request)
    return redirect("index")

def cart_view(request):
    cart = request.session.get("cart", {})
    items = []
    total = 0
    ordered_ids = set()
    last_order = None
    if request.user.is_authenticated:
        last_order = Order.objects.filter(user=request.user).order_by('-created_at').first()
        if last_order:
            ordered_ids = set([str(item.product_id) for item in last_order.items.all()])
    if cart:
        ids = [int(k) for k in cart.keys()]
        qs = Product.objects.filter(id__in=ids)
        for p in qs:
            q = cart.get(str(p.id), 0)
            s = p.price * q
            is_ordered = str(p.id) in ordered_ids
            items.append({"p": p, "qty": q, "sum": s, "ordered": is_ordered})
            total += s
    if request.GET.get("remove"):
        rid = request.GET.get("remove")
        cart = request.session.get("cart", {})
        if rid in cart:
            del cart[rid]
            request.session["cart"] = cart
            request.session.modified = True
            return redirect("cart")
    return render(request, "store/cart.html", {"items": items, "total": total})

@login_required
@transaction.atomic
def checkout_view(request):
    cart = request.session.get("cart", {})
    if not cart:
        return redirect("cart")
    name = ""
    surname = ""
    phone = ""
    error = ""
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        surname = request.POST.get("surname", "").strip()
        phone = request.POST.get("phone", "").strip()
        if not name or not surname or not phone:
            error = "Iltimos, ism, familiya va telefon raqamni to'ldiring!"
            return render(request, "store/checkout.html", {"error": error, "name": name, "surname": surname, "phone": phone})
        ids = [int(k) for k in cart.keys()]
        qs = Product.objects.filter(id__in=ids)
        order = Order.objects.create(user=request.user, name=name, surname=surname, phone=phone)
        total = 0
        products_api = []
        for p in qs:
            qty = cart.get(str(p.id), 0)
            price = p.price
            if p.stock < qty:
                error = f"{p.title} uchun yetarli mahsulot yo'q. Qolgan: {p.stock}"
                return render(request, "store/checkout.html", {"error": error, "name": name, "surname": surname, "phone": phone})
            OrderItem.objects.create(order=order, product=p, qty=qty, price=price)
            p.stock -= qty
            p.save()
            total += price * qty
            products_api.append({"id": p.id, "title": p.title, "qty": qty, "price": float(price)})
        order.total = total
        order.save()
        # Send order to external API
        api_url = "https://example.com/api/orders/"  # Замените на ваш URL
        payload = {
            "order_id": order.id,
            "user": request.user.username,
            "name": name,
            "surname": surname,
            "phone": phone,
            "total": float(order.total),
            "products": products_api
        }
        try:
            requests.post(api_url, json=payload, timeout=5)
        except Exception:
            pass
        # Clear the cart after successful order
        request.session["cart"] = {}
        request.session.modified = True
        return render(request, "store/thanks.html", {"order": order, "name": name, "surname": surname, "phone": phone})
    return render(request, "store/checkout.html")

class OrderAPIView(APIView):
    def get(self, request):
        orders = Order.objects.all().order_by('-created_at')
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    def post(self, request):
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
