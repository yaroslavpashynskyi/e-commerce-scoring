import logging
from flask import Blueprint, request, jsonify
import pandas as pd
from backend.services.ranking_service import compute_critic_weights, voronin_score

logger = logging.getLogger(__name__)
rank_bp = Blueprint('ranking', __name__)

@rank_bp.route('/rank', methods=['POST'])
def rank():
    """
    Ендпоінт для багатокритеріального ранжування.

    Параметри:
      Немає (очікується JSON-тіло запиту).

    Повертає:
      Response: JSON-відповідь із відсортованим списком товарів.
    """
    data = request.get_json()
    if not isinstance(data, list) or not data:
        logger.warning("Невалідний формат даних для ранжування: %r", data)
        return jsonify({'error': 'Невалідний формат введення'}), 400

    df = pd.DataFrame([
        {ch['parameter']: ch['value'] for ch in item['selected_characteristics']}
        for item in data
    ])
    modes = [ch['mode'] for ch in data[0]['selected_characteristics']]

    weights = compute_critic_weights(df, modes)
    scores = voronin_score(df, weights, modes)

    results = sorted([
        {'title': item['title'], 'id': item['id'], 'score': float(s)}
        for item, s in zip(data, scores)
    ], key=lambda x: x['score'], reverse=True)

    logger.info("Ранжування успішно виконано для %d елементів", len(results))
    return jsonify(results), 200

