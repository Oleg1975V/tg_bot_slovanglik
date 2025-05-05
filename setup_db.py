"""
Модуль для работы с базой данных приложения для изучения слов.
Включает модели данных, инициализацию БД и утилиты для работы с данными.
"""

import os

import psycopg2
from dotenv import load_dotenv
from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    BigInteger,
    create_engine,
)
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

# Загрузка переменных окружения из файла .env
load_dotenv()

# Базовый класс для декларативного определения моделей
Base = declarative_base()


class User(Base):
    """Модель, представляющая пользователя приложения.

    Attributes:
        id (int): Уникальный идентификатор пользователя
        chat_id (int): Уникальный идентификатор чата пользователя
        username (str): Имя пользователя (опционально)
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(255))


class Word(Base):
    """Модель, представляющая стандартное слово для изучения.

    Attributes:
        id (int): Уникальный идентификатор слова
        word (str): Слово на иностранном языке
        translation (str): Перевод слова
        category (str): Категория слова
        level (int): Уровень сложности слова
    """

    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(255), nullable=False, index=True)
    translation = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    level = Column(Integer, nullable=False, index=True)

    __table_args__ = (Index("ix_category_level", "category", "level"),)


class UserWord(Base):
    """Модель для хранения слов, связанных с пользователем.

    Attributes:
        id (int): Уникальный идентификатор записи
        user_id (int): Идентификатор пользователя
        word (str): Слово на иностранном языке
        translation (str): Перевод слова
        category (str): Категория слова
        level (int): Уровень сложности
        is_custom (bool): Флаг пользовательского слова
    """

    __tablename__ = "user_words"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    word = Column(String(255), nullable=False)
    translation = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    level = Column(Integer, nullable=False, index=True)
    is_custom = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_user_category", "user_id", "category"),
        Index("ix_user_level", "user_id", "level"),
        Index("ix_full_filter", "user_id", "category", "level"),
    )


class UserState(Base):
    """Модель для хранения текущего состояния пользователя.

    Attributes:
        id (int): Уникальный идентификатор состояния
        user_id (int): Идентификатор пользователя
        level (int): Текущий уровень сложности
        category (str): Текущая категория обучения
    """

    __tablename__ = "user_states"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    level = Column(Integer, nullable=True)
    category = Column(String(50), nullable=True)

    __table_args__ = (Index("ix_user_state", "user_id"),)


# Получение параметров подключения из переменных окружения
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Формирование URL для подключения к базе данных
DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_database_if_not_exists() -> None:
    """Создает базу данных PostgreSQL, если она не существует."""
    try:
        # Подключение к системной базе для проверки существования целевой БД
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database="postgres",
            connect_timeout=5,
        )
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (DB_NAME,)
        )
        exists = cursor.fetchone()

        if not exists:
            # Создание новой базы данных с UTF-8 кодировкой
            create_db_query = (
                f"CREATE DATABASE {DB_NAME} "
                "ENCODING 'UTF8' "
                "TEMPLATE template0"
            )
            cursor.execute(create_db_query)
            print(f"[INFO] База данных '{DB_NAME}' создана")
        else:
            print(f"[INFO] База данных '{DB_NAME}' уже существует")

    except psycopg2.errors.InsufficientPrivilege:
        print("[ERROR] Недостаточно прав для создания БД")
        raise
    except psycopg2.OperationalError as e:
        print(f"[FATAL] Ошибка подключения: {str(e)}")
        raise SystemExit(1)
    finally:
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals():
            conn.close()


def init_db() -> None:
    """Инициализирует структуру базы данных, создавая все таблицы."""
    try:
        Base.metadata.create_all(bind=engine)
        print("Таблицы успешно созданы")
    except Exception as e:
        print(f"Ошибка при создании таблиц: {e}")


def populate_default_words() -> None:
    """Заполняет таблицу слов стандартным набором данных."""
    default_words = [
        # Уровень 1: Числа, Цвета, Размеры
        {"word": "one", "translation": "один",
         "category": "числа", "level": 1},
        {"word": "two", "translation": "два",
         "category": "числа", "level": 1},
        {"word": "three", "translation": "три",
         "category": "числа", "level": 1},
        {"word": "red", "translation": "красный",
         "category": "цвета", "level": 1},
        {"word": "blue", "translation": "синий",
         "category": "цвета", "level": 1},
        {"word": "thin", "translation": "худой",
         "category": "размеры", "level": 1},
        {"word": "fat", "translation": "толстый",
         "category": "размеры", "level": 1},
        {"word": "long", "translation": "длинный",
         "category": "размеры", "level": 1},
        {"word": "short", "translation": "короткий",
         "category": "размеры", "level": 1},

        # Уровень 2: Местоимения, Семья, Человек
        {"word": "I", "translation": "я",
         "category": "местоимения", "level": 2},
        {"word": "you", "translation": "ты",
         "category": "местоимения", "level": 2},
        {"word": "he", "translation": "он",
         "category": "местоимения", "level": 2},
        {"word": "she", "translation": "она",
         "category": "местоимения", "level": 2},
        {"word": "father", "translation": "отец",
         "category": "семья", "level": 2},
        {"word": "mother", "translation": "мать",
         "category": "семья", "level": 2},
        {"word": "brother", "translation": "брат",
         "category": "семья", "level": 2},
        {"word": "sister", "translation": "сестра",
         "category": "семья", "level": 2},
        {"word": "boy", "translation": "мальчик",
         "category": "человек", "level": 2},
        {"word": "girl", "translation": "девочка",
         "category": "человек", "level": 2},
        {"word": "man", "translation": "мужчина",
         "category": "человек", "level": 2},
        {"word": "woman", "translation": "женщина",
         "category": "человек", "level": 2},

        # Уровень 3: Еда, Посуда, Мебель
        {"word": "apple", "translation": "яблоко",
         "category": "еда", "level": 3},
        {"word": "banana", "translation": "банан",
         "category": "еда", "level": 3},
        {"word": "bread", "translation": "хлеб",
         "category": "еда", "level": 3},
        {"word": "water", "translation": "вода",
         "category": "еда", "level": 3},
        {"word": "plate", "translation": "тарелка",
         "category": "посуда", "level": 3},
        {"word": "fork", "translation": "вилка",
         "category": "посуда", "level": 3},
        {"word": "knife", "translation": "нож",
         "category": "посуда", "level": 3},
        {"word": "spoon", "translation": "ложка",
         "category": "посуда", "level": 3},
        {"word": "chair", "translation": "стул",
         "category": "мебель", "level": 3},
        {"word": "table", "translation": "стол",
         "category": "мебель", "level": 3},
        {"word": "bed", "translation": "кровать",
         "category": "мебель", "level": 3},
        {"word": "sofa", "translation": "диван",
         "category": "мебель", "level": 3},
    ]

    session = SessionLocal()
    try:
        for word_data in default_words:
            word = Word(**word_data)
            session.add(word)
        session.commit()
        print("Стандартные слова успешно добавлены")
    except IntegrityError:
        session.rollback()
        print("Слова уже существуют в базе данных")
    finally:
        session.close()


def load_standard_words_for_user(user_id: int) -> None:
    """Добавляет стандартные слова для конкретного пользователя.

    Args:
        user_id: Идентификатор пользователя
    """
    session = SessionLocal()
    try:
        standard_words = session.query(Word).all()
        for word in standard_words:
            existing_word = session.query(UserWord).filter_by(
                user_id=user_id,
                word=word.word.lower(),
                translation=word.translation.lower(),
                category=word.category.lower(),
                level=word.level,
                is_custom=False,
            ).first()

            if not existing_word:
                new_word = UserWord(
                    user_id=user_id,
                    word=word.word.lower(),
                    translation=word.translation.lower(),
                    category=word.category.lower(),
                    level=word.level,
                    is_custom=False,
                )
                session.add(new_word)
        session.commit()
        print(f"Стандартные слова загружены для пользователя {user_id}")
    except IntegrityError:
        session.rollback()
        print("Ошибка при загрузке стандартных слов")
    finally:
        session.close()


if __name__ == "__main__":
    # Создание БД при необходимости
    create_database_if_not_exists()

    try:
        # Проверка подключения и инициализация структуры
        with engine.connect() as connection:
            print("Успешное подключение к базе данных.")

        init_db()
        populate_default_words()

    except OperationalError:
        print("Не удалось подключиться к базе данных.")
