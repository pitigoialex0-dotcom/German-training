"""
common.py — то, что нужно нескольким экранам: запуск урока.

Урок описывается «спецификацией» (spec) — маленьким словарем, по которому
урок можно собрать заново (например, для кнопки «Ещё раз»):
  {"type": "station", "id": "Wohnen|words|1"}       — станция пути
  {"type": "topic", "thema": "Wohnen"}                — тренировка темы
  {"type": "practice", "kind": "article", "topics": [...], "lessons": [...]}
  {"type": "review"}                                  — повторение дня
"""

import streamlit as st

import lesson
import path
import themen
import vocab


def build(spec, words, progress_data):
    """Собирает урок по спецификации. Возвращает словарь урока."""
    if spec["type"] == "station":
        units = path.build_path(words)
        station = path.find_station(units, spec["id"])
        if station is None:
            return None
        info = themen.info(station["thema"])
        new = lesson.build_station_lesson(station, words, progress_data)
        new["title"] = f"{info['emoji']} {info['name']} · {station['icon']} {station['title']}"
        new["color"] = info["color"]
        new["thema"] = station["thema"]
    elif spec["type"] == "topic":
        info = themen.info(spec["thema"])
        topic_words = themen.words_of_topic(words, spec["thema"])
        new = lesson.build_topic_lesson(f"{info['emoji']} {info['name']}", topic_words, words, progress_data)
        new["color"] = info["color"]
        new["thema"] = spec["thema"]
    elif spec["type"] == "practice":
        selected = vocab.filter_by_topics(words, spec.get("topics", []))
        selected = vocab.filter_by_lessons(selected, spec.get("lessons", []))
        new = lesson.build_practice_lesson(spec["kind"], selected, progress_data)
    else:
        new = lesson.build_review_lesson(words, progress_data)
    new["spec"] = spec
    return new


def start_lesson(spec, words, progress_data):
    """Создаёт урок и запоминает его в st.session_state — app.py покажет экран урока."""
    new = build(spec, words, progress_data)
    if new is None or not new["queue"]:
        st.toast("Для этого урока пока нет заданий 🤷")
        return
    new["origin"] = st.session_state.get("page_title", "")
    st.session_state["lesson"] = new
    st.rerun()
