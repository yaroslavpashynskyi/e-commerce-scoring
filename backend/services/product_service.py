import json
import time
import random
import logging
from typing import List
from backend.data.models import Product
from backend.utils.product_enricher import fetch_products, enrich_product

logger = logging.getLogger(__name__)

MAX_FETCH_ATTEMPTS = 5
COMMON_THRESHOLD = 0.8

def get_cached_suitable(query: str, limit: int) -> List[Product]:
    """Повертає закешовані «підходящі» товари за запитом."""
    logger.debug("get_cached_suitable(query=%r, limit=%d)", query, limit)
    return (Product
            .select()
            .where(Product.suitable & Product.title.contains(query))
            .order_by(Product.created_at.desc())
            .limit(limit))

def update_suitability(products: List[Product]) -> None:
    """
    Оновлює поле suitable на основі загальних характеристик і наявності ціни.
    — збирає частоту ключів,
    — визначає «must-have» ключі,
    — для кожного продукту ставить флаг.
    """
    if not products:
        logger.debug("Немає продуктів для оновлення відповідності.")
        return

    key_freq = {}
    for p in products:
        for ch in json.loads(p.characteristics):
            key_freq[ch['requirement']] = key_freq.get(ch['requirement'], 0) + 1

    total = len(products)
    required = {k for k, cnt in key_freq.items() if cnt / total >= COMMON_THRESHOLD}
    logger.info("Обов'язкові характеристики: %s", required)

    for p in products:
        keys = {ch['requirement'] for ch in json.loads(p.characteristics)}
        is_ok = (p.price is not None) and required.issubset(keys)
        if p.suitable != is_ok:
            p.suitable = is_ok
            p.save()
            logger.info("Продукт %s відповідність встановлено в %s", p.id, is_ok)

def fetch_and_cache(query: str, needed: int) -> None:
    """
    Підтягує товари з API поки не набере потрібну кількість «підходящих» або не вичерпає спроби.
    """
    attempts = 0
    limit = needed
    while attempts < MAX_FETCH_ATTEMPTS:
        logger.info("Спроба завантаження %d для %r (потрібно=%d, ліміт=%d)",
                    attempts + 1, query, needed, limit)
        batch = fetch_products(limit, query)
        if not batch:
            logger.warning("Жодного елемента не завантажено на спробі %d", attempts + 1)
            break

        for raw in batch:
            if Product.select().where(Product.id == raw['id']).exists():
                continue
            enriched = enrich_product(raw)
            time.sleep(random.uniform(0.4, 0.8))
            if enriched:
                Product.create(
                    id=enriched['id'],
                    identifier=enriched['identifier'],
                    title=enriched['title'],
                    price=enriched['price'],
                    characteristics=json.dumps(enriched['characteristics']),
                    suitable=True
                )
                logger.debug("Збережено продукт %s", enriched['id'])

        # Перерахунок suitability для всіх
        products_all = list(Product.select().where(Product.title.contains(query)))
        update_suitability(products_all)

        suitable_now = get_cached_suitable(query, needed)
        logger.info("Підходящих %d/%d", len(suitable_now), needed)
        if len(suitable_now) >= needed:
            break

        limit = needed - len(suitable_now) + len(products_all)
        attempts += 1

