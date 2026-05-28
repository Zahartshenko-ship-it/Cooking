import re

def build_ingredients_list(df_source):
    #Собирает список всех уникальных ингредиентов из датафрейма
    all_ings_set = set()
    for ing_string in df_source['ingredients']:
        if not isinstance(ing_string, str):
            continue
        raw_ingredients = ing_string.split()
        for ing in raw_ingredients:
            clean_ing = re.split(r'[—–\-]', ing)[0]
            clean_ing = clean_ing.strip().lower().replace('.', '').replace('_', ' ')
            if clean_ing and len(clean_ing) > 1:
                all_ings_set.add(clean_ing)
    return sorted(list(all_ings_set))