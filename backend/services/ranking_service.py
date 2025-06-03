import logging
import numpy as np
import pandas as pd
from typing import List

logger = logging.getLogger(__name__)

def compute_critic_weights(df: pd.DataFrame, modes: List[str]) -> pd.Series:
    """
    Обчислення ваг CRITIC з урахуванням напрямків оптимізації ("max" або "min") для кожного критерію.

    :param df: Вхідний DataFrame із числовими характеристиками.
    :param modes: Список напрямків оптимізації для кожного стовпця ("max" або "min").
    :return: Серія з вагами критеріїв.
    """

    logger.info("compute_critic_weights: розмір датафрейму %s", df.shape)
    if len(modes) != df.shape[1]:
        raise ValueError("Кількість елементів у 'modes' має збігатися з кількістю стовпців у DataFrame.")

    norm = df.copy()
    for i, col in enumerate(df.columns):
        if modes[i] == 'max':
            norm[col] = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
        elif modes[i] == 'min':
            norm[col] = (df[col].max() - df[col]) / (df[col].max() - df[col].min())
        else:
            raise ValueError(f"Неприпустиме значення '{modes[i]}' у modes. Має бути 'max' або 'min'.")

    std = norm.std(ddof=0)
    corr = norm.corr()
    C = std * (1 - corr).sum(axis=1)
    weights = C / C.sum()
    return weights

def voronin_score(
    df: pd.DataFrame,
    weights: pd.Series,
    modes: List[str]
) -> np.ndarray:
    """
    Обчислення скорів Voronin для заданого набору даних.

    :param df: Вхідний DataFrame із числовими характеристиками.
               Кожен стовпець представляє критерій, а кожен рядок — альтернативу.
    :param weights: Серія ваг критеріїв, що сумуються до 1.0.
                    Індекси повинні відповідати назвам стовпців df.
    :param modes: Список напрямків оптимізації для кожного критерію.
                  Значення можуть бути "max" (більший кращий) або "min" (менший кращий).
                  Довжина списку повинна збігатися з кількістю стовпців df.
    :return: Масив скорів для кожної альтернативи. Чим більший скор, тим краща альтернатива.

    :raises ValueError: Якщо:
        - Сума ваг не дорівнює 1.0.
        - Довжина modes не збігається з кількістю стовпців df.
        - Значення в modes не є "max" або "min".
    """
    logger.info("voronin_score: початок обчислення скорів")
    logger.info("voronin_score: розмір датафрейму %s", df.shape)
    logger.info("voronin_score: ваги критеріїв %s", weights.values)
    logger.info("voronin_score: режими оптимізації %s", modes)

    if not np.isclose(weights.sum(), 1.0):
        logger.error("voronin_score: сума ваг не дорівнює 1")
        raise ValueError("Сума ваг має дорівнювати 1.")
    if len(modes) != df.shape[1]:
        logger.error("voronin_score: довжина modes не збігається з кількістю стовпців df")
        raise ValueError("Довжина modes повинна збігатися з кількістю стовпців df.")
    if not all(m in {"max", "min"} for m in modes):
        logger.error("voronin_score: некоректні елементи в modes")
        raise ValueError("Елементи modes можуть бути лише 'max' або 'min'.")

    # матриця нормалізованих відхилень y_ij ∈ [0, 1] (0 — ідеал, 1 — антиідеал)
    Y = np.zeros_like(df.values, dtype=float)

    for j, mode in enumerate(modes):
        col = df.iloc[:, j].astype(float).values
        col_min, col_max = col.min(), col.max()
        span = col_max - col_min
        if span == 0:  # усі значення однакові — критерій не дискримінує
            Y[:, j] = 0.0
            continue

        if mode == 'max':           # більший кращий → відхилення від max
            Y[:, j] = (col_max - col) / span
        else:                       # менший кращий → відхилення від min
            Y[:, j] = (col - col_min) / span

    logger.debug("voronin_score: матриця нормалізованих відхилень Y створена")
    # уникнути ділення на нуль, якщо y_ij = 1 → додаємо ε
    eps = 1e-12
    scores = np.sum(weights.values / (1.0 - Y + eps), axis=1)

    logger.info("voronin_score: обчислення скорів завершено")
    return scores
