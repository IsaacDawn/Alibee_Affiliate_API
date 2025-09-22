# backend/routes/exchange.py
from fastapi import APIRouter, Query
import requests

router = APIRouter()

@router.get("/exchange-rates")
def get_exchange_rates(base_currency: str = Query("USD", description="Base currency")):
    """Get exchange rates from external API"""
    try:
        # Use a free exchange rate API
        url = f"https://api.exchangerate-api.com/v4/latest/{base_currency}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return {
            "base": data.get("base", base_currency),
            "date": data.get("date"),
            "rates": data.get("rates", {})
        }
    except Exception as e:
        # Return fallback rates if API fails
        fallback_rates = {
            "USD": 1.0,
            "EUR": 0.85,
            "GBP": 0.73,
            "CNY": 7.2,
            "JPY": 110.0,
            "CAD": 1.25,
            "AUD": 1.35,
            "CHF": 0.92,
            "SEK": 8.5,
            "NOK": 8.8,
            "DKK": 6.3,
            "PLN": 3.9,
            "CZK": 21.5,
            "HUF": 300.0,
            "RUB": 75.0,
            "TRY": 8.5,
            "BRL": 5.2,
            "MXN": 20.0,
            "INR": 74.0,
            "KRW": 1180.0,
            "SGD": 1.35,
            "HKD": 7.8,
            "NZD": 1.4,
            "ZAR": 14.5,
            "ILS": 3.2,
            "AED": 3.67,
            "SAR": 3.75,
            "QAR": 3.64,
            "KWD": 0.30,
            "BHD": 0.38,
            "OMR": 0.38,
            "JOD": 0.71,
            "LBP": 1500.0,
            "EGP": 15.7,
            "MAD": 9.0,
            "TND": 2.8,
            "DZD": 135.0,
            "LYD": 4.5,
            "SDG": 55.0,
            "ETB": 44.0,
            "KES": 110.0,
            "UGX": 3500.0,
            "TZS": 2300.0,
            "MWK": 800.0,
            "ZMW": 18.0,
            "BWP": 11.0,
            "SZL": 14.5,
            "LSL": 14.5,
            "NAD": 14.5,
            "MZN": 63.0,
            "AOA": 650.0,
            "GMD": 52.0,
            "GHS": 6.0,
            "NGN": 410.0,
            "XOF": 550.0,
            "XAF": 550.0,
            "CDF": 2000.0,
            "RWF": 1000.0,
            "BIF": 2000.0,
            "DJF": 180.0,
            "SOS": 580.0,
            "ERN": 15.0,
            "SSP": 130.0,
            "CVE": 100.0,
            "STN": 22.0,
            "GNF": 10000.0,
            "LRD": 170.0,
            "SLE": 22.0
        }
        
        return {
            "base": base_currency,
            "date": "2024-01-01",
            "rates": fallback_rates,
            "error": str(e),
            "fallback": True
        }
