from django.contrib import admin

from .models import Category, Order, OrderLine, OrderStatusHistory, Product, ProductImage, StockMovement


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "position")


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "platform", "price", "stock", "is_published")
    list_filter = ("category", "platform", "is_published")
    search_fields = ("name", "sku")
    inlines = [ProductImageInline]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "product", "kind", "quantity", "stock_after", "author", "reason")
    readonly_fields = [f.name for f in StockMovement._meta.fields]


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0


class HistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "created_at", "first_name", "last_name", "total", "status")
    list_filter = ("status", "delivery_mode")
    search_fields = ("reference", "email", "last_name")
    inlines = [OrderLineInline, HistoryInline]
