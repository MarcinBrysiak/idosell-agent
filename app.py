import json
import os
from datetime import date

import streamlit as st

# Ustaw zmienne środowiskowe ze Streamlit Secrets przed importem modułów
try:
    for key in ["ANTHROPIC_API_KEY", "IDOSELL_API_KEY", "IDOSELL_SHOP_URL",
                "GA4_PROPERTY_ID", "GA4_CREDENTIALS_PATH", "GA4_CREDENTIALS_JSON"]:
        if key in st.secrets:
            os.environ[key] = st.secrets[key]
except Exception:
    pass  # lokalnie używamy .env

from dotenv import load_dotenv
load_dotenv()

import anthropic
from tools.idosell import (
    get_orders,
    get_revenue_summary,
    get_top_products,
    get_stock_levels,
)
from tools.ga4 import get_ga4_report

load_dotenv()

# ── Konfiguracja strony ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Agent analityczny – pieczoneiwedzone.pl",
    page_icon="🥩",
    layout="centered",
)

st.title("🥩 Agent analityczny")
st.caption("pieczoneiwedzone.pl — sprzedaż, zamówienia, produkty, ruch GA4")


# ── Stałe (z agent.py) ────────────────────────────────────────────────────────
MODEL = "claude-opus-4-5"

TOOLS = [
    {
        "name": "get_orders",
        "description": "Pobiera listę zamówień ze sklepu pieczoneiwedzone.pl z IdoSell za podany okres czasu.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "description": "Data początkowa YYYY-MM-DD"},
                "date_to":   {"type": "string", "description": "Data końcowa YYYY-MM-DD"},
                "status":    {"type": "string", "description": "Opcjonalny filtr statusu"},
            },
            "required": ["date_from", "date_to"],
        },
    },
    {
        "name": "get_revenue_summary",
        "description": "Oblicza podsumowanie przychodów (łączna sprzedaż, liczba zamówień, średnia wartość koszyka).",
        "input_schema": {
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "description": "Data początkowa YYYY-MM-DD"},
                "date_to":   {"type": "string", "description": "Data końcowa YYYY-MM-DD"},
            },
            "required": ["date_from", "date_to"],
        },
    },
    {
        "name": "get_top_products",
        "description": "Najlepiej sprzedające się produkty posortowane po wartości sprzedaży.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date_from": {"type": "string", "description": "Data początkowa YYYY-MM-DD"},
                "date_to":   {"type": "string", "description": "Data końcowa YYYY-MM-DD"},
                "limit":     {"type": "integer", "description": "Liczba produktów (domyślnie 10)"},
            },
            "required": ["date_from", "date_to"],
        },
    },
    {
        "name": "get_stock_levels",
        "description": "Produkty z niskim stanem magazynowym (WMS).",
        "input_schema": {
            "type": "object",
            "properties": {
                "low_stock_threshold": {"type": "integer", "description": "Próg niskiego stanu (domyślnie 5)"},
            },
            "required": [],
        },
    },
    {
        "name": "get_ga4_report",
        "description": "Raport ruchu i zachowania użytkowników z Google Analytics 4.",
        "input_schema": {
            "type": "object",
            "properties": {
                "metrics":    {"type": "array", "items": {"type": "string"}, "description": "Lista metryk GA4"},
                "dimensions": {"type": "array", "items": {"type": "string"}, "description": "Lista wymiarów GA4"},
                "date_from":  {"type": "string", "description": "Data początkowa YYYY-MM-DD"},
                "date_to":    {"type": "string", "description": "Data końcowa YYYY-MM-DD"},
            },
            "required": ["metrics", "dimensions", "date_from", "date_to"],
        },
    },
]

SYSTEM_PROMPT = f"""Jesteś analitycznym asystentem sklepu internetowego pieczoneiwedzone.pl,
specjalizującego się w sprzedaży wędlin i wyrobów mięsnych.
Odpowiadasz zawsze po polsku, zwięźle i profesjonalnie.
Podajesz konkretne liczby, trendy i wnioski biznesowe.
Dzisiejsza data: {date.today().strftime('%Y-%m-%d')}."""

MAX_RESULT_CHARS = 20_000


def execute_tool(name: str, tool_input: dict) -> str:
    try:
        if name == "get_orders":
            result = get_orders(**tool_input)
        elif name == "get_revenue_summary":
            result = get_revenue_summary(**tool_input)
        elif name == "get_top_products":
            result = get_top_products(**tool_input)
        elif name == "get_stock_levels":
            result = get_stock_levels(**tool_input)
        elif name == "get_ga4_report":
            result = get_ga4_report(**tool_input)
        else:
            result = {"error": f"Nieznane narzędzie: {name}"}
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if len(text) > MAX_RESULT_CHARS:
            text = text[:MAX_RESULT_CHARS] + f"\n...[PRZYCIĘTO]"
        return text
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def run_agent(question: str, status_placeholder) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    messages = [{"role": "user", "content": question}]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
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
                status_placeholder.info(f"⚙️ Pobieram dane: `{block.name}`…")
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


# ── Historia czatu ────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🥩"):
        st.markdown(msg["content"])

# ── Pole wejściowe ────────────────────────────────────────────────────────────
if prompt := st.chat_input("Zadaj pytanie o sprzedaż, produkty lub ruch na stronie…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🥩"):
        status = st.empty()
        status.info("🔍 Analizuję…")
        try:
            answer = run_agent(prompt, status)
            status.empty()
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as e:
            status.empty()
            st.error(f"Błąd: {e}")

# ── Stopka ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("Przykłady: *Ile zarobiliśmy w tym miesiącu?* · *Top 10 produktów w marcu* · *Skąd pochodzi ruch na stronie?*")
