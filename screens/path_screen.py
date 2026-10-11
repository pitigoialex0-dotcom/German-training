"""
path_screen.py — «Путь»: разделы по темам экзамена и станции-кружки зигзагом.

🟡 жёлтый кружок — станция пройдена (под ним звёзды),
🟣 фиолетовый пульсирующий — текущая станция,
⚪ серый — закрыта, откроется после предыдущей.
"""

import streamlit as st

import path
import progress
import themen
import ui
from screens import common

# Смещение кружков по колонкам, чтобы путь шёл «змейкой» (7 колонок, середина — 3)
ZIGZAG = [3, 4, 5, 4, 3, 2, 1, 2]


def render(words, progress_data):
    units = path.build_path(words)
    states = path.station_states(units, progress_data)
    current = path.current_station(units, progress_data)
    stations = path.all_stations(units)
    passed = sum(1 for state in states.values() if state == "done")

    ui.show(f'<div class="hero"><div><h1>🗺️ Путь к Goethe A2</h1>'
            f'<p>{len(units)} разделов по темам экзамена. Проходи станции по порядку — '
            f'каждая открывает следующую.</p>'
            f'<div class="level-bar"><small>Пройдено станций: {passed} из {len(stations)}</small>'
            f'{ui.bar(passed / len(stations) if stations else 0, "#FDE047", 14)}</div></div>'
            f'<div class="hero-right"><span class="pill">⭐ {progress.total_stars(progress_data)}</span>'
            f'<span class="pill">🏆 {checkpoints_passed(units, states)} чекпоинтов</span></div></div>')

    left, right = st.columns([3, 2], gap="large")
    with right:
        side_panel(units, current, words, progress_data)
    with left:
        for number, unit in enumerate(units, start=1):
            done, total = path.unit_progress(unit, states)
            info = unit["info"]
            has_current = current is not None and current["thema"] == unit["thema"]
            label = f'{info["emoji"]} Раздел {number}: {info["name"]} — {done}/{total}'
            if done == total:
                label += " ✅"
            with st.expander(label, expanded=has_current):
                ui.show(f'<div class="unit-banner" style="--c:{info["color"]}"><div>'
                        f'<div class="small">Раздел {number}</div>'
                        f'<div class="title">{info["emoji"]} {ui.esc(info["name"])}</div>'
                        f'<div>{ui.esc(info["ru"])}</div></div>'
                        f'<div class="count">{done} / {total}</div></div>')
                draw_stations(number, unit, states, words, progress_data)


def draw_stations(unit_number, unit, states, words, progress_data):
    """Кружки станций зигзагом. Каждый кружок — кнопка Streamlit, раскрашенная через CSS."""
    for index, station in enumerate(unit["stations"]):
        state = states[station["id"]]
        columns = st.columns(7)
        with columns[ZIGZAG[index % len(ZIGZAG)]]:
            if state == "current":
                ui.show('<div class="start-bubble">СТАРТ</div>')
            # Ключ кнопки начинается с node-done / node-current / node-locked — по нему CSS красит кружок
            clicked = st.button(station["icon"], key=f"node-{state}-{unit_number}-{index}",
                                help=station["title"], disabled=state == "locked")
            stars = path.stars_text(progress_data, station) if state == "done" else ""
            ui.show(f'<div class="node-label">{station["title"]}<br><span class="stars">{stars}</span></div>')
        if clicked:
            common.start_lesson({"type": "station", "id": station["id"]}, words, progress_data)


def side_panel(units, current, words, progress_data):
    """Правая колонка: текущая станция, легенда, как это работает."""
    if current is None:
        ui.show('<div class="card card-accent" style="--c:#F59E0B"><div class="big-emoji">🏁</div>'
                '<h3>Путь пройден!</h3><div class="muted">Повторяй слова и проходи станции заново на 3 звезды.</div></div>')
    else:
        info = themen.info(current["thema"])
        names = ", ".join(current["keys"][:5]) + ("…" if len(current["keys"]) > 5 else "")
        ui.show(f'<div class="card card-accent" style="--c:{info["color"]}">'
                f'<div class="muted">Следующая станция</div>'
                f'<h3>{current["icon"]} {ui.esc(info["name"])} · {current["title"]}</h3>'
                f'<div class="muted">{ui.esc(names)}</div></div>')
        if st.button("▶ Начать станцию", type="primary", width="stretch", key="path-start"):
            common.start_lesson({"type": "station", "id": current["id"]}, words, progress_data)

    ui.show('<div class="card"><h3>Как устроен путь</h3>'
            '<div>📘 <b>Слова</b> — по 6–8 новых слов: знакомство → выбор → написать самому</div>'
            '<div>🎯 <b>Артикли</b> — der / die / das для существительных темы</div>'
            '<div>⏪ <b>Perfekt</b> — прошедшее время глаголов (нужно для Schreiben и Sprechen)</div>'
            '<div>🏆 <b>Чекпоинт</b> — смешанный тест по теме, нужно 80%</div>'
            '<div class="muted" style="margin-top:8px">Станция засчитывается от 60% ответов с первой попытки. '
            '⭐ 60% · ⭐⭐ 80% · ⭐⭐⭐ без ошибок. Пройденные станции можно проходить заново.</div></div>')


def checkpoints_passed(units, states):
    """Сколько чекпоинтов пройдено."""
    count = 0
    for station in path.all_stations(units):
        if station["kind"] == "checkpoint" and states[station["id"]] == "done":
            count += 1
    return count
