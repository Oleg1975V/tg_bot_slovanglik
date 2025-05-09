
# **Документация по использованию программы "Slovanglik**

## **1. Назначение программы**

Бот предназначен для изучения английских слов через интерактивные карточки.
Основные функции:

- Изучение слов по уровням сложности и категориям.
- Добавление и удаление пользовательских слов.
- Статистика количества слов по уровням и категориям.
- Автоматическая загрузка стандартной базы слов через команду /start или кнопку Обновить.
- Адаптивное обучение (слова с ошибками показываются чаще).
- Слова предоставляются в случайном порядке, исключая повторения подряд на протяжении 3 следующих слов.

## **2. Установка и запуск**

Требования:

- Python 3.9+
- PostgreSQL
- Библиотеки: python-dotenv, psycopg2, sqlalchemy, pyTelegramBotAPI

Настройка окружения:

- Установите зависимости: pip install -r requirements.txt

- Создайте файл .env в корне проекта:

BOT\_TOKEN=ваш\_токен\_бота

DB\_USER=postgres

DB\_PASSWORD=ваш\_пароль

DB\_HOST=localhost

DB\_PORT=5432

DB\_NAME=english\_learning

Инициализация БД:

Запустите setup\_db.py для создания структуры БД и заполнения стандартными словами: python setup\_db.py

Запуск бота: python main.py

## **3. Начало работы**

Команда: /start создает аккаунт в БД

Главное меню:

Бот приветствует пользователя, отображает доступные уровни сложности и категории слов.

*Пример ответа:*

*Хэллоу! Ваш личный бот для изучения английского готов к работе!*

*Выберите уровень для изучения:*

### *Уровень 1*

` *• Размеры*

` *• Цвета*

` *• Числа*

### *Уровень 2*

` *• Местоимения*

` *• Семья*

` *• Человек*

### *Уровень 3*

` *• Еда*

` *• Мебель*

` *• Посуда*

Выберите уровень и категорию для изучения

## **4. Основные функции**

4\.1. Выбор уровня и категории

Уровни:

Отображаются кнопками (Уровень 1, Уровень 2, и т.д.).

Категории:

Отображаются кнопками (например, "Цвета").

Навигация:

- Выбрать уровень - вернуться к выбору уровня.
- Выбрать категорию - выбрать другую категорию в текущем уровне.

### 4\.2.  Обучение

Карточка слова:

Бот показывает изучаемое слово на русском и 4 варианта ответа на английском из которых необходимо выбрать правильный ответ.

Механика:

- При правильном ответе → новое слово.
- При ошибке → попробуйте еще раз, при этом неправильно переведенное слово повторяется в последующем чаще.
- Кнопка Дальше - пропустить текущее слово (оставить без ответа).

Добавление пользовательского слова:

1. Нажмите "Добавить слово +"
2. Введите русское слово: "стол"
3. Перевод: "table"
Слово добавится в вашу персональную базу.

Удаление слова

1. Нажмите "Удалить слово -"
2. Введите русское слово: "стол"
3. Слово удалится из вашей базы.

### 4\.3. Справка по командам

- «/Start» - начало работы с ботом.
- «Выбрать уровень» - переход к выбору уровня сложности.
- «Выбрать категорию» - переход к выбору категории для текущего уровня.
- «Дальше» - пропустить текущее слово и перейти к следующему.
- «Добавить слово +» - добавить новое слово в персональную базу.
- «Удалить слово -» -  удалить слово из персональной базы.
- «Обновить» - обновляет стандартные слова из общей базы.
- «Статистика» - показывает статистику по количеству слов.

### 4\.4. Статистика

Команда (кнопка) Статистика показывает:

- Общее количество изучаемых слов.
- Распределение количества слов по уровням.
- Распределение количества слов по категориям.

*Пример:*

"Всего слов - 42

Уровень 1 - 15

Числа - 5

Цвета - 7

Местоимения - 3"

### 4\.5. Особенности работы программы

Персонализация:

- Каждый пользователь имеет свой набор слов (стандартные + пользовательские).
- Текущее состояние (уровень, категория).

Алгоритм обучения:

- Слова с ошибками добавляются чаще в последующем предложении.
- Исключается повторение на протяжении следующих 3 слов.

База данных:

1. Таблица users : хранит данные о пользователях (id чата, имя).
2. Таблица words: хранится общая база стандартных слов (неизменяемая).
3. Таблица user\_words (для возможности редактирования) хранятся:

- Стандартные слова с флагом is\_custom=False.
- Пользовательские слова флагом is\_custom=True.
  Структура БД и индексы оптимизированы для быстрого поиска слов по уровням и категориям.

## **5. Технические детали:**

- База данных : PostgreSQL.
- ORM : SQLAlchemy.
- Бот реализован на библиотеке telebot.
- Кэширование состояний : временные состояния пользователей хранятся в оперативной памяти (State).

### **Заключение:**

Программа "Slovanglik" предоставляет удобный инструмент для изучения английских слов через Telegram. Гибкая система уровней, категорий и пользовательских слов позволяет адаптировать обучение под индивидуальные потребности.
