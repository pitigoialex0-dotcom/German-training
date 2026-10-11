"""
app.py — точка входа приложения. Запуск: streamlit run app.py

ГЛАВНОЕ ПРО STREAMLIT:
при каждом нажатии кнопки весь этот файл выполняется заново, сверху вниз.
Всё, что нужно помнить между нажатиями (текущий урок), хранится в st.session_state.

Что делает этот файл:
1. настраивает страницу и подключает стили (style.css);
2. загружает словарь (words.csv) и прогресс (progress.json);
3. строит меню сверху из страниц (папка screens/);
4. если идёт урок — показывает урок, иначе — выбранную страницу.
"""

import os

import streamlit as st

import progress
import ui
import vocab
from screens import dictionary, goethe_screen, home, lesson_screen, path_screen, practice, stats, topics

WORDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "words.csv")

st.set_page_config(page_title="Deutsch A2", page_icon="🇩🇪", layout="wide")
ui.inject_css()

words, warnings = vocab.load_words(WORDS_FILE)
progress_data = progress.load_progress()

for warning in warnings:
    st.warning(warning)


# Каждая страница — маленькая функция, которая вызывает нужный экран
def page_home():
    home.render(words, progress_data)


def page_path():
    path_screen.render(words, progress_data)


def page_topics():
    topics.render(words, progress_data)


def page_practice():
    practice.render(words, progress_data)


def page_goethe():
    goethe_screen.render(words, progress_data)


def page_stats():
    stats.render(words, progress_data)


def page_dictionary():
    dictionary.render(words, progress_data, WORDS_FILE)


pages = [
    st.Page(page_home, title="Главная", icon="🏠", default=True),
    st.Page(page_path, title="Путь", icon="🗺️", url_path="path"),
    st.Page(page_topics, title="Темы", icon="🧭", url_path="topics"),
    st.Page(page_practice, title="Тренировка", icon="🏋️", url_path="practice"),
    st.Page(page_goethe, title="Goethe A2", icon="🎓", url_path="goethe"),
    st.Page(page_stats, title="Статистика", icon="📊", url_path="stats"),
    st.Page(page_dictionary, title="Словарь", icon="📖", url_path="dictionary"),
]
current_page = st.navigation(pages, position="top")
st.session_state["page_title"] = current_page.title

if not words:
    st.error("Словарь пуст. Добавь слова в words.csv или на странице «Словарь».")
    if current_page.title == "Словарь":
        current_page.run()
    st.stop()

# Урок открыт со страницы X. Если ты ушёл на другую страницу через меню — урок закрываем.
active = st.session_state.get("lesson")
if active is not None and active.get("origin") != current_page.title:
    del st.session_state["lesson"]
    active = None

if active is not None:
    lesson_screen.render(words, progress_data)
else:
    current_page.run()
