# Agent analityczny — pieczoneiwedzone.pl

## Opis projektu

Agent analityczny dla sklepu internetowego **pieczoneiwedzone.pl**, specjalizującego się w sprzedaży wędlin i wyrobów mięsnych (pieczone, wędzone, kiełbasy, szynki, salami i inne wyroby mięsne). Sklep działa na platformie **IdoSell** — polskiej platformie e-commerce.

## Cel agenta

Agent umożliwia właścicielom i menedżerom sklepu zadawanie pytań w języku polskim i uzyskiwanie odpowiedzi opartych na danych z:
- **IdoSell Admin API** — zamówienia, przychody, produkty, stany magazynowe
- **Google Analytics 4** — ruch na stronie, zachowanie użytkowników, źródła ruchu, konwersje

## Struktura projektu

```
idosell-agent/
├── agent.py              # Główna pętla agenta z Claude claude-opus-4-5
├── requirements.txt      # Zależności Python
├── .env                  # Zmienne środowiskowe (nie commitować!)
├── CLAUDE.md             # Ten plik
└── tools/
    ├── __init__.py
    ├── idosell.py        # Integracja z IdoSell Admin API
    └── ga4.py            # Integracja z Google Analytics 4
```

## Konfiguracja (.env)

```env
ANTHROPIC_API_KEY=twoj_klucz_anthropic
IDOSELL_API_KEY=twoj_klucz_idosell
IDOSELL_SHOP_URL=https://pieczoneiwedzone.pl
GA4_CREDENTIALS_PATH=./idosell-agent-a6f6c6c686c4.json
GA4_PROPERTY_ID=twoje_property_id
```

## Dostępne narzędzia agenta

| Narzędzie | Opis |
|-----------|------|
| `get_orders` | Lista zamówień za podany okres z filtrami |
| `get_revenue_summary` | Suma przychodów, liczba zamówień, średnia wartość koszyka |
| `get_top_products` | Ranking produktów po wartości sprzedaży |
| `get_stock_levels` | Produkty z niskim stanem magazynowym (WMS) |
| `get_ga4_report` | Raport ruchu i zachowania użytkowników z GA4 |

## Uruchomienie

```bash
# Aktywacja środowiska
source venv/bin/activate

# Uruchomienie agenta
python agent.py
```

## Przykładowe pytania

- "Ile zarobiliśmy w tym miesiącu?"
- "Jakie produkty sprzedały się najlepiej w ostatnim kwartale?"
- "Które produkty mają niski stan magazynowy?"
- "Skąd pochodzi ruch na stronie w tym tygodniu?"
- "Ile mieliśmy zamówień w zeszłym tygodniu i jaka była średnia wartość koszyka?"
- "Porównaj sprzedaż tego miesiąca z poprzednim"

## Model AI

Agent używa modelu **claude-opus-4-5** przez Anthropic API z mechanizmem tool use — samodzielnie decyduje, które narzędzia wywołać, aby odpowiedzieć na pytanie użytkownika.
