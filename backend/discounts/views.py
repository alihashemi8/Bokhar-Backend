from rest_framework.viewsets import ModelViewSet
from rest_framework import permissions
from django.utils import timezone
from rest_framework import viewsets
from django.db import transaction

from .models import ProductDiscount, GlobalDiscount, Coupon
from .serializers import ProductDiscountSerializer, GlobalDiscountSerializer, CouponSerializer

from rest_framework.response import Response
from rest_framework import status

# ---------------------------------------------------------
#   PERMISSION
# ---------------------------------------------------------
class IsSeller(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and getattr(request.user, "role", None) == "seller"


# ---------------------------------------------------------
#   ProductDiscount

class ProductDiscountViewSet(viewsets.ModelViewSet):
    queryset = ProductDiscount.objects.all()
    serializer_class = ProductDiscountSerializer

    def create(self, request, *args, **kwargs):
        category_id = request.data.get('category_id')
        
        # اگر category_id ارسال شده، تخفیف رو روی همه مواد دسته‌بندی اعمال کن
        if category_id:
            return self._create_category_discount(request, category_id)
        
        # در غیر این صورت، تخفیف معمولی (روی material خاص)
        return super().create(request, *args, **kwargs)
    
    def _create_category_discount(self, request, category_id):
        """ایجاد تخفیف برای همه مواد داخل دسته‌بندی"""
        from backend.products.models import MaterialPrice  # ایمپورت مدل MaterialPrice
        
        # گرفتن همه مواد رنگ/متریال محصولات این دسته
        materials = MaterialPrice.objects.filter(
            pricing_tab__product__category_id=category_id
        ).select_related('pricing_tab__product')
        
        if not materials.exists():
            return Response(
                {"error": "هیچ محصولی با مواد مشخص در این دسته‌بندی یافت نشد"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_discounts = []
        errors = []
        
        with transaction.atomic():
            # اول تخفیف‌های قبلی این دسته رو غیرفعال کن (اختیاری)
            ProductDiscount.objects.filter(
                category_id=category_id,
                is_active=True
            ).update(is_active=False, end_at=timezone.now())
            
            # حالا برای هر material تخفیف جدید بساز
            for material in materials:
                data = {
                    'material': material.id,
                    'product': material.pricing_tab.product.id,
                    'category': category_id,
                    'type': request.data.get('type'),
                    'value': request.data.get('value'),
                    'start_at': request.data.get('start_at'),
                    'end_at': request.data.get('end_at'),
                    'is_active': True
                }
                
                serializer = self.get_serializer(data=data)
                try:
                    serializer.is_valid(raise_exception=True)
                    self.perform_create(serializer)
                    created_discounts.append(serializer.instance)
                except Exception as e:
                    errors.append({
                        'material_id': material.id,
                        'error': str(e)
                    })
        
        if errors and not created_discounts:
            return Response(
                {"errors": errors, "message": "هیچ تخفیفی ایجاد نشد"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(
            {
                "message": f"تخفیف برای {len(created_discounts)} ماده ایجاد شد",
                "discounts": self.get_serializer(created_discounts, many=True).data,
                "errors": errors if errors else None
            },
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        # اگر می‌خوای ویرایش تخفیف دسته‌ای هم کار کنه
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # اگر این تخفیف مربوط به دسته‌بندی بود (category ست شده)
        if instance.category and not kwargs.get('skip_category_update'):
            return self._update_category_discount(request, instance, partial)
        
        return super().update(request, *args, **kwargs)
    
    def _update_category_discount(self, request, instance, partial):
        """به‌روزرسانی همه تخفیف‌های related به یک دسته‌بندی"""
        category_id = instance.category_id
        
        # پیدا کردن همه تخفیف‌های فعال این دسته
        discounts = ProductDiscount.objects.filter(
            category_id=category_id,
            is_active=True
        )
        
        updated = []
        for discount in discounts:
            serializer = self.get_serializer(
                discount, 
                data=request.data, 
                partial=partial
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            updated.append(serializer.data)
        
        return Response(updated[0] if updated else {})
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # اگر تخفیف دسته‌ای بود، همه رو پاک کن
        if instance.category:
            ProductDiscount.objects.filter(
                category_id=instance.category_id,
                is_active=True
            ).update(is_active=False, end_at=timezone.now())
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        return super().destroy(request, *args, **kwargs)


class GlobalDiscountViewSet(ModelViewSet):
    queryset = GlobalDiscount.objects.all()
    serializer_class = GlobalDiscountSerializer
    permission_classes = [IsSeller]


class CouponViewSet(ModelViewSet):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsSeller]
