"""
topics.py — «Темы»: карточки всех тем экзамена с прогрессом и кнопкой тренировки.
Здесь можно учить любую тему сразу, не дожидаясь её на пути.
"""

import streamlit as st

import lesson
import progress
import themen
import ui
from screens import common


def topic_stats(topic_words, progress_data):
    """Цифры по теме: (выучено, начато, ждут повторения, точность или None)."""
    learned = 0
    started = 0
    for word in topic_words:
        if progress.is_learned(word, progress_data):
            learned += 1
        if not lesson.is_new(word, progress_data):
            started += 1
    due = lesson.count_review_due(topic_words, progress_data)
    correct, total = progress.accuracy(topic_words, progress_data, progress.MODES)
    accuracy = correct / total if total else None
    return learned, started, due, accuracy


def render(words, progress_data):
    topics = themen.ordered_topics(words)
    total_learned = sum(1 for word in words if progress.is_learned(word, progress_data))
    ui.show(f'<div class="hero"><div><h1>🧭 Темы экзамена</h1>'
            f'<p>В Goethe A2 все задания крутятся вокруг этих тем. Учи любую в любом порядке.</p></div>'
            f'<div class="hero-right"><span class="pill">📚 {len(topics)} тем</span>'
            f'<span class="pill">✅ {total_learned} / {len(words)} слов</span></div></div>')

    columns = st.columns(3, gap="medium")
    for number, thema in enumerate(topics):
        info = themen.info(thema)
        topic_words = themen.words_of_topic(words, thema)
        learned, started, due, accuracy = topic_stats(topic_words, progress_data)
        accuracy_text = f"{round(accuracy * 100)}%" if accuracy is not None else "—"

        with columns[number % 3]:
            ui.show(
                f'<div class="topic-card" style="--c:{info["color"]}"><div class="head">'
                f'<div class="emoji">{info["emoji"]}</div><div><div class="name">{ui.esc(info["name"])}</div>'
                f'<div class="ru">{ui.esc(info["ru"])}</div></div></div>'
                f'<div style="margin-top:12px">{ui.bar(learned / len(topic_words), info["color"], 12)}</div>'
                f'<div class="nums"><span>✅ {learned}/{len(topic_words)} выучено</span>'
                f'<span>👀 {started} начато</span><span>🔁 {due}</span><span>🎯 {accuracy_text}</span></div></div>'
            )
            col_a, col_b = st.columns([1.3, 1])
            with col_a:
                if st.button("▶ Учить", key=f"topic-{number}", type="primary", width="stretch"):
                    common.start_lesson({"type": "topic", "thema": thema}, words, progress_data)
            with col_b:
                with st.popover("📖 Слова", width="stretch"):
                    for word in topic_words:
                        box = progress.get_card(progress_data, word, "ru_de")["box"]
                        mark = "✅" if progress.is_learned(word, progress_data) else ("🆕" if lesson.is_new(word, progress_data) else f"📦{box}")
                        ui.show(f'{mark} <b>{ui.article_html(word)}</b> — {ui.esc(word["russian"])}')
            st.write("")
