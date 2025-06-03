import re
import statistics
import logging
import numpy as np
import requests

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def extract_text_in_last_parentheses(text):
    """
    Витягує текст в останніх дужках з рядка.

    :param text: Рядок, з якого потрібно витягти текст.
    :return: Текст в останніх дужках або None, якщо не знайдено.
    """
    start = text.rfind('(')
    end = text.rfind(')')
    if start != -1 and end != -1 and start < end:
        result = text[start + 1:end]
        logging.debug(f"Витягнуто текст у дужках: {result}")
        return result
    logging.debug("Вміст у дужках не знайдено.")
    return None


def hotline_request(url, payload, token=None, referer=None):
    """
    Надсилає POST-запит до API Hotline з необхідними заголовками.

    :param url: URL-адреса для запиту.
    :param payload: JSON-тіло запиту.
    :param token: Токен авторизації (необов'язковий).
    :param referer: Referer-рядок (необов'язковий).
    :return: JSON-відповідь сервера.
    :raises: HTTPError, якщо запит не вдалий.
    """
    headers = {
        "accept": "*/*",
        "accept-language": "uk,ru;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "x-language": "uk",
        "user-agent": "Mozilla/5.0",
    }
    if referer:
        headers["x-referer"] = f"https://hotline.ua{referer}"
    if token:
        headers["x-token"] = token

    logging.debug(f"Надсилання запиту до API Hotline: {url} з даними: {payload}")
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def smart_trend(values):
    """
    Обчислює трендову (типову) ціну з використанням гістограми та методу Фрідмана-Діакониса.

    :param values: Список числових значень (наприклад, ціни).
    :return: Усереднене значення в найгустішому інтервалі.
    """
    if len(values) <= 3:
        return statistics.mean(values)

    q75, q25 = np.percentile(values, [75, 25])
    iqr = q75 - q25
    n = len(values)
    bin_width = 2 * iqr * (n ** (-1 / 3))

    if bin_width == 0:
        return statistics.mean(values)

    min_value, max_value = min(values), max(values)
    bins = np.arange(min_value, max_value + bin_width, bin_width)
    counts, bin_edges = np.histogram(values, bins=bins)

    max_count_index = np.argmax(counts)
    trend_interval = (bin_edges[max_count_index], bin_edges[max_count_index + 1])

    clustered_values = [v for v in values if trend_interval[0] <= v < trend_interval[1]]
    result = statistics.mean(clustered_values) if clustered_values else statistics.mean(values)

    logging.debug(f"Розраховано трендову ціну: {result}")
    return result


def fetch_products(product_limit, search_query):
    """
    Завантажує продукти з Prozorro API з витягом ідентифікаторів.

    :param product_limit: Максимальна кількість продуктів.
    :param search_query: Текст пошуку.
    :return: Список продуктів з полями id, title, identifier.
    """
    base_url = "https://prozorro.gov.ua/api/search/products"
    products = []
    page = 1
    regex = re.compile(r"\((?=[^)]*[A-Z])(?=[^)]*\d)[A-Za-z0-9\-/]+\)")

    while len(products) < product_limit:
        params = {"text": search_query, "page": page}
        response = requests.post(base_url, params=params, headers={
            "accept": "application/json, text/plain, */*",
            "accept-language": "uk",
            "user-agent": "Mozilla/5.0"
        })

        if response.status_code != 200:
            logging.warning(f"Помилка запиту: {response.status_code}")
            break

        data = response.json()
        items = data.get("data", [])

        if not items:
            logging.info("Немає більше продуктів для завантаження.")
            break

        for item in items:
            title = item.get("title", "")
            match = regex.search(title)
            if match:
                identifier = extract_text_in_last_parentheses(title)
                products.append({
                    "id": item.get("id"),
                    "identifier": identifier,
                    "title": title.lower(),
                })
                if len(products) >= product_limit:
                    break
        page += 1

    logging.info(f"Завантажено {len(products)} продуктів.")
    return products


def enrich_product(product):
    """
    Розширює продукт характеристиками з Prozorro та ціною з Hotline.

    :param product: Словник з ключами id, identifier, title.
    :return: Розширений словник продукту з ціною та характеристиками або None.
    """
    url = f"https://market-api.prozorro.gov.ua/api/products/{product['id']}"
    response = requests.get(url, headers={
        "accept": "application/json, text/plain, */*",
        "accept-language": "uk",
        "user-agent": "Mozilla/5.0"
    })

    if response.status_code != 200:
        logging.warning(f"Помилка отримання даних продукту {product['id']}: {response.status_code}")
        return None

    data = response.json().get("data", {})
    characteristics = []

    for req in data.get("requirementResponses", []):
        if "unit" in req:
            characteristics.append({
                "requirement": req.get("requirement"),
                "value": req.get("value", req.get("values", [None])[0]),
                "unit": req["unit"].get("name")
            })

    price = fetch_hotline_price(product["identifier"])

    enriched = {
        "id": product["id"],
        "identifier": product["identifier"],
        "characteristics": characteristics,
        "price": price,
        "title": product["title"],
    }

    logging.info(f"Продукт {product['identifier']} збагачено.")
    return enriched


def fetch_hotline_price(identifier):
    """
    Отримує ціну продукту з Hotline за допомогою трьох етапів API-запитів.

    :param identifier: Ідентифікатор продукту.
    :return: Усереднена типова ціна або None, якщо не вдалося знайти.
    """
    base_url = "https://hotline.ua"
    api_url_search = f"{base_url}/svc/search/api/json-rpc"
    api_url_graphql = f"{base_url}/svc/frontend-api/graphql"

    # Пошук продукту
    search_payload = {
        "jsonrpc": "2.0",
        "method": "search.search",
        "params": {"q": identifier, "lang": "uk", "section_id": None, "entity": "full"},
        "id": 1
    }

    try:
        data = hotline_request(api_url_search, search_payload)
        url_path = data["result"][0]["url"]
        product_slug = url_path.strip('/').split('/')[-1]
    except (KeyError, IndexError, requests.RequestException):
        logging.warning(f"Не знайдено продукт на Hotline для {identifier}")
        return None

    # Отримання токена
    token_payload = {
        "operationName": "urlTypeDefiner",
        "variables": {"path": url_path},
        "query": """
        query urlTypeDefiner($path: String!) {
          urlTypeDefiner(path: $path) {
            token
          }
        }"""
    }

    try:
        data = hotline_request(api_url_graphql, token_payload)
        token = data["data"]["urlTypeDefiner"]["token"]
    except (KeyError, TypeError, requests.RequestException):
        logging.warning(f"Не вдалося отримати токен для {identifier}")
        return None

    # Отримання цін
    prices_payload = {
        "operationName": "getOffers",
        "variables": {"path": product_slug, "cityId": 187},
        "query": """
        query getOffers($path: String!, $cityId: Int!) {
          byPathQueryProduct(path: $path, cityId: $cityId) {
            offers(first: 1000) {
              edges {
                node {
                  price
                }
              }
            }
          }
        }"""
    }

    try:
        data = hotline_request(api_url_graphql, prices_payload, token=token, referer=url_path)
        edges = data["data"]["byPathQueryProduct"]["offers"]["edges"]
        prices = [edge["node"]["price"] for edge in edges if "price" in edge["node"]]
        if prices:
            trend = round(smart_trend(prices), 2)
            logging.info(f"Знайдено ціну для {identifier}: {trend}")
            return trend
    except (KeyError, TypeError, requests.RequestException):
        logging.warning(f"Не вдалося витягнути ціни для {identifier}")
    return None

