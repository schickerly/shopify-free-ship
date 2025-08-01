from flask import Flask, request, jsonify
import os
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configuration
SHOP_DOMAIN = "nv-soy-candles.myshopify.com"
ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN")
FREE_SHIPPING_THRESHOLD = float(os.environ.get("FREE_SHIPPING_THRESHOLD", 75))
DISCOUNT_CODE = os.environ.get("FREE_SHIPPING_CODE", "FIRSTSHIP")

@app.route("/")
def home():
    return "Free Shipping Options App is running"

@app.route("/check-free-shipping")
def check_free_shipping():
    customer_id = request.args.get("customer_id")
    cart_total = request.args.get("cart_total")
    debug = request.args.get("debug", "false").lower() == "true"

    # Validate required parameters
    if not ACCESS_TOKEN or not SHOP_DOMAIN:
        return jsonify({"error": "Server not configured"}), 500
    if not customer_id or not cart_total:
        return jsonify({"error": "Missing required parameters"}), 400

    try:
        cart_total = float(cart_total)
    except ValueError:
        return jsonify({"error": "Invalid cart total value"}), 400

    # GraphQL query to get order count
    graphql_query = {
        "query": f"""
        {{
          customer(id: "gid://shopify/Customer/{customer_id}") {{
            orders(first: 1) {{
              edges {{
                node {{
                  id
                }}
              }}
            }}
          }}
        }}
        """
    }

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": ACCESS_TOKEN,
    }

    try:
        response = requests.post(
            f"https://{SHOP_DOMAIN}/admin/api/2023-07/graphql.json",
            json=graphql_query,
            headers=headers,
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        orders = data.get("data", {}).get("customer", {}).get("orders", {}).get("edges", [])
        order_count = len(orders)
    except Exception as e:
        return jsonify({"error": "Customer not found or no order data", "details": str(e)}), 500

    is_first_order = order_count == 0
    eligible = is_first_order and cart_total < FREE_SHIPPING_THRESHOLD

    result = {
        "eligible": eligible,
        "is_first_order": is_first_order,
        "order_count": order_count,
        "discount_code": DISCOUNT_CODE if eligible else None
    }

    if debug:
        print("Debug info:", result)

    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)
