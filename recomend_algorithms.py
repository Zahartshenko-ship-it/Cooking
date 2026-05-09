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
