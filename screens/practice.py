"""
practice.py — «Тренировка»: свободные уроки одного вида с фильтром по темам и урокам Menschen.
"""

import streamlit as st

import lesson
import themen
import ui
import vocab
from screens import common

# Виды тренировки: (kind, иконка, название, описание, цвет)
MODES = [
    ("de_ru", "🃏", "Немецкий → русский", "Узнаёшь слово и пишешь перевод. Основа для Lesen и Hören.", "#7C3AED"),
    ("ru_de", "✍️", "Русский → немецкий", "Вспоминаешь слово сам, с артиклем. Нужно для Schreiben и Sprechen.", "#EC4899"),
    ("article", "🎯", "Артикли", "der / die / das. Ошибки в артиклях считаются отдельно.", "#2563EB"),
    ("perfekt", "⏪", "Perfekt", "hat gemacht / ist gefahren — главное время для рассказа о прошлом на A2.", "#F59E0B"),
    ("diktat", "🎧", "Диктант", "Слушаешь предложение и пишешь его. Тренирует Hören и орфографию.", "#14B8A6"),
    ("mix", "🎲", "Микс", "Всё вперемешку — как в чекпоинте.", "#22C55E"),
]


def available(kind, words):
    """Сколько слов подходит для тренировки этого вида."""
    if kind == "article":
        return len([word for word in words if vocab.is_noun(word)])
    if kind == "perfekt":
        return len([word for word in words if vocab.is_verb_with_perfekt(word)])
    if kind == "diktat":
        return len([word for word in words if word["example"]])
    return len(words)


def render(words, progress_data):
    due = lesson.count_review_due(words, progress_data)
    ui.show(f'<div class="hero"><div><h1>🏋️ Тренировка</h1>'
            f'<p>Свободные уроки по 15 заданий. Сначала самые трудные и те, что пора повторить.</p></div>'
            f'<div class="hero-right"><span class="pill">🔁 {due} к повторению</span></div></div>')

    col_topics, col_lessons = st.columns([2, 1])
    with col_topics:
        topic_names = themen.ordered_topics(words)
        topics = ui.remembered_multiselect("Темы", topic_names, "saved-practice-topics", placeholder="Все темы",
                                           format_func=lambda name: f'{themen.info(name)["emoji"]} {name}')
    with col_lessons:
        lessons = ui.remembered_multiselect("Lektion (Menschen)", vocab.get_lessons(words), "saved-practice-lessons",
                                            placeholder="Все уроки")
    selected = vocab.filter_by_lessons(vocab.filter_by_topics(words, topics), lessons)
    st.caption(f"Выбрано слов: {len(selected)}")

    # Повторение дня — отдельной широкой карточкой
    ui.show(f'<div class="card card-accent" style="--c:#F59E0B"><h3>🔁 Повторение дня — {due} карточек</h3>'
            f'<div class="muted">Система Лейтнера: всё, что пора повторить сегодня, во всех режимах.</div></div>')
    if st.button("🔁 Начать повторение", key="practice-review", disabled=due == 0, type="primary"):
        common.start_lesson({"type": "review"}, words, progress_data)

    columns = st.columns(3, gap="medium")
    for number, (kind, icon, title, description, color) in enumerate(MODES):
        count = available(kind, selected)
        with columns[number % 3]:
            ui.show(f'<div class="card card-accent" style="--c:{color}; min-height:150px">'
                    f'<div class="big-emoji">{icon}</div><h3>{title}</h3>'
                    f'<div class="muted">{description}</div><div class="muted">Доступно слов: <b>{count}</b></div></div>')
            if st.button(f"▶ {title}", key=f"practice-{kind}", width="stretch", disabled=count == 0):
                spec = {"type": "practice", "kind": kind, "topics": topics, "lessons": lessons}
                common.start_lesson(spec, words, progress_data)
