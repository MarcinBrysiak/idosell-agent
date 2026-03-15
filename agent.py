import json
import os
from dotenv import load_dotenv
import anthropic

from tools.idosell import (
    get_orders,
    get_revenue_summary,
    get_top_products,
    get_stock_levels,
)
from tools.ga4 import get_ga4_report

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-opus-4-5"

TOOLS = [
    {
        "name": "get_orders",
        "description": (
            "Pobiera listę zamówień ze sklepu pieczoneiwedzone.pl z IdoSell "
            "za podany okres czasu. Zwraca szczegóły zamówień takie jak "
            "wartość, produkty, status i dane klienta."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date_from": {
                    "type": "string",
                    "description": "Data początkowa w formacie YYYY-MM-DD",
                },
                "date_to": {
                    "type": "string",
                    "description": "Data końcowa w formacie YYYY-MM-DD",
                },
                "status": {
                    "type": "string",
                    "description": "Opcjonalny filtr statusu zamówienia (np. 'completed', 'pending')",
                },
            },
            "required": ["date_from", "date_to"],
        },
    },
    {
        "name": "get_revenue_summary",
        "description": (
            "Oblicza podsumowanie przychodów sklepu pieczoneiwedzone.pl za podany okres. "
            "Zwraca łączną wartość sprzedaży, liczbę zamówień i średnią wartość zamówienia."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date_from": {
                    "type": "string",
                    "description": "Data początkowa w formacie YYYY-MM-DD",
                },
                "date_to": {
                    "type": "string",
                    "description": "Data końcowa w formacie YYYY-MM-DD",
                },
            },
            "required": ["date_from", "date_to"],
        },
    },
    {
        "name": "get_top_products",
        "description": (
            "Zwraca listę najlepiej sprzedających się produktów ze sklepu "
            "pieczoneiwedzone.pl posortowanych po wartości sprzedaży za dany okres. "
            "Przydatne do analizy popularności produktów z oferty wędliniarskiej."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date_from": {
                    "type": "string",
                    "description": "Data początkowa w formacie YYYY-MM-DD",
                },
                "date_to": {
                    "type": "string",
                    "description": "Data końcowa w formacie YYYY-MM-DD",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maksymalna liczba produktów do zwrócenia (domyślnie 10)",
                    "default": 10,
                },
            },
            "required": ["date_from", "date_to"],
        },
    },
    {
        "name": "get_stock_levels",
        "description": (
            "Sprawdza stany magazynowe w WMS sklepu pieczoneiwedzone.pl. "
            "Zwraca produkty z niskim stanem magazynowym poniżej podanego progu, "
            "co pozwala wykryć produkty wymagające uzupełnienia zapasów."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "low_stock_threshold": {
                    "type": "integer",
                    "description": "Próg niskiego stanu magazynowego w sztukach (domyślnie 5)",
                    "default": 5,
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_ga4_report",
        "description": (
            "Pobiera raport analityczny z Google Analytics 4 dla strony pieczoneiwedzone.pl. "
            "Umożliwia analizę ruchu na stronie, źródeł odwiedzin, zachowania użytkowników "
            "i konwersji. Metryki: sessions, activeUsers, screenPageViews, bounceRate, "
            "averageSessionDuration, conversions. "
            "Wymiary: date, country, city, pagePath, sessionSource, sessionMedium, deviceCategory."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Lista metryk GA4 do pobrania, np. "
                        '["sessions", "activeUsers", "screenPageViews"]'
                    ),
                },
                "dimensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Lista wymiarów GA4, np. "
                        '["date", "sessionSource", "deviceCategory"]'
                    ),
                },
                "date_from": {
                    "type": "string",
                    "description": "Data początkowa w formacie YYYY-MM-DD",
                },
                "date_to": {
                    "type": "string",
                    "description": "Data końcowa w formacie YYYY-MM-DD",
                },
            },
            "required": ["metrics", "dimensions", "date_from", "date_to"],
        },
    },
]

SYSTEM_PROMPT = """Jesteś analitycznym asystentem sklepu internetowego pieczoneiwedzone.pl,
specjalizującego się w sprzedaży wędlin i wyrobów mięsnych (pieczone, wędzone, kiełbasy, szynki, itp.).
Sklep działa na platformie IdoSell (polska platforma e-commerce).

Twoim zadaniem jest analiza danych sprzedażowych, zamówień, produktów i ruchu na stronie.
Odpowiadasz zawsze po polsku, w sposób zwięzły i profesjonalny.
Gdy dostaniesz pytanie analityczne, korzystaj z dostępnych narzędzi aby pobrać potrzebne dane.
Podawaj konkretne liczby, trendy i wnioski biznesowe.

Dostępne narzędzia:
- Dane zamówień i sprzedaży z IdoSell API
- Stany magazynowe z WMS
- Ruch na stronie i zachowanie użytkowników z Google Analytics 4
"""


MAX_RESULT_CHARS = 20_000


def execute_tool(tool_name: str, tool_input: dict):
    """Wykonuje wywołanie narzędzia i zwraca wynik."""
    try:
        if tool_name == "get_orders":
            result = get_orders(**tool_input)
        elif tool_name == "get_revenue_summary":
            result = get_revenue_summary(**tool_input)
        elif tool_name == "get_top_products":
            result = get_top_products(**tool_input)
        elif tool_name == "get_stock_levels":
            result = get_stock_levels(**tool_input)
        elif tool_name == "get_ga4_report":
            result = get_ga4_report(**tool_input)
        else:
            result = {"error": f"Nieznane narzędzie: {tool_name}"}
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if len(text) > MAX_RESULT_CHARS:
            text = text[:MAX_RESULT_CHARS] + f"\n... [PRZYCIĘTO — pełny wynik miał {len(text)} znaków]"
        return text
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def run_agent(user_question: str) -> str:
    """Uruchamia pętlę agenta dla podanego pytania użytkownika."""
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")
    system = f"{SYSTEM_PROMPT}\n\nDzisiejsza data: {today}."

    messages = [{"role": "user", "content": user_question}]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if block.type == "text":
                    return block.text
            return ""

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"  [Wywołuję: {block.name}({json.dumps(block.input, ensure_ascii=False)})]")
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        else:
            for block in response.content:
                if block.type == "text":
                    return block.text
            return ""


def main():
    print("=" * 60)
    print("Agent analityczny - pieczoneiwedzone.pl")
    print("Wpisz pytanie po polsku lub 'exit' aby zakończyć.")
    print("=" * 60)

    while True:
        try:
            question = input("\nPytanie: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nDo widzenia!")
            break

        if question.lower() == "exit":
            print("Do widzenia!")
            break

        if not question:
            continue

        print("\nAnalizuję...")
        try:
            answer = run_agent(question)
            print(f"\nOdpowiedź:\n{answer}")
        except Exception as e:
            print(f"\nBłąd: {e}")


if __name__ == "__main__":
    main()
