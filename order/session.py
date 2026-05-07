
from order.models import *
from product.models import *

class OrderSession:
    def __init__(self, request):
        self.request = request
        self.session = request.session
        cart = self.session.get("cart")
        if not cart:
            cart = {}
            self.session["cart"] = cart
        self.cart = cart

    def __iter__(self):
        cart = self.cart.copy()
        for key, item in cart.items():
            product = Product.objects.get(id=item['product_id'])
            pricing_tab = ProductPricingTab.objects.get(id=item['pricing_tab_id'])
            size = Size.objects.get(id=item['size']) if item.get('size') else None
            item['product'] = product
            item['pricing_tab'] = pricing_tab
            item['size_obj'] = size
            item['total_price'] = int(item['price']) * item['quantity']
            item['id_unique'] = key
            yield item

    def unique_code(self, product_id,pricing_tab_id,size_id,material):
        return f"{product_id}-{pricing_tab_id}-{size_id}--{material}"

    def add_cart(self, product_id,pricing_tab_id, size_id, material, quantity):
        try :
            product = Product.objects.get(id=product_id)
            pricing_tab = ProductPricingTab.objects.get(id=pricing_tab_id,product = product)
        except (Product.DoesNotExist , ProductPricingTab.DoesNotExist):
            raise ValueError("محصول یا سرویس نامعتبر است.")
        try:
            material_price = MaterialPrice.objects.get(material=material,pricing_tab = pricing_tab)
            price =material_price.price
        except (MaterialPrice.DoesNotExist):
            raise ValueError(f"جنس{material} برای این محصول نیست")
        size = None
        if size_id :
            try:
                size = Size.objects.get(id=size_id)
            except Size.DoesNotExist:
                raise ValueError("این سایز وجود ندارد.")
        id_unique = self.unique_code(product_id,pricing_tab_id,size_id,material)
        if id_unique not in self.cart:
            self.cart[id_unique] = {
                "quantity": quantity,
                "size": size_id,
                "material": material,
                "product_id": product_id,
                "product_name":product.title,
                "pricing_tab_id": pricing_tab.id,
                "pricing_tab_service" : pricing_tab.tab_name,
                 "size_display":size ,
                "price": str(price),
                "id": str(product.id),
            }
        else:
            self.cart[id_unique]["quantity"] += quantity
        self.session["cart"] = self.cart
        self.session.modified = True

    def remove_cart(self, id_unique):
        if id_unique in self.cart:
            if self.cart[id_unique]["quantity"] > 0:
                self.cart[id_unique]["quantity"] -= 1
                if self.cart[id_unique]["quantity"] == 0:
                    del self.cart[id_unique]
            self.session["cart"] = self.cart
            self.session.modified = True

    def total_price(self):
        total_price = 0
        for item in self.cart.values():
            total_price += int(item["price"]) * item["quantity"]
        return total_price

    def clear(self):
        self.session["cart"] = {}
        self.session.modified = True



