from django.contrib import admin
from .models import Category, Product, ProductPricingTab, MaterialPrice, Size

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(ProductPricingTab)
admin.site.register(MaterialPrice)
admin.site.register(Size)
