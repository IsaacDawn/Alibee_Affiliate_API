import time, hmac, hashlib
import requests
from urllib.parse import urlencode

class AliClient:
    def __init__(self, app_key: str, app_secret: str, tracking_id: str, base: str = "https://api-sg.aliexpress.com/sync"):
        self.app_key = app_key
        self.app_secret = app_secret.encode("utf-8")
        self.tracking_id = tracking_id
        self.base = base

    def _timestamp_ms(self) -> str:
        return str(int(time.time() * 1000))

    def _sign_sha256(self, params: dict) -> str:
        """
        AliExpress sync (OpenService) امضای HMAC-SHA256 می‌خواهد.
        رشتهٔ امضا = querystring مرتب‌شده (key=value با &)، بدون url-encodeِ دوباره.
        """
        # مرتب‌سازی بر اساس نام پارامتر
        items = sorted((k, v) for k, v in params.items() if v is not None)
        plain = "&".join(f"{k}={v}" for k, v in items).encode("utf-8")
        return hmac.new(self.app_secret, plain, hashlib.sha256).hexdigest().upper()

    def call(self, method: str, **service_params):
        """
        فراخوانی عمومی: method را مثل 'aliexpress.affiliate.product.query' بده،
        بقیه پارامترها (keywords, page_no, ...) را به صورت kwargs.
        """
        base_params = {
            "method": method,
            "app_key": self.app_key,
            "sign_method": "sha256",
            "timestamp": self._timestamp_ms(),
            "tracking_id": self.tracking_id,
            # اگر سند الزام کند: target_language/target_currency/… را می‌توان اینجا پیش‌فرض گذاشت
        }
        all_params = {**base_params, **{k: v for k, v in service_params.items() if v is not None}}

        # ساخت امضا
        sign = self._sign_sha256(all_params)
        all_params["sign"] = sign

        # درخواست
        r = requests.get(self.base, params=all_params, timeout=30)
        r.raise_for_status()
        return r.json()
