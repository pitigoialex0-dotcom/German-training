"""
stats.py — «Статистика»: опыт, точность по режимам, темы, коробки Лейтнера, трудные слова.
"""

import streamlit as st

import lesson
import progress
import themen
import ui

MODE_NAMES = {
    "de_ru": "🃏 DE → RU",
    "ru_de": "✍️ RU → DE",
    "article": "🎯 Артикли",
    "perfekt": "⏪ Perfekt",
    "diktat": "🎧 Диктант",
}


def percent(correct, total):
    if total == 0:
        return "—"
    return f"{round(correct / total * 100)}%"


def render(words, progress_data):
    xp = progress_data["xp"]
    level, inside, needed = progress.level_info(xp)
    learned = sum(1 for word in words if progress.is_learned(word, progress_data))
    correct, total = progress.accuracy(words, progress_data, progress.MODES)

    ui.show(f'<div class="hero"><div><h1>📊 Статистика</h1>'
            f'<p>Уровень {level} · {inside}/{needed} XP до следующего</p>'
            f'<div class="level-bar">{ui.bar(inside / needed, "#FDE047", 14)}</div></div>'
            f'<div class="hero-right"><span class="pill">⚡ {xp} XP</span>'
            f'<span class="pill">🔥 {progress.streak(progress_data)} дн.</span></div></div>')

    ui.show(ui.tiles([
        ui.tile("📚", f"{learned} / {len(words)}", "слов выучено", "#22C55E"),
        ui.tile("🎯", percent(correct, total), f"верно из {total} ответов", "#3B82F6"),
        ui.tile("⭐", progress.total_stars(progress_data), "звёзд на пути", "#F59E0B"),
        ui.tile("✍️", len(progress_data["exam"]["schreiben_done"]), "писем Schreiben", "#EC4899"),
        ui.tile("🗣️", progress_data["exam"]["sprechen_done"], "карточек Sprechen", "#8B5CF6"),
    ]))

    left, right = st.columns([1.2, 1], gap="large")
    with left:
        # --- Точность по режимам ---
        rows = []
        for mode, name in MODE_NAMES.items():
            mode_correct, mode_total = progress.accuracy(words, progress_data, [mode])
            value = mode_correct / mode_total if mode_total else 0
            rows.append(f'<div class="ready-row" style="grid-template-columns: 140px 1fr 110px"><span>{name}</span>'
                        f'{ui.bar(value, "#7C3AED", 12)}'
                        f'<span class="pct">{percent(mode_correct, mode_total)} ({mode_total})</span></div>')
        ui.show('<div class="card"><h3>🎯 Точность по режимам</h3>' + "".join(rows) + "</div>")

        # --- Темы ---
        table = []
        for thema in themen.ordered_topics(words):
            info = themen.info(thema)
            topic_words = themen.words_of_topic(words, thema)
            topic_learned = sum(1 for word in topic_words if progress.is_learned(word, progress_data))
            topic_correct, topic_total = progress.accuracy(topic_words, progress_data, progress.MODES)
            table.append({
                "Тема": f'{info["emoji"]} {thema}',
                "Выучено": topic_learned / len(topic_words),
                "Слов": len(topic_words),
                "Точность": topic_correct / topic_total if topic_total else None,
                "К повторению": lesson.count_review_due(topic_words, progress_data),
            })
        st.subheader("🧭 Темы")
        st.dataframe(table, hide_index=True, width="stretch", column_config={
            "Выучено": st.column_config.ProgressColumn("Выучено", format="percent", min_value=0, max_value=1),
            "Точность": st.column_config.ProgressColumn("Точность", format="percent", min_value=0, max_value=1),
        })

    with right:
        goal = progress_data["settings"]["daily_xp"]
        ui.show(f'<div class="card"><h3>⚡ XP за 2 недели</h3>'
                f'{ui.week_chart(progress.last_days_xp(progress_data, 14), goal)}</div>')

        mode = st.radio("📦 Коробки Лейтнера", list(MODE_NAMES.keys()), format_func=MODE_NAMES.get, horizontal=True)
        counts = progress.box_counts(words, progress_data, mode)
        colors = ["#94A3B8", "#F43F5E", "#F97316", "#F59E0B", "#84CC16", "#22C55E"]
        labels = ["новые", 1, 2, 3, 4, 5]
        ui.show(ui.tiles([ui.tile("📦" if label != "новые" else "🆕", counts[label],
                                  "новые" if label == "новые" else f"коробка {label}", colors[i])
                          for i, label in enumerate(labels)]))

    st.subheader("😈 Топ-10 трудных слов")
    rows = progress.mistakes_table(words, progress_data)
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.write("Ошибок пока нет. Или ты ещё не начинал 😉")

    with st.expander("⚠️ Сбросить весь прогресс"):
        sure = st.checkbox("Да, я хочу удалить весь прогресс (XP, звёзды, коробки)")
        if st.button("Удалить прогресс", disabled=not sure):
            progress.reset_progress()
            st.session_state.clear()
            st.rerun()
