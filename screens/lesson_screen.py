"""
lesson_screen.py — экран урока: задание, ответ, результат, итоги.

Состояние урока хранится в st.session_state["lesson"] (см. lesson.py).
Порядок на экране:
  1. если есть результат последнего ответа → показываем его и кнопку «Дальше»;
  2. если урок закончен → экран итогов;
  3. иначе → текущее задание.
"""

import random

import streamlit as st

import checker
import lesson
import progress
import themen
import ui
from screens import common

PRAISE = ["Richtig! 🎉", "Super! 💪", "Sehr gut! ⭐", "Toll! 🙌", "Perfekt! ✨", "Klasse! 🚀"]

TIPS = {
    "intro": "Прочитай слово вслух и запомни артикль по цвету: der — синий, die — красный, das — зелёный.",
    "choice": "Нажимай цифры 1–4 на клавиатуре, чтобы выбрать вариант.",
    "de_ru": "Если вариантов перевода несколько, подойдёт любой.",
    "ru_de": "Существительные пиши с артиклем: der Tisch. ä/ö/ü/ß можно писать как ae/oe/ue/ss.",
    "article": "Клавиши 1, 2, 3 = der, die, das. Слова на -ung, -heit, -keit почти всегда die.",
    "perfekt": "sein — движение и смена состояния (ist gefahren, ist aufgestanden), остальное чаще haben.",
    "diktat": "Это тренировка Hören и Schreiben. Слушай сколько угодно раз, знаки препинания не важны.",
}


def render(words, progress_data):
    current = st.session_state["lesson"]
    by_key = {word["key"]: word for word in words}
    color = current["color"]

    ui.keyboard_shortcuts()
    top_bar(current)

    if current["result"] is not None:
        layout(current, lambda: show_result(current, by_key, progress_data))
    elif current["finished"]:
        show_finish(current, by_key, words, progress_data)
    else:
        task = lesson.current_task(current)
        word = by_key.get(task["key"])
        if word is None:
            # Слово удалили из словаря во время урока — просто пропускаем задание
            lesson.skip_intro(current)
            st.rerun()
        layout(current, lambda: show_task(current, task, word, color, progress_data))


def top_bar(current):
    """Верхняя полоса: выход, прогресс урока, серия правильных ответов, XP."""
    col_exit, col_bar = st.columns([1, 16], vertical_alignment="center")
    with col_exit:
        if st.button("✖", key="exit-lesson", help="Выйти из урока"):
            del st.session_state["lesson"]
            st.rerun()
    with col_bar:
        fraction = current["done"] / current["total"] if current["total"] else 1
        combo = f'<span class="combo">🔥 {current["combo"]}</span>' if current["combo"] >= 2 else ""
        ui.show(f'<div class="lesson-top">{ui.bar(fraction, "#22C55E", 20)}{combo}'
                f'<span class="xp-chip">⚡ {current["xp"]} XP</span></div>')


def layout(current, draw_center):
    """Три колонки: слева — об уроке, в центре — задание, справа — подсказки."""
    left, center, right = st.columns([1, 2.3, 1], gap="large")
    with left:
        remaining = len(current["queue"])
        ui.show(f'<div class="card card-accent" style="--c:{current["color"]}">'
                f'<div class="muted">Урок</div><h3>{ui.esc(current["title"])}</h3>'
                f'<div class="muted">Осталось заданий: <b>{remaining}</b></div>'
                f'<div class="muted">Ошибок: <b>{len(current["mistakes"])}</b> · '
                f'лучшее комбо: <b>{current["best_combo"]}</b></div></div>')
    with center:
        draw_center()
    with right:
        task = lesson.current_task(current)
        kind = current["result"]["task"]["kind"] if current["result"] else (task["kind"] if task else "intro")
        ui.show(f'<div class="card"><div class="muted">💡 Подсказка</div>{TIPS.get(kind, "")}</div>'
                '<div class="card"><div class="muted">⌨️ Клавиатура</div>'
                '<span class="kbd">Enter</span> проверить / дальше<br>'
                '<span class="kbd">1</span>–<span class="kbd">4</span> варианты ответа</div>')


# ---------------------------------------------------------------
# Задание
# ---------------------------------------------------------------

def question_card(label, main_html, sub_html, color):
    ui.show(f'<div class="q-card" style="--c:{color}"><div class="q-label">{label}</div>'
            f'<div class="q-word">{main_html}</div><div class="q-sub">{sub_html}</div></div>')


def show_task(current, task, word, color, progress_data):
    kind = task["kind"]
    title = lesson.TASK_TITLES[kind]
    nonce = f'{task["key"]}-{kind}-{task["tries"]}-{current["done"]}'
    topic = themen.info(themen.topic_of(word))
    chips = ui.chip(f'{topic["emoji"]} {topic["name"]}', topic["color"])
    if task["tries"] > 0:
        chips += ui.chip("🔁 повторяем ошибку", "#F43F5E")

    if kind == "intro":
        question_card("✨ " + title, ui.article_html(word), ui.esc(word["russian"]) + "<br>" + chips, color)
        ui.show(ui.word_info(word, color))
        ui.speak_button(word["key"], "🔊 Послушать", key_hint=nonce)
        if st.button("Понятно, дальше ➡️", type="primary", width="stretch"):
            lesson.skip_intro(current)
            if current["finished"]:
                lesson.finish(current, progress_data)
                progress.save_progress(progress_data)
            st.rerun()
        ui.focus('[data-testid="stBaseButton-primary"]', nonce)
        return

    if kind == "choice":
        question_card(title, ui.article_html(word), chips, color)
        ui.speak_button(word["key"], "🔊 Послушать", key_hint=nonce)
        columns = st.columns(2)
        for number, option in enumerate(task["options"], start=1):
            with columns[(number - 1) % 2]:
                if st.button(f"{number}. {option}", key=f"opt-{number}", width="stretch"):
                    ok = option == word["russian"]
                    result = {"status": "correct" if ok else "wrong", "hint": ""}
                    submit(current, task, word, result, option, progress_data)
        return

    if kind == "article":
        question_card(title, ui.esc(word["german"]), ui.esc(word["russian"]) + "<br>" + chips, color)
        columns = st.columns(3)
        for number, article in enumerate(checker.ARTICLES):
            with columns[number]:
                if st.button(article, key=f"art-{article}", width="stretch"):
                    ok = article == word["article"]
                    result = {"status": "correct" if ok else "wrong", "hint": ""}
                    submit(current, task, word, result, article, progress_data)
        return

    # Задания с вводом текста: de_ru, ru_de, perfekt, diktat
    if kind == "de_ru":
        question_card(title, ui.article_html(word), chips, color)
        ui.speak_button(word["key"], "🔊 Послушать")
        label = "Перевод на русский"
        placeholder = "Пустой ответ = «не знаю»"
    elif kind == "ru_de":
        sub = (ui.esc(word["english"]) + "<br>") if word["english"] else ""
        if word["article"]:
            sub += "<b>существительное — с артиклем</b><br>"
        question_card(title, ui.esc(word["russian"]), sub + chips, color)
        label = "По-немецки"
        placeholder = "например: der Tisch"
    elif kind == "perfekt":
        question_card(title, ui.esc(word["german"]),
                      f'{ui.esc(word["russian"])}<br>er / sie / es <b>___ ___</b><br>{chips}', color)
        label = "Perfekt (вспомогательный глагол + Partizip II)"
        placeholder = "например: hat gemacht / ist gefahren"
    else:  # diktat
        question_card(title, "🎧", "Послушай предложение и напиши его по-немецки<br>" + chips, color)
        ui.speak_button(word["example"], "🔊 Слушать ещё раз", key_hint=nonce)
        label = "Что ты услышал?"
        placeholder = "Напиши предложение"

    with st.form("answer-form", clear_on_submit=True):
        answer_text = st.text_input(label, placeholder=placeholder)
        submitted = st.form_submit_button("Проверить ✔️", type="primary", width="stretch")
    ui.focus('[data-testid="stForm"] input', nonce)

    if submitted:
        if kind == "de_ru":
            result = checker.check_answer(answer_text, word["russian"])
        elif kind == "ru_de":
            result = checker.check_german(answer_text, word)
        elif kind == "perfekt":
            result = checker.check_perfekt(answer_text, word)
        else:
            result = checker.check_sentence(answer_text, word["example"])
        submit(current, task, word, result, answer_text, progress_data)


def submit(current, task, word, result, answer_text, progress_data):
    """Обрабатывает ответ: Лейтнер, XP, сохранение. Потом показываем результат."""
    ok = checker.is_accepted(result)
    kind = task["kind"]
    if kind in progress.MODES:
        article_mistake = result["status"] == "wrong_article" or (kind == "article" and not ok)
        progress.record_answer(progress_data, word, kind, ok, article_mistake)

    result["task"] = dict(task)        # копия задания: в очереди оно может измениться
    xp = lesson.answer(current, ok)
    if xp:
        progress.add_xp(progress_data, xp)
    if current["finished"]:
        lesson.finish(current, progress_data)
    progress.save_progress(progress_data)

    result["ok"] = ok
    result["xp"] = xp
    result["answer"] = answer_text
    result["combo"] = current["combo"]
    result["praise"] = random.choice(PRAISE)
    current["result"] = result
    st.rerun()


# ---------------------------------------------------------------
# Результат ответа
# ---------------------------------------------------------------

def correct_answer_html(kind, word):
    """Правильный ответ для показа после ошибки."""
    if kind in ["de_ru", "choice"]:
        return ui.esc(word["russian"])
    if kind == "perfekt":
        return ui.esc(word["perfekt"])
    if kind == "diktat":
        return ui.esc(word["example"])
    return ui.article_html(word)


def show_result(current, by_key, progress_data):
    result = current["result"]
    task = result["task"]
    kind = task["kind"]
    word = by_key.get(task["key"])
    if word is None:
        current["result"] = None
        st.rerun()

    if result["ok"]:
        body = f"+{result['xp']} XP"
        if result["combo"] >= 3:
            body += f" · 🔥 {result['combo']} подряд!"
        if result["status"] == "typo":
            body += f"<br>Засчитано с опечаткой. Правильно: <b>{correct_answer_html(kind, word)}</b>"
        elif result["hint"]:
            body += f"<br>{ui.esc(result['hint'])}"
        ui.show(ui.result_banner(True, result["praise"], body))
    else:
        body = f"Правильно: <b>{correct_answer_html(kind, word)}</b>"
        if result["answer"].strip():
            body += f"<br>Твой ответ: {ui.esc(result['answer'])}"
        if result["hint"]:
            body += f"<br>{ui.esc(result['hint'])}"
        if len(current["queue"]) > 0 and task["tries"] < lesson.MAX_TRIES:
            body += "<br>🔁 Это задание вернётся в конце урока."
        ui.show(ui.result_banner(False, "Fast! Почти 🙈", body))

    if kind == "diktat" and result["status"] != "correct":
        marked = []
        for original, ok in checker.sentence_diff(result["answer"], word["example"]):
            css_class = "diff-ok" if ok else "diff-bad"
            marked.append(f'<span class="{css_class}">{ui.esc(original)}</span>')
        ui.show('<div class="word-info">' + " ".join(marked) + "</div>")

    ui.show(ui.word_info(word, current["color"]))
    left, right = st.columns(2)
    with left:
        ui.speak_button(word["key"], "🔊 Слово")
    if word["example"]:
        with right:
            ui.speak_button(word["example"], "🔊 Пример")

    nonce = f'{task["key"]}-{kind}-{task["tries"]}-{current["done"]}-result'
    if progress_data["settings"].get("sounds", True):
        ui.play_sound(result["ok"], nonce)

    label = "Итоги урока 🏁" if current["finished"] else "Дальше ➡️"
    if st.button(label, type="primary", width="stretch", key="next-task"):
        current["result"] = None
        st.rerun()
    ui.focus('.st-key-next-task button', nonce)


# ---------------------------------------------------------------
# Итоги урока
# ---------------------------------------------------------------

def show_finish(current, by_key, words, progress_data):
    lesson.finish(current, progress_data)
    progress.save_progress(progress_data)

    accuracy = lesson.accuracy(current)
    stars = current.get("stars", 0)
    if stars == 3:
        trophy, title = "🏆", "Идеально! Ни одной ошибки!"
    elif stars >= 1:
        trophy, title = "🎉", "Урок пройден!"
    else:
        trophy, title = "💪", "Хорошая тренировка — попробуй ещё раз"

    station_note = ""
    if current["station"] is not None:
        need = "80%" if current["station"].endswith("checkpoint") else "60%"
        if (current["station"].endswith("checkpoint") and accuracy >= 0.8) or \
                (not current["station"].endswith("checkpoint") and stars >= 1):
            station_note = ui.result_banner(True, "Станция пройдена! 🗺️", "Следующая станция на пути открыта.")
        else:
            station_note = ui.result_banner(False, "Станция пока не пройдена",
                                            f"Нужно решить с первой попытки хотя бы {need} заданий.")

    left, center, right = st.columns([1, 2.3, 1], gap="large")
    with center:
        ui.show(f'<div class="finish"><div class="trophy">{trophy}</div><h2>{title}</h2>'
                f'<div class="stars-big">{"⭐" * stars}{"☆" * (3 - stars)}</div>'
                f'<div class="muted">{ui.esc(current["title"])}</div></div>')
        ui.show(ui.tiles([
            ui.tile("⚡", f'+{current["xp"]}', "XP за урок", "#7C3AED"),
            ui.tile("🎯", f"{round(accuracy * 100)}%", "с первой попытки", "#22C55E"),
            ui.tile("🔥", current["best_combo"], "лучшее комбо", "#F59E0B"),
            ui.tile("❌", len(current["mistakes"]), "слов с ошибками", "#F43F5E"),
        ], min_width=120))
        ui.show(station_note)

        if stars >= 2 and not current.get("celebrated"):
            st.balloons()
            current["celebrated"] = True

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Продолжить ➡️", type="primary", width="stretch", key="finish-continue"):
                del st.session_state["lesson"]
                st.rerun()
        with col2:
            if st.button("🔁 Ещё раз", width="stretch", key="finish-again"):
                common.start_lesson(current["spec"], words, progress_data)
        ui.focus('.st-key-finish-continue button', "finish-" + current["title"])

    with left:
        ui.show(f'<div class="card"><div class="muted">Всего опыта</div>'
                f'<div class="countdown">{progress_data["xp"]}</div><div class="muted">XP</div></div>')
    with right:
        if current["mistakes"]:
            ui.show('<div class="muted" style="margin-bottom:6px">Повтори эти слова:</div>')
            for key in current["mistakes"][:6]:
                if key in by_key:
                    ui.show(ui.word_info(by_key[key], current["color"]))
