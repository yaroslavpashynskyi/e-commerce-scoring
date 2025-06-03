import streamlit as st
import pandas as pd
import requests
import uuid

def highlight_score(val):
    """
    Забарвлює клітинку в залежності від значення val [1,5]:
    1 - зелений (#22c55e), 5 - червоний (#dc2626)
    """
    # Нормалізуємо val до діапазону [0,1], де 1 => 0 (зелений), 5 => 1 (червоний)
    norm_val = (val - 1) / (5 - 1)
    norm_val = min(max(norm_val, 0), 1)  # Безпечна нормалізація

    # Градієнт: Зелений (#22c55e) -> Червоний (#dc2626)
    r = int(34 + (220 - 34) * norm_val)
    g = int(197 + (38 - 197) * norm_val)
    b = int(94 + (38 - 94) * norm_val)

    return f'background-color: rgb({r}, {g}, {b}); color: white'

st.set_page_config(page_title="Product Ranking App", layout="wide")
st.title("🔍 Онлайн-сервіс із підтримки оптимального вибору комерційних пропозицій.")

# Ініціалізація стану
if 'products_df' not in st.session_state:
    st.session_state.products_df = None
if 'custom_products' not in st.session_state:
    st.session_state.custom_products = []

# Запит товарів
query = st.text_input("Пошуковий запит", value="powerbank")
limit = st.number_input("Кількість товарів", min_value=1, max_value=100, value=10)

if st.button("📦 Отримати товари"):
    try:
        url = f"http://localhost:8000/products?query={query}&limit={limit}"
        response = requests.get(url)
        response.raise_for_status()
        items = response.json()["items"]
        rows = []
        for item in items:
            row = {"Назва": item["title"], "Ціна": item["price"], "id": item["id"]}
            for ch in item["characteristics"]:
                row[ch["requirement"]] = ch["value"]
            rows.append(row)
        st.session_state.products_df = pd.DataFrame(rows)
    except Exception as e:
        st.error(f"❌ Помилка: {e}")



# Якщо товари вже є
if st.session_state.products_df is not None:
    # Додавання власного товару
    st.subheader("➕ Додати свій товар")
    with st.expander("Натисніть, щоб додати вручну"):
        col1, col2 = st.columns(2)
        with col1:
            new_title = st.text_input("Назва товару")
            new_price = st.number_input("Ціна", min_value=0.0, step=1.0)
        with col2:
            raw_characteristics = st.text_area(
                "Характеристики (назва=значення по рядках)",
                help="Наприклад:\nЄмність=20000\nПотужність=25"
            )
        if st.button("➕ Додати товар"):
            try:
                new_item = {
                    "Назва": new_title,
                    "Ціна": new_price,
                    "id": str(uuid.uuid4())[:8]
                }
                for line in raw_characteristics.strip().splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        new_item[k.strip()] = float(v.strip())
                st.session_state.custom_products.append(new_item)
                st.success("✅ Товар додано!")
            except Exception as e:
                st.error(f"❌ Помилка в характеристиках: {e}")

    df_main = st.session_state.products_df.copy()
    df_all = pd.concat([df_main, pd.DataFrame(st.session_state.custom_products)], ignore_index=True)

    st.subheader("📋 Усі товари")
    st.dataframe(df_all.drop(columns=["id"]), use_container_width=True)

    # Вибір параметрів
    st.subheader("⚙️ Вибір індикаторів та екстримальні вимоги до них")
    selected_criteria = {}
    filter_mask = pd.Series([True] * len(df_all))

    for col in df_all.columns:
        if col not in ["Назва", "id"]:
            col1, col2, col3 = st.columns([2, 1.5, 3])
            with col1:
                use = st.checkbox(f"{col}", key=f"use_{col}")
            if use:
                with col2:
                    mode = st.radio("Оптимізація", ["min", "max"], key=f"mode_{col}", horizontal=True)
                with col3:
                    try:
                        min_val = float(df_all[col].min())
                        max_val = float(df_all[col].max())
                        slider = st.slider(f"Екстримальні значення для {col}", min_val, max_val, (min_val, max_val), key=f"slider_{col}")
                        filter_mask &= (df_all[col] >= slider[0]) & (df_all[col] <= slider[1])
                        selected_criteria[col] = mode
                    except:
                        st.warning(f"⚠️ Неможливо побудувати фільтр для {col} (нечислове значення?)")

    # Submit
    if st.button("📤 Обрати оптимальні товари"):
        filtered_df = df_all[filter_mask].copy()
        payload = []

        for _, row in filtered_df.iterrows():
            obj = {
                "id": row["id"],
                "title": row["Назва"],
                "selected_characteristics": []
            }
            for param, mode in selected_criteria.items():
                if param in row and pd.notna(row[param]):
                    obj["selected_characteristics"].append({
                        "parameter": param,
                        "value": row[param],
                        "mode": mode
                    })
            payload.append(obj)

        st.success("Дані підготовлено. Надсилаємо на оцінку...")

        try:
            res = requests.post("http://localhost:8000/rank", json=payload)
            res.raise_for_status()
            ranking = res.json()
        except Exception as e:
            st.error(f"❌ Помилка при ранжуванні: {e}")
            ranking = []

        if ranking:
            st.header("🏆 Оцінка товарів")
            st.subheader("Стовпець \"Оцінка\" - чим нижче, тим краще. 1 - ідеальний варіант.")

            scores_df = pd.DataFrame(ranking).sort_values(by="score", ascending=True)
            merged_df = scores_df.merge(df_all, on="id", how="left")
            merged_df["🔗 Prozorro"] = merged_df["id"].apply(
                lambda x: f"https://prozorro.gov.ua/uk/product/{x}"
            )

            cols = ["score", "Назва", "🔗 Prozorro"] + [
                c for c in merged_df.columns if c not in ["id", "title", "Назва", "score", "🔗 Prozorro"]
            ]

            styled = merged_df[cols].style.map(highlight_score, subset=["score"])

            st.dataframe(
                styled,
                use_container_width=True,
                column_config={
                    "🔗 Prozorro": st.column_config.LinkColumn(display_text="Відкрити"),
                    "score": st.column_config.Column(label="Оцінка"),
                }
            )
