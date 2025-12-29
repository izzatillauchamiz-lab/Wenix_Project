from django.contrib import admin
from .models import Category, Product, Order, OrderItem

class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "price", "stock", "is_new", "created_at")
    list_filter = ("category", "is_new")
    search_fields = ("title",)

admin.site.register(Category)
admin.site.register(Product, ProductAdmin)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "qty", "price")

class OrderAdmin(admin.ModelAdmin):
    def order_summary(self, obj):
        return ", ".join([f"{item.product} (x{item.qty})" for item in obj.items.all()])
    order_summary.short_description = "Ordered Products"
    list_display = ("id", "user", "name", "surname", "phone", "order_summary", "total", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "name", "surname", "phone")
    inlines = [OrderItemInline]
    readonly_fields = ("user", "name", "surname", "phone", "total", "created_at")

admin.site.register(Order, OrderAdmin)
