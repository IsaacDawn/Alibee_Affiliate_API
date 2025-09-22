"""
Currency Service using CurrencyFreaks API
"""

import requests
import asyncio
import time
import json
import os
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CurrencyService:
    """Service for managing currency exchange rates using CurrencyFreaks API"""
    
    def __init__(self):
        self.api_key = "c7063a6ee3e44e18a5d05425654ec4cb"
        self.base_url = "https://api.currencyfreaks.com/latest"
        # AliExpress supported currencies (comprehensive list)
        self.supported_currencies = [
            "USD",  # United States Dollar
            "CNY",  # Chinese Yuan
            "EUR",  # Euro
            "GBP",  # British Pound
            "JPY",  # Japanese Yen
            "INR",  # Indian Rupee
            "AUD",  # Australian Dollar
            "CAD",  # Canadian Dollar
            "BRL",  # Brazilian Real
            "RUB",  # Russian Ruble
            "KRW",  # South Korean Won
            "SGD",  # Singapore Dollar
            "HKD",  # Hong Kong Dollar
            "TWD",  # Taiwan Dollar
            "THB",  # Thai Baht
            "MYR",  # Malaysian Ringgit
            "IDR",  # Indonesian Rupiah
            "PHP",  # Philippine Peso
            "VND",  # Vietnamese Dong
            "TRY",  # Turkish Lira
            "PLN",  # Polish Zloty
            "CZK",  # Czech Koruna
            "HUF",  # Hungarian Forint
            "RON",  # Romanian Leu
            "BGN",  # Bulgarian Lev
            "HRK",  # Croatian Kuna
            "SEK",  # Swedish Krona
            "NOK",  # Norwegian Krone
            "DKK",  # Danish Krone
            "CHF",  # Swiss Franc
            "ILS",  # Israeli Shekel
            "AED",  # UAE Dirham
            "SAR",  # Saudi Riyal
            "EGP",  # Egyptian Pound
            "ZAR",  # South African Rand
            "MXN",  # Mexican Peso
            "ARS",  # Argentine Peso
            "CLP",  # Chilean Peso
            "COP",  # Colombian Peso
            "PEN",  # Peruvian Sol
            "UYU",  # Uruguayan Peso
            "NZD",  # New Zealand Dollar
        ]
        
        # Cache for exchange rates
        self.rates_cache: Dict[str, float] = {}
        self.last_update: Optional[datetime] = None
        self.update_interval = 28800  # 8 hours in seconds
        self.rate_multiplier = 0.963  # Multiplier applied to all exchange rates
        self.cache_file = "currency_rates_cache.json"  # File to store rates
        
        # Fallback rates (updated with AliExpress compatible rates)
        self.fallback_rates = {
            "USD": 1.0,    # United States Dollar
            "CNY": 7.11,   # Chinese Yuan (AliExpress rate)
            "EUR": 0.85,   # Euro
            "GBP": 0.73,   # British Pound
            "JPY": 110.0,  # Japanese Yen
            "INR": 83.0,   # Indian Rupee
            "AUD": 1.50,   # Australian Dollar
            "CAD": 1.35,   # Canadian Dollar
            "BRL": 5.20,   # Brazilian Real
            "RUB": 95.0,   # Russian Ruble
            "KRW": 1350.0, # South Korean Won
            "SGD": 1.35,   # Singapore Dollar
            "HKD": 7.80,   # Hong Kong Dollar
            "TWD": 32.0,   # Taiwan Dollar
            "THB": 36.0,   # Thai Baht
            "MYR": 4.70,   # Malaysian Ringgit
            "IDR": 15500.0,# Indonesian Rupiah
            "PHP": 56.0,   # Philippine Peso
            "VND": 24500.0,# Vietnamese Dong
            "TRY": 30.0,   # Turkish Lira
            "PLN": 4.0,    # Polish Zloty
            "CZK": 23.0,   # Czech Koruna
            "HUF": 360.0,  # Hungarian Forint
            "RON": 4.6,    # Romanian Leu
            "BGN": 1.66,   # Bulgarian Lev
            "HRK": 6.8,    # Croatian Kuna
            "SEK": 10.8,   # Swedish Krona
            "NOK": 10.5,   # Norwegian Krone
            "DKK": 6.3,    # Danish Krone
            "CHF": 0.88,   # Swiss Franc
            "ILS": 3.7,    # Israeli Shekel
            "AED": 3.67,   # UAE Dirham
            "SAR": 3.75,   # Saudi Riyal
            "EGP": 30.9,   # Egyptian Pound
            "ZAR": 18.5,   # South African Rand
            "MXN": 17.0,   # Mexican Peso
            "ARS": 850.0,  # Argentine Peso
            "CLP": 900.0,  # Chilean Peso
            "COP": 4100.0, # Colombian Peso
            "PEN": 3.7,    # Peruvian Sol
            "UYU": 39.0,   # Uruguayan Peso
            "NZD": 1.62,   # New Zealand Dollar
        }
    
    async def get_exchange_rates(self, base_currency: str = "USD") -> Dict[str, float]:
        """Get exchange rates for all supported currencies"""
        
        # Try to load from file first
        if not self.rates_cache:
            self._load_rates_from_file()
        
        # Check if cache is valid
        if self._is_cache_valid():
            logger.info(f"✅ Using cached rates (last update: {self.last_update})")
            return self._calculate_relative_rates(base_currency)
        
        # Update rates from API
        await self._update_rates_from_api()
        
        # Return calculated rates
        return self._calculate_relative_rates(base_currency)
    
    def _is_cache_valid(self) -> bool:
        """Check if cached rates are still valid"""
        if not self.last_update or not self.rates_cache:
            logger.info("🕐 No previous update found or empty cache, cache is invalid")
            return False
        
        time_since_update = datetime.now() - self.last_update
        hours_since_update = time_since_update.total_seconds() / 3600
        is_valid = time_since_update.total_seconds() < self.update_interval
        
        logger.info(f"🕐 Cache status: Last update was {hours_since_update:.1f} hours ago, valid for {self.update_interval/3600:.1f} hours")
        logger.info(f"🕐 Cache is {'✅ VALID' if is_valid else '❌ EXPIRED'}")
        
        return is_valid
    
    async def _update_rates_from_api(self):
        """Update exchange rates from CurrencyFreaks API"""
        try:
            logger.info("🔄 Updating exchange rates from CurrencyFreaks API...")
            
            # Prepare symbols string
            symbols = ",".join(self.supported_currencies)
            
            # Make API request
            url = f"{self.base_url}?apikey={self.api_key}&symbols={symbols}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"📊 CurrencyFreaks API Response: {data}")
            
            # Extract rates
            if 'rates' in data:
                self.rates_cache = data['rates']
                self.last_update = datetime.now()
                
                # Convert string values to float and apply 0.963 multiplier (except USD, EUR, GBP, ILS)
                for currency, rate_str in self.rates_cache.items():
                    try:
                        rate = float(rate_str)
                        # Apply rate multiplier to all rates except USD, EUR, GBP, ILS
                        if currency in ["USD", "EUR", "GBP", "ILS"]:
                            self.rates_cache[currency] = rate  # Keep USD, EUR, GBP, ILS as is
                        else:
                            self.rates_cache[currency] = rate * self.rate_multiplier
                    except (ValueError, TypeError):
                        logger.warning(f"⚠️ Invalid rate for {currency}: {rate_str}")
                        # Use fallback rate with 0.963 multiplier (except USD, EUR, GBP, ILS)
                        fallback_rate = self.fallback_rates.get(currency, 1.0)
                        if currency in ["USD", "EUR", "GBP", "ILS"]:
                            self.rates_cache[currency] = fallback_rate  # Keep USD, EUR, GBP, ILS as is
                        else:
                            self.rates_cache[currency] = fallback_rate * self.rate_multiplier
                
                logger.info(f"✅ Successfully updated {len(self.rates_cache)} exchange rates")
                logger.info(f"🕐 Update timestamp: {self.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"📈 Updated rates: {self.rates_cache}")
                
                # Save to file
                self._save_rates_to_file()
                
            else:
                logger.error("❌ No 'rates' field in API response")
                self._use_fallback_rates()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error fetching rates from CurrencyFreaks API: {e}")
            self._use_fallback_rates()
        except Exception as e:
            logger.error(f"❌ Unexpected error updating rates: {e}")
            self._use_fallback_rates()
    
    def _use_fallback_rates(self):
        """Use fallback rates when API fails"""
        logger.warning("⚠️ Using fallback exchange rates with 0.963 multiplier (except USD, EUR, GBP, ILS)")
        logger.info(f"🕐 Fallback timestamp: {self.last_update.strftime('%Y-%m-%d %H:%M:%S')}")
        # Apply rate multiplier to fallback rates (except USD, EUR, GBP, ILS)
        self.rates_cache = {}
        for currency, rate in self.fallback_rates.items():
            if currency in ["USD", "EUR", "GBP", "ILS"]:
                self.rates_cache[currency] = rate  # Keep USD, EUR, GBP, ILS as is
            else:
                self.rates_cache[currency] = rate * self.rate_multiplier
        self.last_update = datetime.now()
        
        # Save to file
        self._save_rates_to_file()
    
    def _calculate_relative_rates(self, base_currency: str) -> Dict[str, float]:
        """Calculate rates relative to base currency"""
        if not self.rates_cache:
            logger.warning("⚠️ No rates available, using fallback")
            self._use_fallback_rates()
        
        # Get base currency rate
        base_rate = self.rates_cache.get(base_currency, 1.0)
        
        # Calculate relative rates
        relative_rates = {}
        for currency, rate in self.rates_cache.items():
            if currency != base_currency:
                relative_rates[currency] = rate / base_rate
        
        logger.info(f"💱 Calculated relative rates for {base_currency}: {relative_rates}")
        return relative_rates
    
    def get_rate(self, from_currency: str, to_currency: str) -> float:
        """Get exchange rate between two currencies"""
        if from_currency == to_currency:
            return 1.0
        
        if not self.rates_cache:
            self._use_fallback_rates()
        
        from_rate = self.rates_cache.get(from_currency, 1.0)
        to_rate = self.rates_cache.get(to_currency, 1.0)
        
        return to_rate / from_rate
    
    def convert_amount(self, amount: float, from_currency: str, to_currency: str) -> float:
        """Convert amount from one currency to another"""
        if from_currency == to_currency:
            return amount
        
        rate = self.get_rate(from_currency, to_currency)
        return amount * rate
    
    def _save_rates_to_file(self):
        """Save current rates to JSON file"""
        try:
            cache_data = {
                "rates": self.rates_cache,
                "last_update": self.last_update.isoformat() if self.last_update else None,
                "rate_multiplier": self.rate_multiplier,
                "supported_currencies": self.supported_currencies,
                "update_interval": self.update_interval
            }
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Saved {len(self.rates_cache)} exchange rates to {self.cache_file}")
            
        except Exception as e:
            logger.error(f"❌ Error saving rates to file: {e}")
    
    def _load_rates_from_file(self) -> bool:
        """Load rates from JSON file"""
        try:
            if not os.path.exists(self.cache_file):
                logger.info(f"📁 Cache file {self.cache_file} not found")
                return False
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            self.rates_cache = cache_data.get("rates", {})
            last_update_str = cache_data.get("last_update")
            
            if last_update_str:
                self.last_update = datetime.fromisoformat(last_update_str)
            
            logger.info(f"📂 Loaded {len(self.rates_cache)} exchange rates from {self.cache_file}")
            logger.info(f"📅 Last update: {self.last_update}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error loading rates from file: {e}")
            return False
    
    def get_cache_info(self) -> Dict:
        """Get information about current cache"""
        return {
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "cache_valid": self._is_cache_valid(),
            "rates_count": len(self.rates_cache),
            "supported_currencies": self.supported_currencies,
            "update_interval_hours": self.update_interval / 3600,
            "last_update_formatted": self.last_update.strftime('%Y-%m-%d %H:%M:%S') if self.last_update else None,
            "next_update_in_hours": (self.update_interval - (datetime.now() - self.last_update).total_seconds()) / 3600 if self.last_update else None,
            "rate_multiplier": self.rate_multiplier,
            "cache_file": self.cache_file,
            "file_exists": os.path.exists(self.cache_file)
        }

# Global instance
currency_service = CurrencyService()
