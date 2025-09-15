import os, mysql.connector
from dotenv import load_dotenv
load_dotenv()

cfg = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}

items = [
    {
        "product_id": "demo-1001",
        "title": "Wireless Earbuds Pro",
        "image_main": "https://picsum.photos/seed/earbuds/600/800",
        "video_url": None,
        "sale_price": 19.99, "sale_price_currency": "USD",
        "original_price": 29.99, "original_price_currency": "USD",
        "lastest_volume": 12000, "rating_weighted": 4.5,
        "category_id": "100001",
    },
    {
        "product_id": "demo-1002",
        "title": "Smart Watch – Fitness Tracker",
        "image_main": "https://picsum.photos/seed/watch/600/800",
        "video_url": None,
        "sale_price": 24.50, "sale_price_currency": "USD",
        "original_price": 39.00, "original_price_currency": "USD",
        "lastest_volume": 8500, "rating_weighted": 4.2,
        "category_id": "100002",
    },
    {
        "product_id": "demo-1003",
        "title": "Mini Tripod with Phone Holder",
        "image_main": "https://picsum.photos/seed/tripod/600/800",
        "video_url": "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
        "sale_price": 9.90, "sale_price_currency": "USD",
        "original_price": 14.90, "original_price_currency": "USD",
        "lastest_volume": 5600, "rating_weighted": 4.0,
        "category_id": "100003",
    },
]

cn = mysql.connector.connect(**cfg)
cur = cn.cursor()
for it in items:
    cur.execute(
        """
        INSERT INTO aliexpress_products (
            product_id, product_title, product_main_image_url, product_video_url,
            sale_price, sale_price_currency, original_price, original_price_currency,
            lastest_volume, rating_weighted, first_level_category_id, fetched_at, saved_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(), NOW())
        ON DUPLICATE KEY UPDATE
            product_title=VALUES(product_title),
            product_main_image_url=VALUES(product_main_image_url),
            product_video_url=VALUES(product_video_url),
            sale_price=VALUES(sale_price),
            sale_price_currency=VALUES(sale_price_currency),
            original_price=VALUES(original_price),
            original_price_currency=VALUES(original_price_currency),
            lastest_volume=VALUES(lastest_volume),
            rating_weighted=VALUES(rating_weighted),
            first_level_category_id=VALUES(first_level_category_id),
            saved_at=NOW()
        """,
        (
            it["product_id"], it["title"], it["image_main"], it["video_url"],
            it["sale_price"], it["sale_price_currency"], it["original_price"], it["original_price_currency"],
            it["lastest_volume"], it["rating_weighted"], it["category_id"]
        )
    )
cn.commit()
cur.close(); cn.close()
print("Seed done ✅")
