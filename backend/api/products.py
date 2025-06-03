import logging
from flask import Blueprint, request, jsonify, abort
from backend.services.product_service import get_cached_suitable, fetch_and_cache

logger = logging.getLogger(__name__)
products_bp = Blueprint('products', __name__)

@products_bp.route('/products', methods=['GET'])
def get_products():
    """
    Повертає список «підходящих» товарів за пошуковим запитом.

    Параметри:
      - query (str): Текст пошуку.
      - limit (int): Максимальна кількість результатів.

    Повертає:
      Response: JSON-відповідь із кількістю та списком товарів.
    """
    query = request.args.get('query', '').lower().strip()
    limit = request.args.get('limit', type=int, default=10)
    if not query or limit < 1:
        logger.warning("Невалідні параметри запиту: query=%r, limit=%r", query, limit)
        abort(400, "Невалідний запит або ліміт")

    products = get_cached_suitable(query, limit)
    if len(products) < limit:
        fetch_and_cache(query, limit)
        products = get_cached_suitable(query, limit)

    items = [p.to_dict() for p in products]
    logger.info("Повернуто %d товарів за запитом '%s'", len(items), query)
    return jsonify({'count': len(items), 'items': items}), 200
