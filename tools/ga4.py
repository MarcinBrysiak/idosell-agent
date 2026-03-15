import os
from dotenv import load_dotenv
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)
from google.oauth2 import service_account

load_dotenv()

GA4_CREDENTIALS_PATH = os.getenv("GA4_CREDENTIALS_PATH")
GA4_PROPERTY_ID = os.getenv("GA4_PROPERTY_ID")


def get_ga4_report(
    metrics: list[str],
    dimensions: list[str],
    date_from: str,
    date_to: str,
) -> dict:
    """
    Pobiera raport z Google Analytics 4.

    Args:
        metrics: Lista metryk, np. ["sessions", "activeUsers", "screenPageViews"]
        dimensions: Lista wymiarów, np. ["date", "country", "pagePath"]
        date_from: Data początkowa w formacie YYYY-MM-DD
        date_to: Data końcowa w formacie YYYY-MM-DD

    Returns:
        Słownik z wynikami raportu zawierający nagłówki i wiersze danych
    """
    # Obsługa credentials: z Streamlit Secrets (JSON string) lub z pliku
    ga4_credentials_json = os.getenv("GA4_CREDENTIALS_JSON")
    if ga4_credentials_json:
        import json as _json
        info = _json.loads(ga4_credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
    else:
        credentials = service_account.Credentials.from_service_account_file(
            GA4_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
    client = BetaAnalyticsDataClient(credentials=credentials)

    request = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        date_ranges=[DateRange(start_date=date_from, end_date=date_to)],
        dimensions=[Dimension(name=dim) for dim in dimensions],
        metrics=[Metric(name=met) for met in metrics],
    )

    response = client.run_report(request)

    dimension_headers = [dh.name for dh in response.dimension_headers]
    metric_headers = [mh.name for mh in response.metric_headers]

    rows = []
    for row in response.rows:
        row_data = {}
        for i, dim_value in enumerate(row.dimension_values):
            row_data[dimension_headers[i]] = dim_value.value
        for i, met_value in enumerate(row.metric_values):
            row_data[metric_headers[i]] = met_value.value
        rows.append(row_data)

    return {
        "dimension_headers": dimension_headers,
        "metric_headers": metric_headers,
        "rows": rows,
        "row_count": len(rows),
        "date_from": date_from,
        "date_to": date_to,
    }
