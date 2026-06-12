document.addEventListener('DOMContentLoaded', () => {
    const ingredientsList = document.getElementById('ingredientsList');
    const addIngredientBtn = document.getElementById('addIngredientBtn');
    const recipeForm = document.getElementById('recipeForm');
    const formMessage = document.getElementById('formMessage');

    // Вынесли логику валидации в отдельную функцию
    function setupValidation(inputEl) {
        inputEl.addEventListener('input', function () {
            if (/[,\s]/.test(this.value)) {
                this.classList.remove('input-error');
                void this.offsetWidth;
                this.classList.add('input-error');

                // Показываем предупреждение в модалке, если функция доступна
                if (window.showDialogMessage) {
                    window.showDialogMessage('Пробелы и запятые запрещены. Используйте _', '#dc3545');
                }
            } else {
                this.classList.remove('input-error');
            }
        });
    }

    // Применяем валидацию к самому первому полю, которое уже есть в HTML
    const initialInput = ingredientsList.querySelector('.ingredient-input');
    if (initialInput) {
        setupValidation(initialInput);
    }

    // Функция для создания нового ингредиента
    function createIngredientInput(placeholder = 'Новый ингредиент') {
        const wrapper = document.createElement('div');
        wrapper.className = 'ingredient-input-wrap';

        wrapper.innerHTML = `
            <input type="text" class="ingredient-input form-input" placeholder="${placeholder}" required>
            <button type="button" class="remove-ing-btn">&times;</button>
        `;

        const inputEl = wrapper.querySelector('.ingredient-input');
        setupValidation(inputEl); // Навешиваем валидацию на новое поле

        // Обработчик удаления
        wrapper.querySelector('.remove-ing-btn').addEventListener('click', () => {
            wrapper.style.opacity = '0';
            wrapper.style.transform = 'translateX(10px)';
            setTimeout(() => wrapper.remove(), 300);
        });

        wrapper.style.opacity = '0';
        wrapper.style.transform = 'translateX(-10px)';

        return wrapper;
    }

    // Динамическое добавление полей для ингредиентов
    addIngredientBtn.addEventListener('click', () => {
        const wrapper = createIngredientInput('Новый ингредиент');
        ingredientsList.appendChild(wrapper);

        setTimeout(() => {
            wrapper.style.transition = 'all 0.3s ease';
            wrapper.style.opacity = '1';
            wrapper.style.transform = 'translateX(0)';
        }, 10);

        if (window.showDialogMessage) {
            window.showDialogMessage('Поле добавлено', '#007bff');
        }
    });

    // Отправка формы на бэкенд
    recipeForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const name = document.getElementById('recipeName').value;
        const description = document.getElementById('recipeDescription').value;
        const ingredientInputs = document.querySelectorAll('.ingredient-input');

        const invalidInput = Array.from(ingredientInputs).find(input => /[,\s]/.test(input.value));
        if (invalidInput) {
            invalidInput.classList.remove('input-error');
            void invalidInput.offsetWidth;
            invalidInput.classList.add('input-error');
            invalidInput.focus();
            showMessage('Ингредиент содержит пробел или запятую. Используйте _', 'error');
            return;
        }

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
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            });

            const result = await response.json();

            if (response.ok) {
                showMessage(`Рецепт "${result.name}" успешно добавлен!`, 'success');
                recipeForm.reset();
                ingredientsList.innerHTML = '';

                const newWrapper = createIngredientInput('Например, Курица');
                ingredientsList.appendChild(newWrapper);

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
        setTimeout(() => {
            formMessage.className = 'message hidden';
        }, 3000);
    }
});