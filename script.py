import pandas as pd
from sqlalchemy import create_engine, text
from flask import Flask, request, jsonify, render_template
from recomend_algorithms import recommend_strict, recommend_with_extras
from ingredients_funcs import build_ingredients_list
from db_init import get_engine

app = Flask(__name__, static_folder='static', static_url_path='/static')

df = None
ALL_INGREDIENTS = []


def load_data():
    global df, ALL_INGREDIENTS
    try:
        print("Загрузка данных из БД...")
        engine = get_engine()
        df = pd.read_sql("SELECT name, ingredients FROM recipes", con=engine)
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

    print(f"Готово: {len(df)} рецептов, {len(ALL_INGREDIENTS)} уникальных ингредиентов.")


load_data()

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

    # Нормализуем ингредиенты в формат БД: "Лук Курица Картофель"
    ingredients_pipe = "  ".join(ing.capitalize() for ing in ingredients_list)

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
                    INSERT INTO recipes (name, ingredients, instructions)
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

@app.route('/api/recipe/<path:name>')
def get_recipe(name):
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT name, ingredients, instructions FROM recipes WHERE name = :name LIMIT 1"),
                {"name": name}
            )
            row = result.fetchone()
        if row:
            return jsonify({
                "name": row[0],
                "ingredients": row[1],
                "instructions": row[2] or "Описание не указано."
            })
        return jsonify({"error": "Рецепт не найден"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8080)