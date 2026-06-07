// static/js/recipe.js
document.addEventListener('DOMContentLoaded', () => {
    const ingredientsList = document.getElementById('ingredientsList');
    const addIngredientBtn = document.getElementById('addIngredientBtn');
    const recipeForm = document.getElementById('recipeForm');
    const formMessage = document.getElementById('formMessage');

    // 1. Динамическое добавление полей для ингредиентов
    addIngredientBtn.addEventListener('click', () => {
        const wrapper = document.createElement('div');
        wrapper.className = 'ingredient-input-wrap';
        
        wrapper.innerHTML = `
            <input type="text" class="ingredient-input" placeholder="Новый ингредиент" required>
            <button type="button" class="remove-ing-btn">✕</button>
        `;
        
        wrapper.querySelector('.remove-ing-btn').addEventListener('click', () => {
            wrapper.remove();
        });

        ingredientsList.appendChild(wrapper);
    });

    // 2. Отправка формы на бэкенд
    recipeForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const name = document.getElementById('recipeName').value;
        const description = document.getElementById('recipeDescription').value;

        const ingredientInputs = document.querySelectorAll('.ingredient-input');
        const ingredients = Array.from(ingredientInputs)
            .map(input => input.value.trim())
            .filter(value => value !== '');

        const requestData = {
            name: name,
            ingredients: ingredients,
            description: description
        };

        try {
            const response = await fetch('/api/add_recipe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            const result = await response.json();

            if (response.ok) {
                showMessage(`Рецепт "${result.name}" успешно добавлен!`, 'success');
                recipeForm.reset();
                ingredientsList.innerHTML = `
                    <div class="ingredient-input-wrap">
                        <input type="text" class="ingredient-input" placeholder="Например, Курица" required>
                        <button type="button" class="remove-ing-btn" onclick="this.parentElement.remove()">✕</button>
                    </div>
                `;
            } else {
                showMessage(`Ошибка: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('Ошибка сети:', error);
            showMessage('Не удалось связаться с сервером.', 'error');
        }
    });

    function showMessage(text, type) {
        formMessage.innerText = text;
        formMessage.className = `message ${type}`;
    }
});