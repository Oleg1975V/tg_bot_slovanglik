import random
from telebot import types, TeleBot
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from setup_db import (
    engine, User, Word, UserWord, UserState,
    load_standard_words_for_user
)
from dotenv import load_dotenv
from typing import Dict, Optional
import os

# Загрузка переменных окружения
load_dotenv()
print("Starting Telegram bot...")

# Инициализация бота с использованием HTML для форматирования
token_bot = os.getenv("BOT_TOKEN")
bot = TeleBot(token_bot, parse_mode="HTML")

# Создание сессии базы данных
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Command:
    """Команды для взаимодействия с ботом."""
    ADD_WORD = 'Добавить слово +'
    NEXT = 'Дальше ⏭'
    DELETE_WORD = 'Удалить слово -'


class State:
    """Класс для хранения временных состояний пользователей."""

    def __init__(self):
        self.users_state: Dict[int, dict] = {}

    def get(self, chat_id: int) -> Optional[dict]:
        """Получить состояние пользователя"""
        return self.users_state.get(chat_id)

    def set(self, chat_id: int, data: dict):
        """Установить состояние пользователя"""
        self.users_state[chat_id] = data

    def clear(self, chat_id: int):
        """Очистить состояние пользователя"""
        if chat_id in self.users_state:
            del self.users_state[chat_id]


state_storage = State()


def get_all_words(chat_id: int, category: str) -> list:
    """
    Получает все слова для указанной категории.

    :param chat_id: ID чата пользователя
    :param category: Категория слов
    :return: Список всех слов
    """
    db = SessionLocal()
    user = db.query(User).filter_by(chat_id=chat_id).first()
    state = db.query(UserState).filter_by(user_id=user.id).first()
    current_level = state.level if state else 1
    words = []
    if user:
        words = db.query(UserWord).filter_by(
            user_id=user.id,
            category=category,
            level=current_level
        ).all()
    db.close()
    return words


def get_categories_for_level(level):
    """
    Получает категории для указанного уровня.

    :param level: Уровень сложности
    :return: Список категорий
    """
    db = SessionLocal()
    try:
        categories = db.query(Word.category).filter_by(
            level=level
        ).distinct().all()
        user_categories = db.query(UserWord.category).filter_by(
            level=level
        ).distinct().all()
        all_categories = set(
            [category[0].lower() for category in categories] +
            [category[0].lower() for category in user_categories]
        )
        return list(all_categories)
    finally:
        db.close()


def get_levels_and_categories() -> dict:
    """
    Получает уровни и категории из базы данных.

    :return: Словарь уровней и категорий
    """
    db = SessionLocal()
    try:
        levels = db.query(Word.level).distinct().order_by(Word.level).all()
        levels_dict = {}
        for level in levels:
            level_number = level[0]
            categories = db.query(Word.category).filter_by(
                level=level_number
            ).distinct().all()
            categories_list = [category[0].title() for category in categories]
            levels_dict[f"Уровень {level_number}"] = categories_list
        return levels_dict
    finally:
        db.close()


# Главное меню
@bot.message_handler(commands=['start'])
def start(message):
    """
    Обработчик команды /start.

    :param message: Сообщение от пользователя
    """
    chat_id = message.chat.id
    username = message.from_user.username
    db = SessionLocal()
    user = db.query(User).filter_by(chat_id=chat_id).first()
    if not user:
        new_user = User(chat_id=chat_id, username=username)
        db.add(new_user)
        db.commit()
        # Создаем запись в UserState
        user_state = UserState(user_id=new_user.id)
        db.add(user_state)
        db.commit()
        # Загружаем стандартные слова для нового пользователя
        load_standard_words_for_user(new_user.id)
    db.close()
    # Приветствие при запуске бота
    greetings = [
        "Привет! Я твой новый помощник по изучению английского языка!",
        "Здравствуйте! Готов помочь вам освоить английский язык?",
        "Приветствуем вас! Давайте вместе учим английский!",
        "Хэллоу! Ваш личный бот для изучения английского готов к работе!"
    ]
    random_greeting = random.choice(greetings)
    bot.send_message(chat_id, random_greeting)
    go_to_main_menu(message)


def go_to_main_menu(message):
    """
    Перенаправляет пользователя в главное меню выбора уровней.

    :param message: Сообщение от пользователя
    """
    chat_id = message.chat.id
    levels_and_categories = get_levels_and_categories()
    message_text = "<b>Выберите уровень для изучения:</b>\n"

    for level, categories in levels_and_categories.items():
        message_text += f"\n<b>{level}</b>\n"
        for category in categories:
            message_text += f"  • <i>{category}</i>\n"

    markup = types.ReplyKeyboardMarkup(row_width=2)
    buttons = [
        types.KeyboardButton(level)
        for level in levels_and_categories.keys()
    ]

    if len(buttons) % 2 != 0:
        buttons.append(types.KeyboardButton(""))

    buttons.extend([
        types.KeyboardButton("Справка"),
        types.KeyboardButton("Обновить"),
        types.KeyboardButton("Статистика")
    ])

    markup.add(*buttons)
    bot.send_message(chat_id, message_text, reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "Обновить")
def update_words(message):
    """
    Обработчик команды "Обновить".

    :param message: Сообщение от пользователя
    """
    chat_id = message.chat.id
    db = SessionLocal()
    user = db.query(User).filter_by(chat_id=chat_id).first()
    if not user:
        bot.send_message(chat_id, "Пользователь не найден.")
        db.close()
        return

    load_standard_words_for_user(user.id)
    bot.send_message(chat_id, "База данных обновлена")
    db.close()


@bot.message_handler(func=lambda message: message.text == "Статистика")
def show_statistics(message):
    """
    Обработчик команды "Статистика".

    :param message: Сообщение от пользователя
    """
    chat_id = message.chat.id
    db = SessionLocal()

    try:
        user = db.query(User).filter_by(chat_id=chat_id).first()
        if not user:
            bot.send_message(chat_id, "Пользователь не найден.")
            return

        stats = db.query(
            UserWord.level,
            UserWord.category,
            func.count(UserWord.id)
        ).filter(
            UserWord.user_id == user.id
        ).group_by(
            UserWord.level,
            UserWord.category
        ).all()

        levels = {}
        total_words = 0

        for level, category, count in stats:
            if level not in levels:
                levels[level] = {}
            levels[level][category] = count
            total_words += count

        if not levels:
            bot.send_message(chat_id, "В вашей базе пока нет слов.")
            return

        response = f"<b>Статистика</b>\nВсего слов - {total_words}\n"

        for level_num in sorted(levels.keys()):
            categories = levels[level_num]
            level_total = sum(categories.values())
            response += f"\n{level_num} Уровень - {level_total}\n"

            for category in sorted(categories.keys(), key=lambda x: x.lower()):
                response += f"{category.title()} - {categories[category]}\n"

        bot.send_message(chat_id, response)

    except Exception as e:
        print(f"Ошибка при получении статистики: {e}")
        bot.send_message(chat_id, "Ошибка формировании статистики.")
    finally:
        db.close()


@bot.message_handler(func=lambda message: message.text == "Справка")
def show_help(message):
    """
    Обработчик команды "Справка".

    :param message: Сообщение от пользователя
    """
    chat_id = message.chat.id
    help_text = (
        "<b>Справка по использованию бота Slovanglik</b>\n"
        "<i>Назначение программы:</i>\n"
        "Программа предназначена для изучения английского языка через "
        "перевод слов с русского на английский.\n"
        "<i>Основные возможности:</i>\n"
        "• Выбор уровня сложности\n"
        "• Выбор категории слов в каждом уровне сложности\n"
        "• Обучение переводу слов с выбором вариантов ответа\n"
        "• Добавление новых слов\n"
        "• Удаление изученных слов\n"
        "• Статистика количества слов по уровням и категориям\n"
        "<i>Порядок действий:</i>\n"
        "1. Выберите уровень сложности, нажав на соответствующую кнопку "
        "<b>Уровень X</b>, где X — выбранный уровень сложности.\n"
        "2. Выберите категорию слов для обучения, нажав на соответствующую "
        "кнопку <b>Название Категории</b>, в выбранном уровне сложности.\n"
        "3. Бот покажет слово на русском языке и ниже варианты перевода.\n"
        "4. Выберите правильный вариант перевода из предложенных.\n"
        "5. В случае правильного ответа, будет предложенно следующее слово. "
        "При неверном ответе - еще попытка.\n"
        "6. Используйте кнопку <b>Дальше ⏭</b> для перехода к следующему "
        "слову минуя ответ.\n"
        "7. Используйте кнопку <b>Добавить слово +</b> для добавления нового "
        "слова (следуя подсказкам).\n"
        "8. Используйте кнопку <b>Удалить слово -</b> для удаления слова из "
        "словаря (следуя подсказкам).\n"
        "9. Используйте кнопку <b>Выбрать категорию 🔄</b> для выбора другой "
        "категории слов на данном уровне сложности.\n"
        "10. Используйте кнопку <b>Выбрать уровень 🔄</b> для выбора другого "
        "уровня сложности.\n"
        "11. Кнопка <b>Обновить</b> обновляет общую базу данных слов, "
        "при этом слова добавленные пользователем сохраняются.\n"
        "12. Кнопка <b>Статистика</b> выводит на экран общее количество слов "
        "для изучения, а так же на каждом уровне и в категориях.\n"
        "Примечание:\n"
        "- слова предлагаются для перевода в хаотичном порядке\n"
        "- слова в которых была допущена ошибка при выборе варианта перевода, "
        "предлагаются далее чаще других (как наиболее сложные)"
    )
    bot.send_message(chat_id, help_text, parse_mode="HTML")


@bot.message_handler(func=lambda message: message.text.startswith("Уровень"))
def select_level(message):
    """
    Обработчик выбора уровня сложности.

    :param message: Сообщение от пользователя
    """
    chat_id = message.chat.id
    level = int(message.text.split()[-1])
    db = SessionLocal()
    user = db.query(User).filter_by(chat_id=chat_id).first()

    if not user:
        bot.send_message(chat_id, "Пользователь не найден.")
        db.close()
        return

    state = db.query(UserState).filter_by(user_id=user.id).first()

    if not state:
        state = UserState(user_id=user.id, level=level)
        db.add(state)
    else:
        state.level = level

    db.commit()
    bot.send_message(chat_id, f"Уровень {level} успешно загружен!")
    # Формируем кнопки для категорий выбранного уровня
    categories = get_categories_for_level(level)

    if not categories:
        bot.send_message(chat_id, "На этом уровне нет доступных категорий.")
        db.close()
        return

    markup = types.ReplyKeyboardMarkup(row_width=2)
    buttons = [
        types.KeyboardButton(category.title())
        for category in categories
    ]
    buttons.append(types.KeyboardButton("Выбрать уровень 🔄"))
    markup.add(*buttons)

    bot.send_message(chat_id, "Выберите категорию:", reply_markup=markup)
    db.close()


def select_category_menu(message):
    """
    Перенаправляет пользователя в меню выбора категории.

    :param message: Сообщение от пользователя
    """
    chat_id = message.chat.id
    db = SessionLocal()
    user = db.query(User).filter_by(chat_id=chat_id).first()
    state = db.query(UserState).filter_by(user_id=user.id).first()

    if not state or not state.level:
        go_to_main_menu(message)
        db.close()
        return

    level = state.level
    categories = get_categories_for_level(level)

    markup = types.ReplyKeyboardMarkup(row_width=2)
    buttons = [
        types.KeyboardButton(category.title())
        for category in categories
    ]
    buttons.append(types.KeyboardButton("Выбрать уровень 🔄"))
    markup.add(*buttons)

    bot.send_message(
        chat_id,
        "<b>Выберите категорию:</b>",
        reply_markup=markup
    )
    db.close()


def is_valid_category(message):
    """
    Проверяет существование выбранной категории на заданном уровне сложности.

    :param message: Сообщение от пользователя
    :return: True, если категория существует, иначе False
    """
    chat_id = message.chat.id
    db = SessionLocal()
    user = db.query(User).filter_by(chat_id=chat_id).first()
    state = db.query(UserState).filter_by(user_id=user.id).first()

    if not state or not state.level:
        db.close()
        return False

    category = message.text.strip().lower()
    level = state.level
    # Проверяем, существует ли категория на заданном уровне сложности
    category_in_word = db.query(Word.category).filter_by(
        category=category, level=level
    ).first()

    category_in_user_word = db.query(UserWord.category).filter_by(
        user_id=user.id, category=category, level=level
    ).first()

    db.close()
    return category_in_word is not None or category_in_user_word is not None


@bot.message_handler(func=is_valid_category)
def select_category(message):
    """
    Обработчик выбора категории.

    :param message: Сообщение от пользователя
    """
    chat_id = message.chat.id
    category = message.text.strip().lower()
    db = SessionLocal()
    user = db.query(User).filter_by(chat_id=chat_id).first()
    state = db.query(UserState).filter_by(user_id=user.id).first()
    if not state:
        bot.send_message(chat_id, "Ошибка состояния пользователя.")
        db.close()
        return

    state.category = category
    db.commit()
    words = get_all_words(chat_id, category)

    if not words:
        bot.send_message(chat_id, "В этой категории пока нет слов.")
        db.close()
        return

    create_card(chat_id, category, words, state)
    db.close()


def create_card(chat_id: int, category: str, words: list, state: UserState):
    """
    Создает карточку для обучения.

    :param chat_id: ID чата пользователя
    :param category: Категория слов
    :param words: Список слов
    :param state: Состояние пользователя
    """
    if not words:
        bot.send_message(chat_id, "Нет доступных слов для обучения.")
        return

    # Получаем временные состояния пользователя
    temp_state = state_storage.get(chat_id) or {}

    # Получаем список последних трёх слов
    recent_words = temp_state.get("recent_words", [])

    # Получаем список слов с неправильными ответами
    wrong_answers = temp_state.get("wrong_answers", [])

    # Фильтруем слова, исключая последние три
    available_words = [
        word for word in words if word.word.lower() not in recent_words
    ]

    if not available_words:
        available_words = words

    # Увеличиваем вероятность выбора слов с неправильными ответами
    weighted_words = available_words.copy()
    wrong_words_set = set(wrong_answers)

    for word in available_words:
        if word.word.lower() in wrong_words_set:
            weighted_words.extend([word] * 2)

    if not weighted_words:
        weighted_words = available_words

    # Получаем случайное слово из доступных
    word = random.choice(weighted_words)
    target_word = word.word
    translate = word.translation

    # Обновляем список последних трёх слов как очередь
    recent_words.append(target_word.lower())

    if len(recent_words) > 3:
        recent_words.pop(0)

    # Сохраняем обновленные состояния
    temp_state["recent_words"] = recent_words
    temp_state["target_word"] = target_word.lower()
    temp_state["translate_word"] = translate.lower()
    state_storage.set(chat_id, temp_state)
    # Формируем кнопки
    options = [w.word for w in words if w.word.lower() != target_word.lower()]
    random.shuffle(options)

    unique_options = {target_word.lower()}
    while len(unique_options) < 4 and options:
        unique_options.add(options.pop().lower())

    options = list(unique_options)
    random.shuffle(options)

    markup = types.ReplyKeyboardMarkup(row_width=2)
    buttons = [types.KeyboardButton(option) for option in options]
    buttons.extend([
        types.KeyboardButton(Command.NEXT),
        types.KeyboardButton(Command.ADD_WORD),
        types.KeyboardButton(Command.DELETE_WORD),
        types.KeyboardButton("Выбрать категорию 🔄"),
        types.KeyboardButton("Выбрать уровень 🔄")
    ])
    markup.add(*buttons)
    # Отправляем карточку
    greeting = (
        f"<b>Уровень {state.level}</b> - <b>{category.capitalize()}</b>\n"
        "Выберите вариант перевода слова:\n"
        f"🇷🇺 <b><i>{translate}</i></b>"
    )
    bot.send_message(chat_id, greeting, reply_markup=markup)


# Следующая карточка
@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_card(message):
    """
    Обработчик команды "Дальше ⏭".

    :param message: Сообщение от пользователя
    """
    chat_id = message.chat.id
    db = SessionLocal()
    user = db.query(User).filter_by(chat_id=chat_id).first()
    state = db.query(UserState).filter_by(user_id=user.id).first()

    if not state or not state.category:
        db.close()
        return

    words = get_all_words(chat_id, state.category)
    create_card(chat_id, state.category, words, state)
    db.close()


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    """
    Обработчик команды "Добавить слово +" для начала процесса добавления слова.

    :param message: Сообщение от пользователя
    """
    chat_id = message.chat.id
    db = SessionLocal()
    user = db.query(User).filter_by(chat_id=chat_id).first()
    state = db.query(UserState).filter_by(user_id=user.id).first()

    if not state or not state.category:
        db.close()
        return

    bot.send_message(chat_id, "Введите слово на русском:")
    temp_state = state_storage.get(chat_id) or {}
    temp_state["action"] = "add_word"
    temp_state["category"] = state.category.lower()
    temp_state["level"] = state.level
    state_storage.set(chat_id, temp_state)
    db.close()


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    """
    Обработчик команды "Удалить слово -" для начала процесса удаления слова.

    :param message: Сообщение от пользователя
    """
    chat_id = message.chat.id
    db = SessionLocal()
    user = db.query(User).filter_by(chat_id=chat_id).first()
    state = db.query(UserState).filter_by(user_id=user.id).first()

    if not state or not state.category:
        db.close()
        return

    bot.send_message(chat_id, "Введите слово на русском для удаления:")
    temp_state = state_storage.get(chat_id) or {}
    temp_state["action"] = "delete_word"
    temp_state["category"] = state.category.lower()
    temp_state["level"] = state.level
    state_storage.set(chat_id, temp_state)
    db.close()


def process_word_actions(message, user, state, temp_state):
    """
    Обрабатывает действия с добавлением, удалением слов и проверкой ответов.

    :param message: Сообщение от пользователя
    :param user: Объект пользователя
    :param state: Состояние пользователя
    :param temp_state: Временное состояние пользователя
    """
    chat_id = message.chat.id
    db = SessionLocal()
    text = message.text.lower()
    # Логика добавления слова
    if temp_state.get("action") == "add_word":
        temp_state["russian"] = text
        bot.send_message(chat_id, "Введите перевод на английский:")
        temp_state["action"] = "add_translation"
        state_storage.set(chat_id, temp_state)

    elif temp_state.get("action") == "add_translation":
        russian = temp_state.pop("russian", None)
        english = text
        category = temp_state.get("category")
        level = temp_state.get("level")

        if not russian or not category or not level:
            bot.send_message(chat_id, "Ошибка данных добавления слова.")
            db.close()
            return

        existing_word = db.query(UserWord).filter_by(
            user_id=user.id,
            word=english.lower(),
            translation=russian.lower(),
            category=category.lower(),
            level=level
        ).first()

        if existing_word:
            bot.send_message(
                chat_id,
                f"Слово '{russian}' → '{english}' уже имеется."
            )
            # Создаем новую карточку после добавления слова
            words = get_all_words(chat_id, category)
            create_card(chat_id, category, words, state)
            state_storage.clear(chat_id)
        else:
            # Добавляем новое слово в базу данных
            new_word = UserWord(
                user_id=user.id,
                word=english.lower(),
                translation=russian.lower(),
                category=category.lower(),
                level=level
            )
            db.add(new_word)
            db.commit()
            bot.send_message(
                chat_id,
                f"Слово '{russian} → {english}' уже имеется."
            )
            # Создаем новую карточку после добавления слова
            words = get_all_words(chat_id, category)
            create_card(chat_id, category, words, state)
            state_storage.clear(chat_id)
    # Логика удаления слова
    elif temp_state.get("action") == "delete_word":
        category = temp_state.get("category")
        level = temp_state.get("level")
        # Ищем слово для удаления
        word_to_delete = db.query(UserWord).filter_by(
            user_id=user.id,
            translation=text,
            category=category.lower(),
            level=level
        ).first()

        if word_to_delete:
            db.delete(word_to_delete)
            db.commit()
            bot.send_message(chat_id, f"Слово '{text}' удалено!")
        else:
            bot.send_message(chat_id, "Слово не найдено.")
        # Создаем новую карточку после удаления слова
        words = get_all_words(chat_id, category)
        create_card(chat_id, category, words, state)
        state_storage.clear(chat_id)
    # Проверка ответа на карточке
    else:
        target_word = temp_state.get("target_word")

        if not target_word:
            bot.send_message(chat_id, "Ошибка: текущее слово не найдено.")
            db.close()
            return

        if text == target_word:
            bot.send_message(chat_id, "Правильно! 👍")
            # Создаем новую карточку после правильного ответа
            words = get_all_words(chat_id, state.category)
            create_card(chat_id, state.category, words, state)
        else:
            bot.send_message(chat_id, "Неправильно! Попробуйте снова.")
            # Добавляем слово в список неправильных ответов
            wrong_answers = temp_state.get("wrong_answers", [])

            if target_word not in wrong_answers:
                wrong_answers.append(target_word)

            temp_state["wrong_answers"] = wrong_answers
            state_storage.set(chat_id, temp_state)

    db.close()


def process_menu_navigation(message, db):
    """
    Обрабатывает навигацию между меню.

    :param message: Сообщение от пользователя
    :param db: Сессия базы данных
    :return: True, если произошел переход, иначе False
    """
    text = message.text
    # Переход к выбору категории
    if text == "Выбрать категорию 🔄":
        select_category_menu(message)
        return True
    # Переход к выбору уровня
    elif text == "Выбрать уровень 🔄":
        go_to_main_menu(message)
        return True

    return False


@bot.message_handler(func=lambda message: True)
def handle_text(message):
    """
    Обработчик всех текстовых сообщений.

    :param message: Сообщение от пользователя
    """
    chat_id = message.chat.id
    # Получаем долгосрочное состояние из базы данных
    db = SessionLocal()
    user = db.query(User).filter_by(chat_id=chat_id).first()
    state = db.query(UserState).filter_by(user_id=user.id).first()
    # Получаем временное состояние из оперативной памяти
    current_temp_state = state_storage.get(chat_id) or {}

    if not state or not user:
        db.close()
        return
    # Обработка переходов между меню
    if process_menu_navigation(message, db):
        db.close()
        return
    # Обработка действий с добавлением, удалением слов и проверкой ответов
    process_word_actions(message, user, state, current_temp_state)
    db.close()


if __name__ == "__main__":
    bot.infinity_polling()
