import pandas as pd
import re
from sqlalchemy import create_engine, text
from flask import Flask, request, jsonify, render_template
from datetime import datetime

app = Flask(__name__)

df = None
ALL_INGREDIENTS = []

# =============================
# Утилиты
# =============================

def clean_ingredients(text):
    """
    Парсит строку вида 'Свинина — 300 г | Лук — 2 шт'
    Возвращает строку нормализованных ингредиентов через пробел: 'свинина лук'
    """
    if not isinstance(text, str) or text.strip() == "":
        return ""

    items = text.split('|')
    ingredients = []

    for item in items:
        ing_name = re.split(r'\s+[—\-]\s+', item.strip())[0]
        ing_name = ing_name.strip().lower().replace(" ", "_")
        if ing_name:
            ingredients.append(ing_name)

    return " ".join(sorted(set(ingredients)))


def build_ingredients_list(df_source):
    """Собирает список всех уникальных ингредиентов из датафрейма."""
    all_ings_set = set()
    for ing_string in df_source['ingredients']:
        if not isinstance(ing_string, str):
            continue
        raw_ingredients = ing_string.split("|")
        for ing in raw_ingredients:
            clean_ing = re.split(r'[—–\-]', ing)[0]
            clean_ing = clean_ing.strip().lower().replace('.', '')
            if clean_ing and len(clean_ing) > 1:
                all_ings_set.add(clean_ing)
    return sorted(list(all_ings_set))


# =============================
# Логика рекомендаций
# =============================

def recommend_strict(df_source, user_products, top_n=5):
    user_set = set(p.lower().replace(" ", "_") for p in user_products)

    def is_subset(recipe_text):
        recipe_ings = set(recipe_text.split())
        return bool(recipe_ings) and recipe_ings.issubset(user_set)

    mask = df_source['ingredients'].apply(is_subset)
    res_df = df_source[mask].copy()

    if res_df.empty:
        return []

    res_df['ing_count'] = res_df['ingredients'].apply(lambda x: len(x.split()))
    res_df = res_df.sort_values('ing_count')

    return res_df.head(top_n)[['name', 'ingredients']].to_dict('records')


def recommend_with_extras(df_source, user_products, top_n=5):
    user_set = set(p.lower().replace(" ", "_") for p in user_products)

    def score_recipe(recipe_text):
        recipe_ings = recipe_text.split()
        if not recipe_ings:
            return -1, [], 0
        matched = sum(1 for ing in recipe_ings if ing in user_set)
        missing = [ing for ing in recipe_ings if ing not in user_set]
        score = (matched / len(recipe_ings)) - (len(missing) * 0.05)
        return score, missing, matched

    analysis = df_source['ingredients'].apply(score_recipe)
    temp_df = df_source.copy()
    temp_df['score'] = analysis.apply(lambda x: x[0])
    temp_df['missing'] = analysis.apply(lambda x: x[1])
    temp_df['found_count'] = analysis.apply(lambda x: x[2])

    # Исключаем рецепты, которые уже попали в strict (missing == [])
    filtered = temp_df[
        (temp_df['found_count'] > 0) &
        (temp_df['missing'].apply(len) > 0)
    ]
    filtered = filtered.sort_values('score', ascending=False)

    return filtered.head(top_n)[['name', 'ingredients', 'score', 'missing', 'found_count']].to_dict('records')


# =============================
# Инициализация данных
# =============================

def get_engine():
    DB_USER = 'postgres'
    DB_PASSWORD = 'JohnnyCage29'
    DB_HOST = '127.0.0.1'
    DB_PORT = '5432'
    DB_NAME = 'recipes'
    return create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")


def load_data():
    global df, ALL_INGREDIENTS
    try:
        print("Загрузка данных из БД...")
        engine = get_engine()
        df = pd.read_sql("SELECT name, ingredients FROM newtable", con=engine)
        print(f"Загружено {len(df)} рецептов из БД.")
    except Exception as e:
        print(f"Ошибка подключения к БД, пробуем CSV: {e}")
        try:
            df = pd.read_csv("recipes_main.csv", encoding='utf-8-sig', quotechar='"', skipinitialspace=True)
            print(f"Загружено {len(df)} рецептов из CSV.")
        except Exception as e2:
            print(f"Ошибка загрузки CSV: {e2}")
            df = pd.DataFrame(columns=['name', 'ingredients'])

    ALL_INGREDIENTS = build_ingredients_list(df)

    df['ingredients'] = df['ingredients'].fillna("").apply(clean_ingredients)
    df = df[df['ingredients'] != ""].reset_index(drop=True)

    print(f"Готово: {len(df)} рецептов, {len(ALL_INGREDIENTS)} уникальных ингредиентов.")


load_data()


# =============================
# Маршруты (Routes)
# =============================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/ingredients')
def get_ingredients():
    return jsonify(ALL_INGREDIENTS)


@app.route('/api/recommend', methods=['POST'])
def recommend():
    data = request.json
    user_fridge = data.get('products', [])

    if df is None or df.empty:
        return jsonify({"strict": [], "extras": []})

    strict_res = recommend_strict(df, user_fridge, top_n=5)
    extra_res = recommend_with_extras(df, user_fridge, top_n=5)

    return jsonify({
        "strict": strict_res,
        "extras": extra_res
    })


@app.route('/api/add_recipe', methods=['POST'])
def add_recipe():
    """
    Принимает новое блюдо от пользователя и сохраняет в БД и в df.
    Тело запроса (JSON):
        name        — строка, название блюда (обязательно)
        ingredients — список строк, например ["курица", "лук", "картофель"]
        description — строка, описание/рецепт (необязательно)
    """
    global df, ALL_INGREDIENTS

    data = request.json
    name = (data.get('name') or '').strip()
    ingredients_list = data.get('ingredients', [])
    description = (data.get('description') or '').strip()

    # Валидация
    if not name:
        return jsonify({"error": "Название блюда обязательно"}), 400

    ingredients_list = [i.strip() for i in ingredients_list if isinstance(i, str) and i.strip()]
    if not ingredients_list:
        return jsonify({"error": "Список ингредиентов не может быть пустым"}), 400

    # Нормализуем ингредиенты в формат БД: "Лук | Курица | Картофель"
    ingredients_pipe = " | ".join(ing.capitalize() for ing in ingredients_list)

    # Нормализуем в формат поиска: "картофель курица лук"
    normalized = " ".join(sorted(
        set(ing.lower().replace(" ", "_") for ing in ingredients_list)
    ))

    # Сохраняем в PostgreSQL
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO newtable (name, ingredients, instructions)
                    VALUES (:name, :ingredients, :instructions)
                """),
                {
                    "name": name,
                    "ingredients": ingredients_pipe,
                    "instructions": description
                }
            )
            conn.commit()
        print(f"Рецепт '{name}' сохранён в БД.")
    except Exception as e:
        print(f"Ошибка записи в БД: {e}")
        # Не прерываем — добавим в память и ответим успехом

    # Добавляем в оперативный датафрейм (без перезагрузки всего)
    new_row = pd.DataFrame([{
        'name': name,
        'ingredients': normalized
    }])
    df = pd.concat([df, new_row], ignore_index=True)

    # Обновляем список ингредиентов для автокомплита
    for ing in ingredients_list:
        clean = ing.strip().lower()
        if clean and clean not in ALL_INGREDIENTS:
            ALL_INGREDIENTS.append(clean)
    ALL_INGREDIENTS.sort()

    return jsonify({"status": "ok", "name": name, "ingredients": normalized})


if __name__ == '__main__':
    app.run(debug=True, port=5000)