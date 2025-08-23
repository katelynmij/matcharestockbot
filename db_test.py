from db import add_product, update_stock, get_products

# add a test product
product_id = add_product("Yugen Matcha #0", "https://www.yugen-kyoto.com/en-us/products/matcha0-yugen-original-blend")
print(f"✅ Added product with id {product_id}")

# update stock
update_stock(product_id, True)
print(f"✅ Updated stock for product {product_id}")

# fetch all products
products = get_products()
for p in products:
    print(p)

