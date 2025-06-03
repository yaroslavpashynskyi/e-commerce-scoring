import pytest
import pandas as pd
import numpy as np
from backend.services.ranking_service import compute_critic_weights, voronin_score

def test_compute_critic_weights_basic():
    df = pd.DataFrame({
        'Критерій 1': [1, 2, 3],
        'Критерій 2': [10, 50, 100],
    })
    modes = ['max', 'max']
    weights = compute_critic_weights(df, modes)
    assert isinstance(weights, pd.Series), "Результат має бути pd.Series"
    assert np.isclose(weights.sum(), 1.0), "Сума ваг має дорівнювати 1"

def test_compute_critic_weights_expected_result():
    df = pd.DataFrame({
        'Критерій 1': [1, 2, 3],  # Невелика варіація
        'Критерій 2': [10, 50, 100],  # Велика варіація
    })
    modes = ['max', 'max']
    weights = compute_critic_weights(df, modes)
    assert weights['Критерій 2'] > weights['Критерій 1'], "Критерій 2 має більшу вагу через більшу варіацію"

def test_voronin_score_basic():
    df = pd.DataFrame({
        'Ціна': [100, 200, 300],
        'Ємність': [1000, 2000, 3000],
        'Потужність': [5, 10, 15],
    })
    weights = pd.Series([0.2, 0.3, 0.5], index=df.columns)
    modes = ['min', 'max', 'max']
    scores = voronin_score(df, weights, modes)
    assert isinstance(scores, np.ndarray)
    assert len(scores) == df.shape[0]
    assert np.all(scores >= 0), "Скор повинен бути невід'ємним"

def test_voronin_score_weight_sum_error():
    df = pd.DataFrame({
        'Ціна': [100, 200],
        'Ємність': [1000, 1500]
    })
    weights = pd.Series([0.7, 0.2], index=df.columns)  # сума не 1.0
    modes = ['min', 'max']
    with pytest.raises(ValueError, match="Сума ваг має дорівнювати 1."):
        voronin_score(df, weights, modes)

def test_voronin_score_mode_mismatch_error():
    df = pd.DataFrame({
        'Ціна': [100, 200],
        'Ємність': [1000, 1500]
    })
    weights = pd.Series([0.5, 0.5], index=df.columns)
    modes = ['min']  # лише один режим
    with pytest.raises(ValueError, match="Довжина modes повинна збігатися з кількістю стовпців df."):
        voronin_score(df, weights, modes)

def test_voronin_score_identical_rows():
    df = pd.DataFrame({
        'Ціна': [200, 200],
        'Ємність': [1500, 1500]
    })
    weights = pd.Series([0.5, 0.5], index=df.columns)
    modes = ['min', 'max']
    scores = voronin_score(df, weights, modes)
    assert np.allclose(scores, scores[0]), "Скор має бути однаковим для однакових рядків"

def test_voronin_score_dominant_product():
    # Створюємо 10 товарів
    data = {
        'Ціна':        [500, 600, 700, 550, 650, 620, 580, 560, 590, 400],  # min — краще
        'Ємність':     [10000, 9500, 9700, 9600, 9800, 9300, 9200, 9100, 9400, 15000],  # max — краще
        'Потужність':  [15, 13, 14, 12, 13, 11, 10, 13, 12, 25]  # max — краще
    }
    df = pd.DataFrame(data)

    # Товар №9 (індекс 9) домінує по всіх характеристиках:
    # найнижча ціна, найбільша ємність, найбільша потужність

    # Налаштовуємо режими
    modes = ['min', 'max', 'max']

    # Обчислюємо ваги та скор
    weights = compute_critic_weights(df, modes)
    scores = voronin_score(df, weights, modes)

    # Знаходимо індекс з найнищим скором (чим менше — тим краще)
    best_index = np.argmin(scores)

    # Перевіряємо що це саме товар №9
    assert best_index == 9, f"Очікується, що найкращий товар має індекс 9, але отримано {best_index}"