import requests
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ExchangeRateService:
    """
    Service for fetching real-time exchange rates from reliable online sources
    """
    
    def __init__(self):
        # Free API endpoints for exchange rates
        self.apis = [
            {
                'name': 'exchangerate-api',
                'url': 'https://api.exchangerate-api.com/v4/latest/USD',
                'free': True,
                'rate_limit': 1000,  # requests per month
            },
            {
                'name': 'fixer',
                'url': 'http://data.fixer.io/api/latest',
                'free': False,  # Requires API key
                'rate_limit': 100,  # requests per month for free tier
            },
            {
                'name': 'currencylayer',
                'url': 'http://api.currencylayer.com/live',
                'free': False,  # Requires API key
                'rate_limit': 1000,  # requests per month for free tier
            }
        ]
        
        # Cache for exchange rates
        self.cache = {}
        self.cache_duration = 3600  # 1 hour in seconds
        
    def get_exchange_rates(self, base_currency: str = 'USD') -> Dict[str, float]:
        """
        Get current exchange rates for supported currencies
        
        Args:
            base_currency: Base currency (default: USD)
            
        Returns:
            Dictionary with currency codes as keys and rates as values
        """
        # Check cache first
        cache_key = f"rates_{base_currency}_{int(time.time() // self.cache_duration)}"
        if cache_key in self.cache:
            logger.info(f"Using cached exchange rates for {base_currency}")
            return self.cache[cache_key]
        
        # Try to fetch from APIs
        for api in self.apis:
            try:
                if api['name'] == 'exchangerate-api':
                    rates = self._fetch_from_exchangerate_api(base_currency)
                elif api['name'] == 'fixer':
                    rates = self._fetch_from_fixer_api(base_currency)
                elif api['name'] == 'currencylayer':
                    rates = self._fetch_from_currencylayer_api(base_currency)
                else:
                    continue
                
                if rates:
                    # Cache the results
                    self.cache[cache_key] = rates
                    logger.info(f"Successfully fetched exchange rates from {api['name']}")
                    return rates
                    
            except Exception as e:
                logger.warning(f"Failed to fetch from {api['name']}: {e}")
                continue
        
        # Fallback to default rates if all APIs fail
        logger.warning("All exchange rate APIs failed, using default rates")
        return self._get_default_rates(base_currency)
    
    def _fetch_from_exchangerate_api(self, base_currency: str) -> Optional[Dict[str, float]]:
        """
        Fetch exchange rates from exchangerate-api.com (free)
        """
        try:
            url = f"https://api.exchangerate-api.com/v4/latest/{base_currency}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'rates' in data:
                # Filter for supported currencies
                supported_currencies = ['USD', 'EUR', 'ILS']
                rates = {}
                for currency in supported_currencies:
                    if currency in data['rates']:
                        rates[currency] = data['rates'][currency]
                
                return rates
                
        except Exception as e:
            logger.error(f"Error fetching from exchangerate-api: {e}")
            return None
    
    def _fetch_from_fixer_api(self, base_currency: str) -> Optional[Dict[str, float]]:
        """
        Fetch exchange rates from fixer.io (requires API key)
        """
        # This would require an API key, so we'll skip for now
        return None
    
    def _fetch_from_currencylayer_api(self, base_currency: str) -> Optional[Dict[str, float]]:
        """
        Fetch exchange rates from currencylayer.com (requires API key)
        """
        # This would require an API key, so we'll skip for now
        return None
    
    def _get_default_rates(self, base_currency: str) -> Dict[str, float]:
        """
        Get default exchange rates as fallback
        """
        # Default rates (approximate, should be updated regularly)
        default_rates = {
            'USD': {
                'USD': 1.0,
                'EUR': 0.85,  # Approximate
                'ILS': 3.7,   # Approximate
            },
            'EUR': {
                'USD': 1.18,  # Approximate
                'EUR': 1.0,
                'ILS': 4.35,  # Approximate
            },
            'ILS': {
                'USD': 0.27,  # Approximate
                'EUR': 0.23,  # Approximate
                'ILS': 1.0,
            }
        }
        
        return default_rates.get(base_currency, default_rates['USD'])
    
    def convert_currency(self, amount: float, from_currency: str, to_currency: str) -> float:
        """
        Convert amount from one currency to another
        
        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code
            
        Returns:
            Converted amount
        """
        if from_currency == to_currency:
            return amount
        
        rates = self.get_exchange_rates(from_currency)
        if to_currency in rates:
            return amount * rates[to_currency]
        
        # If direct conversion not available, try USD as intermediate
        if from_currency != 'USD' and to_currency != 'USD':
            usd_rates = self.get_exchange_rates('USD')
            if from_currency in usd_rates and to_currency in usd_rates:
                # Convert to USD first, then to target currency
                usd_amount = amount / usd_rates[from_currency]
                return usd_amount * usd_rates[to_currency]
        
        logger.warning(f"Could not convert {from_currency} to {to_currency}")
        return amount  # Return original amount if conversion fails
    
    def get_supported_currencies(self) -> list:
        """
        Get list of supported currencies
        """
        return ['USD', 'EUR', 'ILS']
    
    def is_rate_fresh(self, timestamp: float) -> bool:
        """
        Check if exchange rate is fresh (less than cache_duration old)
        """
        return time.time() - timestamp < self.cache_duration

# Global instance
exchange_rate_service = ExchangeRateService()
