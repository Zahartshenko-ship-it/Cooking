let allIngredients = [];
let myFridge = [];

// Связь с Python: Загрузка базы ингредиентов
fetch('/api/ingredients')
    .then(res => res.json())
    .then(data => { allIngredients = data; });

const input = document.getElementById('ingredientInput');
const suggestionsBox = document.getElementById('suggestionsBox');

// Автокомплит
input.addEventListener('input', function() {
    const val = this.value.toLowerCase();
    suggestionsBox.innerHTML = '';
    if (!val) { suggestionsBox.style.display = 'none'; return; }

    // Сравниваем пробелы с пробелами: убираем подчёркивания у ингредиента
    const matches = allIngredients
        .filter(ing => ing.toLowerCase().replace(/_/g, ' ').startsWith(val))
        .slice(0, 10);

    if (matches.length > 0) {
        suggestionsBox.style.display = 'block';
        matches.forEach(match => {
            const div = document.createElement('div');
            div.className = 'suggestion-item';
            div.textContent = match.replace(/_/g, ' '); // Отображаем без подчёркиваний
            div.onclick = () => {
                addToFridge(match); // В холодильник идёт оригинал с подчёркиваниями
                input.value = ''; 
                suggestionsBox.style.display = 'none'; 
            };
            suggestionsBox.appendChild(div);
        });
    } else { suggestionsBox.style.display = 'none'; }
});

function manualAdd() {
    const text = input.value.trim();
    if (text) {
        addToFridge(text);
        input.value = '';
    }
}

function addToFridge(ing) {
    if (!myFridge.includes(ing)) {
        myFridge.push(ing);
        renderFridge();
        updateFridgeCounter(); // Обновляем корзину и запускаем пульсацию!
    }
}

function removeFromFridge(ing) {
    myFridge = myFridge.filter(i => i !== ing);
    renderFridge();
    updateFridgeCounter(); // Обновляем счетчик при удалении!
}

function updateFridgeCounter() {
    const floatingFridge = document.getElementById('floatingFridge');
    const fridgeCounter = document.getElementById('fridgeCounter');

    if (floatingFridge && fridgeCounter) {
        // Ставим реальную длину твоего массива
        fridgeCounter.textContent = myFridge.length; 

        // Перезапускаем анимацию покачивания
        floatingFridge.classList.add('pulse');
        setTimeout(() => {
            floatingFridge.classList.remove('pulse');
        }, 500);
    }
}

function renderFridge() {
    const container = document.getElementById('fridgeList');
    if (myFridge.length === 0) {
        container.innerHTML = '<div class="empty-state">Ваш холодильник пуст</div>';
        return;
    }
    container.innerHTML = '';
    myFridge.forEach(ing => {
        const div = document.createElement('div');
        div.className = 'fridge-item';
        div.innerHTML = `<span>${ing.replace(/_/g, ' ')}</span><button class="remove-btn" onclick="removeFromFridge('${ing}')">×</button>`;
        container.appendChild(div);
    });
}

// Связь с Python: Поиск рецептов
function findRecipes() {
    const resultsArea = document.getElementById('resultsArea');
    
    // 1. ПРОВЕРКА: Если в холодильнике пусто — возвращаем заглушку и скроллим к ней
    if (myFridge.length === 0) {
        resultsArea.innerHTML = '<div class="empty-state">Добавьте продукты, чтобы увидеть рецепты</div>';
        resultsArea.scrollIntoView({ behavior: 'smooth' });
        return; // Мягко выходим, сервер мучить не нужно
    }
    
    // 2. Если продукты есть, пишем, что ищем рецепты
    resultsArea.innerHTML = '<div class="empty-state">Ищем лучшие варианты...</div>';
    
    // Плавно скроллим к надписи "Ищем лучшие варианты...", чтобы юзер видел: процесс пошел
    resultsArea.scrollIntoView({ behavior: 'smooth' });

    // 3. Отправляем запрос на сервер
    fetch('/api/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ products: myFridge })
    })
    .then(res => res.json())
    .then(data => {
        resultsArea.innerHTML = '';
        
        // Объединяем результаты для вывода в одну колонку как на макете
        const allFound = [...data.strict, ...data.extras];
        
        if (allFound.length === 0) {
            resultsArea.innerHTML = '<div class="empty-state">Ничего не найдено</div>';
            return;
        }
        
        allFound.forEach(r => {
            const card = document.createElement('div');
            card.className = 'recipe-card';
            
            card.style.setProperty('display', 'flex');
            card.style.setProperty('flex-direction', 'column');
            card.style.setProperty('gap', '0px');

            // Безопасная сборка HTML без использования косых кавычек
            card.innerHTML = '<div class="recipe-main-content" style="display: flex; gap: 15px; width: 100%;">' +
                '<div class="recipe-img"></div>' +
                '<div class="recipe-info" style="flex: 1;">' +
                    '<h3>' + r.name + '</h3>' +
                    '<p>' + r.ingredients.substring(0, 60) + '...</p>' +
                    '<div class="recipe-meta">' +
                        '<span class="time-tag">⏱ 15 мин</span>' +
                        '<span class="match-tag">' + (r.missing ? 'Нужно: ' + r.missing.length : 'Есть всё!') + '</span>' +
                    '</div>' +
                '</div>' +
            '</div>' +
            '<div class="recipe-instructions" style="max-height: 0px; overflow: hidden; width: 100%; transition: max-height 0.3s ease;">' +
                '<hr class="instructions-divider">' +
                '<h4>Способ приготовления:</h4>' +
                '<p class="instructions-text" style="margin: 0px; font-size: 13px; color: #555; line-height: 1.6; white-space: pre-wrap;"></p>' +
            '</div>';

            card.addEventListener('click', function(e) {
                console.log("Кликнули по карточке: " + r.name);
                if (e.target.tagName === 'BUTTON' || e.target.tagName === 'A') return;

                const instructionsBlock = card.querySelector('.recipe-instructions');
                const textBlock = card.querySelector('.instructions-text');

                if (card.classList.contains('expanded')) {
                    card.classList.remove('expanded');
                    instructionsBlock.style.setProperty('max-height', '0px');
                    return;
                }

                document.querySelectorAll('.recipe-card.expanded').forEach(openCard => {
                    openCard.classList.remove('expanded');
                    const openBlock = openCard.querySelector('.recipe-instructions');
                    if (openBlock) {
                        openBlock.style.setProperty('max-height', '0px');
                    }
                });

                if (!textBlock.textContent) {
                    textBlock.textContent = "Загрузка рецепта...";
                    instructionsBlock.style.setProperty('max-height', '100px');

                    fetch('/api/recipe/' + encodeURIComponent(r.name))
                        .then(res => res.json())
                        .then(data => {
                            if (data.instructions) {
                                textBlock.textContent = data.instructions;
                            } else if (data.error) {
                                textBlock.textContent = "Ошибка: " + data.error;
                            }
                            instructionsBlock.style.setProperty('max-height', instructionsBlock.scrollHeight + 'px');
                        })
                        .catch(err => {
                            console.error("Ошибка загрузки:", err);
                            textBlock.textContent = "Не удалось загрузить описание.";
                        });
                } else {
                    instructionsBlock.style.setProperty('max-height', instructionsBlock.scrollHeight + 'px');
                }

                card.classList.add('expanded');
            });

            resultsArea.appendChild(card);
        });

        // После того как карточки успешно добавились на страницу — еще раз плавно центрируем на них экран
        resultsArea.scrollIntoView({ behavior: 'smooth' });
    })
    .catch(err => {
        console.error("Ошибка при поиске рецептов:", err);
        resultsArea.innerHTML = '<div class="empty-state">Ошибка соединения с сервером. Попробуйте позже.</div>';
    });
}

// Закрытие выпадашки при клике вне
document.addEventListener('click', (e) => { if (e.target !== input) suggestionsBox.style.display = 'none'; });

// Логика исчезновения заставки
window.addEventListener('load', () => {
    const intro = document.getElementById('intro-screen');
    
    // Задержка в 600 миллисекунд, чтобы пользователь успел увидеть красивый логотип
    setTimeout(() => {
        intro.classList.add('hidden'); // Заставка уезжает вверх
        
        // Через 800мс (время анимации CSS) полностью удаляем блок из HTML, чтобы не тратить ресурсы
        setTimeout(() => {
            intro.remove();
        }, 800);
        
    }, 600);
});

// Переключатель видимости шторки холодильника
function toggleFridgeMenu() {
    const drawer = document.getElementById('fridgeDrawer');
    drawer.classList.toggle('open');
}

function animateFlyToFridge(event) {
    const fridge = document.getElementById('fridgeIcon');
    if (!fridge) return;

    // 1. Получаем координаты клика мыши на экране
    const startX = event.clientX;
    const startY = event.clientY;

    // 2. Получаем координаты центра холодильника
    const fridgeRect = fridge.getBoundingClientRect();
    const targetX = fridgeRect.left + fridgeRect.width / 2 - 7;
    const targetY = fridgeRect.top + fridgeRect.height / 2 - 7;

    // 3. Создаем летающую точку
    const particle = document.createElement('div');
    particle.classList.add('fly-particle');
    
    // Задаем начальную позицию в точке клика
    particle.style.left = `${startX}px`;
    particle.style.top = `${startY}px`;

    document.body.appendChild(particle);

    // 4. Считаем расстояние для смещения
    const diffX = targetX - startX;
    const diffY = targetY - startY;

    // 5. Запускаем полет
    requestAnimationFrame(() => {
        particle.style.transform = `translate(${diffX}px, ${diffY}px) scale(0.3)`;
        particle.style.opacity = '0.5';
    });

    // 6. Приземление в холодильник
    setTimeout(() => {
        particle.remove();
        
        fridge.classList.add('fridge-pulse-active');
        
        setTimeout(() => {
            fridge.classList.remove('fridge-pulse-active');
        }, 400); 
    }, 800);
}