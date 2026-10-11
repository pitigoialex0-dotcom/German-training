"""
home.py — главная страница: опыт и уровень, цель на день, продолжение пути,
повторение, прогресс по темам и готовность к экзамену.
"""

from datetime import date, datetime

import streamlit as st

import goethe
import lesson
import path
import progress
import themen
import ui
from screens import common


def render(words, progress_data):
    content = goethe.load_content()
    units = path.build_path(words)
    states = path.station_states(units, progress_data)
    station = path.current_station(units, progress_data)

    hero(progress_data, states)

    # --- Плитки ---
    goal = progress_data["settings"]["daily_xp"]
    today_xp = progress.xp_on(progress_data, date.today())
    learned = sum(1 for word in words if progress.is_learned(word, progress_data))
    due = lesson.count_review_due(words, progress_data)
    days = goethe.days_until_exam(progress_data)
    exam_value = f"{days} дн." if days is not None and days >= 0 else "—"
    correct, total = progress.accuracy(words, progress_data, progress.MODES)
    accuracy = f"{round(correct / total * 100)}%" if total else "—"
    ui.show(ui.tiles([
        ui.tile("⚡", f"{today_xp} / {goal}", "XP сегодня", "#7C3AED"),
        ui.tile("📚", f"{learned} / {len(words)}", "слов выучено", "#22C55E"),
        ui.tile("🔁", due, "ждут повторения", "#F59E0B"),
        ui.tile("🎯", accuracy, "точность ответов", "#3B82F6"),
        ui.tile("📅", exam_value, "до экзамена", "#EC4899"),
    ]))

    # --- Три карточки действий ---
    col1, col2, col3 = st.columns([1.15, 1, 1.15], gap="medium")
    with col1:
        if station is None:
            ui.show('<div class="card card-accent" style="--c:#F59E0B"><div class="big-emoji">🏁</div>'
                    '<h3>Весь путь пройден!</h3><div class="muted">Повторяй слова и готовься к экзамену.</div></div>')
        else:
            info = themen.info(station["thema"])
            number = path.unit_number(units, station["thema"])
            ui.show(f'<div class="card card-accent" style="--c:{info["color"]}">'
                    f'<div class="muted">Продолжить путь · раздел {number}</div>'
                    f'<h3>{info["emoji"]} {ui.esc(info["name"])}</h3>'
                    f'<div style="font-size:1.15rem;font-weight:800">{station["icon"]} {station["title"]}</div>'
                    f'<div class="muted">{len(station["keys"])} слов · {ui.esc(info["ru"])}</div></div>')
            if st.button("▶ Продолжить путь", type="primary", width="stretch", key="home-continue"):
                common.start_lesson({"type": "station", "id": station["id"]}, words, progress_data)
    with col2:
        ui.show(f'<div class="card card-accent" style="--c:#F59E0B"><div class="muted">Повторение дня</div>'
                f'<h3>🔁 {due} карточек</h3><div class="muted">Интервальное повторение: '
                f'трудные слова чаще, выученные реже.</div></div>')
        if st.button("🔁 Повторить", width="stretch", key="home-review", disabled=due == 0):
            common.start_lesson({"type": "review"}, words, progress_data)
    with col3:
        ui.show(f'<div class="card"><div class="muted">XP за неделю · цель {goal} в день</div>'
                f'{ui.week_chart(progress.last_days_xp(progress_data), goal)}</div>')

    # --- Темы и готовность ---
    col_topics, col_ready = st.columns([1.3, 1], gap="medium")
    with col_topics:
        rows = []
        for thema in themen.ordered_topics(words)[:8]:
            info = themen.info(thema)
            topic_words = themen.words_of_topic(words, thema)
            done = sum(1 for word in topic_words if progress.is_learned(word, progress_data))
            rows.append(f'<div class="ready-row" style="grid-template-columns: 220px 1fr 70px">'
                        f'<span>{info["emoji"]} {ui.esc(info["name"])}</span>'
                        f'{ui.bar(done / len(topic_words), info["color"], 12)}'
                        f'<span class="pct">{done}/{len(topic_words)}</span></div>')
        ui.show('<div class="card"><h3>🧭 Темы</h3><div class="muted">Выучено слов по темам экзамена '
                '(все темы — на странице «Темы»)</div>' + "".join(rows) + "</div>")
    with col_ready:
        parts, overall = goethe.readiness(words, progress_data, content)
        rows = []
        for name, value in parts.items():
            rows.append(f'<div class="ready-row" style="grid-template-columns: 130px 1fr 48px"><span>{name}</span>'
                        f'{ui.bar(value, "#7C3AED", 12)}<span class="pct">{round(value * 100)}%</span></div>')
        ui.show(f'<div class="card"><h3>🎓 Готовность к Goethe A2: {round(overall * 100)}%</h3>'
                f'<div class="muted">Грубая оценка по твоей практике в приложении, а не прогноз баллов.</div>'
                + "".join(rows) + "</div>")

    settings(progress_data)


def hero(progress_data, states):
    """Большой цветной баннер наверху."""
    xp = progress_data["xp"]
    level, inside, needed = progress.level_info(xp)
    streak = progress.streak(progress_data)
    passed = sum(1 for state in states.values() if state == "done")
    hour = datetime.now().hour
    if hour < 11:
        greeting = "Guten Morgen! ☀️"
    elif hour < 18:
        greeting = "Guten Tag! 👋"
    else:
        greeting = "Guten Abend! 🌙"
    ui.show(
        f'<div class="hero"><div><h1>{greeting}</h1>'
        f'<p>Цель — Goethe-Zertifikat A2. Каждый урок — шаг к экзамену.</p>'
        f'<div class="level-bar"><small>Уровень {level} · {inside} / {needed} XP до уровня {level + 1}</small>'
        f'{ui.bar(inside / needed, "#FDE047", 14)}</div></div>'
        f'<div class="hero-right"><span class="pill">🔥 {streak} дн.</span>'
        f'<span class="pill">⚡ {xp} XP</span><span class="pill">⭐ {progress.total_stars(progress_data)}</span>'
        f'<span class="pill">🗺️ {passed}/{len(states)}</span></div></div>'
    )


def settings(progress_data):
    """Настройки: цель на день, дата экзамена, звуки."""
    with st.expander("⚙️ Настройки"):
        col1, col2, col3 = st.columns(3)
        with col1:
            options = [20, 30, 50, 100, 150]
            current = progress_data["settings"]["daily_xp"]
            goal = st.select_slider("Цель XP в день", options=options,
                                    value=current if current in options else 50)
        with col2:
            saved = progress_data["exam"]["date"]
            value = date.fromisoformat(saved) if saved else None
            exam_date = st.date_input("Дата экзамена Goethe A2", value=value, format="DD.MM.YYYY")
        with col3:
            sounds = st.toggle("Звуки в уроках", value=progress_data["settings"]["sounds"])

        new_date = exam_date.isoformat() if exam_date else ""
        if (goal, new_date, sounds) != (current, saved, progress_data["settings"]["sounds"]):
            progress_data["settings"]["daily_xp"] = goal
            progress_data["exam"]["date"] = new_date
            progress_data["settings"]["sounds"] = sounds
            progress.save_progress(progress_data)
            st.rerun()
