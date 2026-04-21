import pandas as pd
import ast
import difflib
import re
from sqlalchemy import create_engine
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

df = None
ALL_INGREDIENTS = []


def clean_ingredients(text):
    """
    Парсит строку вида 'Свинина — 300 г | Лук — 2 шт'
    """
    if not isinstance(text, str) or text.strip() == "":
        return ""

    items = text.split('|')
    ingredients = []

    for item in items:
        ing_name = re.split(r'\s+[—\-]\s+', item.strip())[0]
        ing_name = re.sub(r'\(.*?\)', '', ing_name).strip().lower()
        ing_name = ing_name.replace(" ", "_")

        if ing_name:
            ingredients.append(ing_name)

    return " ".join(sorted(set(ingredients)))

# =============================
# Логика рекомендаций
# =============================

def recommend_strict(df, user_products, top_n=5):
    user_set = set([p.lower().replace(" ", "_") for p in user_products])

    def is_subset(recipe_text):
        recipe_ings = set(recipe_text.split())
        if not recipe_ings:
            return False
        return recipe_ings.issubset(user_set)

    mask = df['ingredients'].apply(is_subset)
    res_df = df[mask].copy()

    if res_df.empty:
        return []

    res_df['ing_count'] = res_df['ingredients'].apply(lambda x: len(x.split()))
    res_df = res_df.sort_values('ing_count')

    return res_df.head(top_n)[['name', 'ingredients']].to_dict('records')


def recommend_with_extras(df, user_products, top_n=5):
    user_set = set([p.lower().replace(" ", "_") for p in user_products])

    def score_recipe(recipe_text):
        recipe_ings = recipe_text.split()
        if not recipe_ings:
            return -1, [], 0
        matched = sum(1 for ing in recipe_ings if ing in user_set)
        missing = [ing for ing in recipe_ings if ing not in user_set]
        score = (matched / len(recipe_ings)) - (len(missing) * 0.05)
        return score, missing, matched

    analysis = df['ingredients'].apply(score_recipe)
    temp_df = df.copy()
    temp_df['score'] = analysis.apply(lambda x: x[0])
    temp_df['missing'] = analysis.apply(lambda x: x[1])
    temp_df['found_count'] = analysis.apply(lambda x: x[2])

    filtered = temp_df[(temp_df['found_count'] > 0) & (temp_df['score'] > 0)]
    filtered = filtered.sort_values('score', ascending=False)

    return filtered.head(top_n).to_dict('records')


# =============================
# Инициализация данных
# =============================
def load_data():
    global df, ALL_INGREDIENTS
    try:
        print("Загрузка данных...")
        DB_USER = 'postgres'
        DB_PASSWORD = 'JohnnyCage29'
        DB_HOST = '127.0.0.1'
        DB_PORT = '5432'
        DB_NAME = 'recipes'

        engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

        query = "SELECT name, ingredients, instructions FROM newtable"

        df = pd.read_sql(query, con=engine)
        df = pd.read_csv("recipes_main.csv", encoding='utf-8-sig', quotechar='"', skipinitialspace=True)

        all_ings_set = set()
        for ing_string in df['ingredients']:
            # Разделяем строку на отдельные ингредиенты
            raw_ingredients = ing_string.split("|")

            for ing in raw_ingredients:
                clean_ing = re.split(r'[—–\-]', ing)[0]

                clean_ing = clean_ing.strip().lower().replace('.', '')

                if clean_ing and len(clean_ing) > 1:  # Игнорируем пустые и одиночные символы
                    all_ings_set.add(clean_ing)

        ALL_INGREDIENTS = sorted(list(all_ings_set))
        print(f"Загружено {len(df)} рецептов и {len(ALL_INGREDIENTS)} уникальных ингредиентов.")
        df['ingredients'] = df['ingredients'].fillna("").apply(clean_ingredients)
        df = df[df['ingredients'] != ""].reset_index(drop=True)

    except Exception as e:
        print(f"Ошибка загрузки данных: {e}")
        df = pd.DataFrame()
        ALL_INGREDIENTS = []

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

    strict_res = recommend_strict(df,user_fridge, top_n=5)
    extra_res = recommend_with_extras(df, user_fridge, top_n=5)

    return jsonify({
        "strict": strict_res,
        "extras": extra_res
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)