from product.models import Product


class OrderSession:
    def __init__(self):
        self.session = request.session
        cart = self.session.get('cart')  # Shopping cart information
        if not cart:
            cart = {}
            self.session['cart'] = cart
        self.cart = cart
    def __iter__(self):
        cart = self.cart.copy()
        for item in cart.values():
            item['product'] = Product.objects.get(id=item['id'])
            item['total_price'] = int(item['price']) * item['quantity']
            item['id_unique'] = self.unique(item["size"] ,item['name'],item['id'])
            yield item

    def unique_code(self,size,name,id):
        return f'{size}-{name}-{id}'

    def add_cart(self,product,size,material,service,quantity):
       id = self.unique_code(product.size,product.name,product.id)
       if id not in self.cart:
           self.session['cart']['id'] = {
               'quantity': 0, 'size': size, "sercice":service,"material":material,'price': str(product.price),
               'id': str(product.id)}
       else:
           self.session['cart']['id']['quantity'] += quantity

       self.session.modified = True

    def remove_cart(self,id_unique):
        if id_unique  in self.cart:
            if self.session['cart']['id']['quantity'] >0:
                self.session['cart']['id']['quantity'] -= self.cart[id_unique]['quantity']
            if self.session['cart']['id']['quantity'] == 0:
                del self.cart[id_unique]
                self.session.modified = True

    def total_price(self):
        cart = self.cart
        total_price = 0
        for item in cart.values():
             total_price = total_price + int(item['price']) * item['quantity']
        return total_price

    def remove(self):
        del self.session['cart']



