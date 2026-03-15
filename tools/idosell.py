import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("IDOSELL_API_KEY")
SHOP_URL = os.getenv("IDOSELL_SHOP_URL", "").rstrip("/")
BASE_URL = f"{SHOP_URL}/api/admin/v3"


def _headers():
    return {
        "X-API-KEY": API_KEY,
        "Content-Type": "application/json",
    }


def _search_orders(params: dict) -> list:
    """Wewnętrzna funkcja wyszukiwania zamówień przez POST /orders/search — z paginacją."""
    url = f"{BASE_URL}/orders/search"
    all_results = []
    page = 0
    page_size = 100

    while True:
        paged_params = {**params, "resultsPage": page, "resultsLimit": page_size}
        response = requests.post(url, headers=_headers(), json={"params": paged_params}, timeout=15)
        data = response.json()

        if response.status_code == 207 or "errors" in data:
            errors = data.get("errors", {})
            if isinstance(errors, dict) and errors.get("faultCode") == 2:
                break  # brak wyników — koniec
            response.raise_for_status()

        results = data.get("Results", [])
        all_results.extend(results)

        if len(results) < page_size:
            break  # ostatnia strona
        page += 1

    return all_results


def get_orders(date_from: str, date_to: str, status: str = None, limit: int = 100) -> dict:
    """
    Pobiera zamówienia z IdoSell za podany okres.

    Args:
        date_from: Data początkowa w formacie YYYY-MM-DD
        date_to: Data końcowa w formacie YYYY-MM-DD
        status: Opcjonalny filtr statusu zamówienia
        limit: Maks. liczba wyników (1–100)

    Returns:
        Słownik z listą zamówień i metadanymi
    """
    params = {
        "ordersRange": {
            "ordersDateRange": {
                "ordersDateType": "add",
                "ordersDateBegin": f"{date_from} 00:00:00",
                "ordersDateEnd": f"{date_to} 23:59:59",
            }
        },
    }
    if status:
        params["ordersStatuses"] = [status]

    orders = _search_orders(params)
    return {"orders": orders, "order_count": len(orders), "date_from": date_from, "date_to": date_to}


def get_revenue_summary(date_from: str, date_to: str) -> dict:
    """
    Oblicza sumę wartości zamówień za podany okres.

    Args:
        date_from: Data początkowa w formacie YYYY-MM-DD
        date_to: Data końcowa w formacie YYYY-MM-DD

    Returns:
        Słownik z podsumowaniem przychodów (suma, liczba zamówień, średnia wartość)
    """
    data = get_orders(date_from, date_to)
    orders = data.get("orders", [])

    total_revenue = 0.0
    for order in orders:
        cost = order.get("orderDetails", {}).get("payments", {}) \
                    .get("orderCurrency", {}).get("orderProductsCost", 0)
        total_revenue += float(cost)

    order_count = len(orders)
    avg_order_value = total_revenue / order_count if order_count > 0 else 0.0

    return {
        "date_from": date_from,
        "date_to": date_to,
        "total_revenue": round(total_revenue, 2),
        "order_count": order_count,
        "avg_order_value": round(avg_order_value, 2),
        "currency": "PLN",
    }


def get_top_products(date_from: str, date_to: str, limit: int = 10) -> list:
    """
    Zwraca produkty posortowane po wartości sprzedaży za podany okres.

    Args:
        date_from: Data początkowa w formacie YYYY-MM-DD
        date_to: Data końcowa w formacie YYYY-MM-DD
        limit: Maksymalna liczba produktów do zwrócenia (domyślnie 10)

    Returns:
        Lista produktów posortowana malejąco po wartości sprzedaży
    """
    data = get_orders(date_from, date_to)
    orders = data.get("orders", [])

    product_sales = {}
    for order in orders:
        products = order.get("orderDetails", {}).get("productsResults", [])
        for product in products:
            product_id = product.get("productId") or product.get("productDisplayedCode")
            product_name = product.get("productName", f"Produkt {product_id}")
            quantity = float(product.get("productQuantity", 0))
            price = float(product.get("productOrderPriceBaseCurrency") or product.get("productOrderPrice") or 0)
            revenue = quantity * price

            if product_id in product_sales:
                product_sales[product_id]["quantity"] += quantity
                product_sales[product_id]["revenue"] += revenue
            else:
                product_sales[product_id] = {
                    "product_id": product_id,
                    "product_name": product_name,
                    "quantity": quantity,
                    "revenue": revenue,
                }

    sorted_products = sorted(product_sales.values(), key=lambda x: x["revenue"], reverse=True)
    for p in sorted_products:
        p["revenue"] = round(p["revenue"], 2)
        p["quantity"] = round(p["quantity"], 2)

    return sorted_products[:limit]


def get_stock_levels(low_stock_threshold: int = 5) -> list:
    """
    Zwraca produkty z niskim stanem magazynowym z WMS.

    Args:
        low_stock_threshold: Próg niskiego stanu (domyślnie 5 sztuk)

    Returns:
        Lista produktów z ilością poniżej progu
    """
    url = f"{BASE_URL}/wms/products"
    payload = {"params": {"stockMax": low_stock_threshold, "resultsLimit": 100}}

    response = requests.post(url, headers=_headers(), json=payload, timeout=15)
    if response.status_code == 207:
        return []
    response.raise_for_status()
    data = response.json()

    products = data.get("Results", data.get("products", []))
    low_stock = [
        {
            "product_id": p.get("productId"),
            "product_name": p.get("productName"),
            "stock": p.get("productStock", p.get("stock", 0)),
            "threshold": low_stock_threshold,
        }
        for p in products
    ]
    return sorted(low_stock, key=lambda x: float(x["stock"] or 0))
