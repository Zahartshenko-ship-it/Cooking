import pandas as pd
import ast
import difflib
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

df = None
ALL_INGREDIENTS = []


# =============================
# Вспомогательные функции
# =============================

def clean_ingredients(text):
    try:
        if isinstance(text, str):
            try:
                d = ast.literal_eval(text)
                ingredients = [k.replace(" ", "_").lower() for k in d.keys()]
                return " ".join(sorted(ingredients))
            except:
                return text.replace(" ", "_").lower()
        return ""
    except:
        return ""


def fuzzy_match(term, choices_set):
    term = term.lower()
    if term in choices_set:
        return True
    matches = difflib.get_close_matches(term, choices_set, n=1, cutoff=0.8)
    return len(matches) > 0


def fuzzy_intersection(user_set, recipe_list):
    matched_count = 0
    missing = []
    for r_ing in recipe_list:
        if fuzzy_match(r_ing, user_set):
            matched_count += 1
        else:
            missing.append(r_ing)
    return matched_count, missing


# =============================
# Логика рекомендаций
# =============================

def recommend_strict(user_products, top_n=5):
    if not user_products:
        return []

    user_set = set([p.lower().replace(" ", "_") for p in user_products])

    def is_subset(recipe_text):
        if not recipe_text: return False
        recipe_ings = recipe_text.split()
        return all(fuzzy_match(r_ing, user_set) for r_ing in recipe_ings)

    mask = df['ingredients'].apply(is_subset)
    filtered_df = df[mask].copy()

    if filtered_df.empty:
        return []

    filtered_df['ing_count'] = filtered_df['ingredients'].apply(lambda x: len(x.split()) if x else 0)
    filtered_df = filtered_df.sort_values('ing_count', ascending=True)

    results = []
    for _, row in filtered_df.head(top_n).iterrows():
        recipe_ings = row['ingredients'].split() if row['ingredients'] else []
        matched, _ = fuzzy_intersection(user_set, recipe_ings)
        results.append({
            "name": row["name"],
            "ingredients": row["ingredients"].replace("_", " "),  # Для красоты
            "score": matched / len(recipe_ings) if recipe_ings else 0
        })
    return results


def recommend_with_extras(user_products, top_n=5):
    if not user_products:
        return []

    user_set = set([p.lower().replace(" ", "_") for p in user_products])

    def score_recipe(recipe_text):
        if not recipe_text: return -1, [], 0
        recipe_ings = recipe_text.split()
        recipe_set = set(recipe_ings)
        matched, missing = fuzzy_intersection(user_set, recipe_ings)

        if matched == 0: return -1, [], 0

        union = len(recipe_set) + len(user_set) - matched
        jaccard = matched / union if union else 0

        score = jaccard - len(missing) * 0.05
        return score, missing, matched

    analysis = df['ingredients'].apply(score_recipe)

    temp_results = []
    for idx, (score, missing, matched) in enumerate(analysis):
        if score > 0:
            temp_results.append({
                'idx': idx,
                'score': score,
                'missing': missing,
                'matched': matched
            })

    # Сортируем по скорингу
    temp_results.sort(key=lambda x: x['score'], reverse=True)

    final_results = []
    for item in temp_results[:top_n]:
        row = df.iloc[item['idx']]
        final_results.append({
            "name": row["name"],
            "found_count": item['matched'],
            "missing": [m.replace("_", " ") for m in item['missing']],
            "score": round(item['score'], 3)
        })
    return final_results


# =============================
# Инициализация данных
# =============================
def load_data():
    global df, ALL_INGREDIENTS
    try:
        print("Загрузка данных...")
        df = pd.read_csv("povarenok_recipes.csv")

        if 'url' in df.columns:
            df = df.drop(columns=["url"])
        df["ingredients"] = df["ingredients"].fillna("").astype(str)
        df["ingredients"] = df["ingredients"].apply(clean_ingredients)

        trash_names = ['Курица, запеченная на соли', 'Целая курица без косточек', 'Как достать кости из курицы']
        for name in trash_names:
            df = df[df["name"] != name]

        df = df[df["ingredients"] != ""]
        df = df.reset_index(drop=True)

        all_ings_set = set()
        for ing_string in df['ingredients']:
            for ing in ing_string.split():
                all_ings_set.add(ing)

        ALL_INGREDIENTS = sorted(list(all_ings_set))
        print(f"Загружено {len(df)} рецептов и {len(ALL_INGREDIENTS)} уникальных ингредиентов.")

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

    strict_res = recommend_strict(user_fridge, top_n=5)
    extra_res = recommend_with_extras(user_fridge, top_n=5)

    return jsonify({
        "strict": strict_res,
        "extras": extra_res
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)