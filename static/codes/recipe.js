// static/js/recipe.js
document.addEventListener('DOMContentLoaded', () => {
    const ingredientsList = document.getElementById('ingredientsList');
    const addIngredientBtn = document.getElementById('addIngredientBtn');
    const recipeForm = document.getElementById('recipeForm');
    const formMessage = document.getElementById('formMessage');

    // Функция для создания нового ингредиента
    function createIngredientInput(placeholder = 'Новый ингредиент') {
        const wrapper = document.createElement('div');
        wrapper.className = 'ingredient-input-wrap';
        
        wrapper.innerHTML = `
            <input type="text" class="ingredient-input form-input" placeholder="${placeholder}" required>
            <button type="button" class="remove-ing-btn">&times;</button>
        `;
        
        // Добавляем обработчик удаления
        wrapper.querySelector('.remove-ing-btn').addEventListener('click', () => {
            wrapper.style.opacity = '0';
            wrapper.style.transform = 'translateX(10px)';
            setTimeout(() => wrapper.remove(), 300);
        });

        // Анимация появления
        wrapper.style.opacity = '0';
        wrapper.style.transform = 'translateX(-10px)';
        
        return wrapper;
    }

    // 1. Динамическое добавление полей для ингредиентов
    addIngredientBtn.addEventListener('click', () => {
        const wrapper = createIngredientInput('Новый ингредиент');
        ingredientsList.appendChild(wrapper);
        
        // Запускаем анимацию
        setTimeout(() => {
            wrapper.style.transition = 'all 0.3s ease';
            wrapper.style.opacity = '1';
            wrapper.style.transform = 'translateX(0)';
        }, 10);
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
                
                // Очищаем список ингредиентов
                ingredientsList.innerHTML = '';
                
                // Создаем новое поле с правильными обработчиками
                const newWrapper = createIngredientInput('Например, Курица');
                ingredientsList.appendChild(newWrapper);
                
                // Запускаем анимацию
                setTimeout(() => {
                    newWrapper.style.transition = 'all 0.3s ease';
                    newWrapper.style.opacity = '1';
                    newWrapper.style.transform = 'translateX(0)';
                }, 10);
                
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
        
        // Скрываем сообщение через 3 секунды
        setTimeout(() => {
            formMessage.className = 'message hidden';
        }, 3000);
    }
});

