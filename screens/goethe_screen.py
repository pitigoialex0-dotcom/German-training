"""
goethe_screen.py — подготовка к Goethe-Zertifikat A2: формат экзамена, отсчёт дней,
готовность, тренажёры Schreiben, Sprechen, Hören и полезные фразы (Redemittel).
"""

import random
import re

import streamlit as st

import goethe
import progress
import themen
import ui
from screens import common

MODULE_COLORS = ["#3B82F6", "#14B8A6", "#EC4899", "#F59E0B", "#8B5CF6"]
XP_SCHREIBEN = 20
XP_SPRECHEN = 5

GREETINGS = ["liebe", "lieber", "hallo", "hi", "sehr geehrte", "sehr geehrter", "guten tag"]
CLOSINGS = ["grüße", "gruesse", "gruß", "gruss", "bis bald", "bis dann", "tschüss", "tschuess", "dein", "deine"]


def render(words, progress_data):
    content = goethe.load_content()
    days = goethe.days_until_exam(progress_data)
    parts, overall = goethe.readiness(words, progress_data, content)

    if days is None:
        countdown = '<span class="pill">📅 дата экзамена не задана</span>'
    elif days >= 0:
        countdown = f'<span class="pill">📅 {days} дн. до экзамена</span>'
    else:
        countdown = '<span class="pill">📅 экзамен уже прошёл</span>'
    ui.show(f'<div class="hero"><div><h1>🎓 Goethe-Zertifikat A2</h1>'
            f'<p>Формат экзамена, тренажёры письма и устной части, диктанты и готовые фразы.</p></div>'
            f'<div class="hero-right">{countdown}<span class="pill">🎯 готовность {round(overall * 100)}%</span></div></div>')

    tabs = st.tabs(["📋 Экзамен", "✍️ Schreiben", "🗣️ Sprechen", "🎧 Hören", "💬 Redemittel"])
    with tabs[0]:
        exam_tab(content, parts, overall, days, words, progress_data)
    with tabs[1]:
        schreiben_tab(content, progress_data)
    with tabs[2]:
        sprechen_tab(content, progress_data)
    with tabs[3]:
        hoeren_tab(words, progress_data)
    with tabs[4]:
        redemittel_tab(content)


# ---------------------------------------------------------------
# Экзамен
# ---------------------------------------------------------------

def exam_tab(content, parts, overall, days, words, progress_data):
    info = content["exam_info"]
    left, right = st.columns([2, 1], gap="large")

    with left:
        modules = info.get("modules", [])
        columns = st.columns(2, gap="medium")
        for number, module in enumerate(modules):
            items = "".join(f'<li><b>{ui.esc(part["teil"])}:</b> {ui.esc(part["description_ru"])}</li>'
                            for part in module["parts"])
            tips = "".join(f"<li>{ui.esc(tip)}</li>" for tip in module["tips_ru"])
            with columns[number % 2]:
                ui.show(f'<div class="module-card" style="--c:{MODULE_COLORS[number % len(MODULE_COLORS)]}">'
                        f'<div class="t">{ui.esc(module["name_de"])} · {ui.esc(module["name_ru"])}</div>'
                        f'<div class="muted">⏱ {ui.esc(module["minutes"])}</div><ul>{items}</ul>'
                        f'<div class="muted" style="margin-top:8px">💡 Советы</div><ul>{tips}</ul></div>')
        if info.get("scoring_ru"):
            ui.show(f'<div class="card"><h3>📊 Как оценивают</h3>{ui.esc(info["scoring_ru"])}</div>')
        if info.get("sources"):
            with st.expander("📚 Источники и что не удалось проверить"):
                if info.get("method_note"):
                    st.write(info["method_note"])
                for url in info["sources"]:
                    ui.show(f'<a href="{ui.esc(url)}" target="_blank">{ui.esc(short_url(url))}</a>')
                if info.get("uncertain"):
                    st.markdown("**Не подтверждено официально:**")
                    for item in info["uncertain"]:
                        st.markdown(f"- {item}")

    with right:
        if days is None:
            ui.show('<div class="card card-accent" style="--c:#EC4899"><div class="muted">Дата экзамена</div>'
                    '<h3>Не задана</h3><div class="muted">Укажи её на главной в «⚙️ Настройки» — '
                    'появится отсчёт и план слов в день.</div></div>')
        else:
            per_day = goethe.words_per_day_needed(words, progress_data)
            plan = f"Чтобы успеть выучить все слова, осваивай ~<b>{per_day}</b> слов в день." if per_day else ""
            ui.show(f'<div class="card card-accent" style="--c:#EC4899"><div class="muted">До экзамена</div>'
                    f'<div class="countdown">{max(days, 0)}</div><div class="muted">дней</div>'
                    f'<div style="margin-top:8px">{plan}</div></div>')

        rows = "".join(f'<div class="ready-row" style="grid-template-columns: 120px 1fr 46px"><span>{name}</span>'
                       f'{ui.bar(value, "#7C3AED", 12)}<span class="pct">{round(value * 100)}%</span></div>'
                       for name, value in parts.items())
        ui.show(f'<div class="card"><h3>Готовность: {round(overall * 100)}%</h3>{rows}'
                f'<div class="muted">Оценка по твоей практике в приложении, не прогноз баллов. '
                f'Lesen здесь не тренируется — для него реши официальный пробный тест (Übungssatz) на goethe.de.</div></div>')

        topics = info.get("official_topics", [])
        if topics:
            chips = "".join(ui.chip(topic, "#7C3AED") for topic in topics)
            note = f'<div class="muted" style="margin-top:6px">{ui.esc(info.get("topics_note", ""))}</div>'
            ui.show(f'<div class="card"><h3>Темы экзамена</h3>{chips}{note}</div>')


def short_url(url):
    """'https://www.goethe.de/de/spr/kup/prf/prf/gzsd2.html' → 'goethe.de/…/gzsd2.html'."""
    url = re.sub(r"^https?://(www\.)?", "", url)
    pieces = url.split("/")
    if len(pieces) > 2:
        return pieces[0] + "/…/" + pieces[-1]
    return url


# ---------------------------------------------------------------
# Schreiben
# ---------------------------------------------------------------

def schreiben_tab(content, progress_data):
    tasks = content["schreiben"]
    if not tasks:
        st.info("Задания Schreiben не найдены (data/goethe_a2.json).")
        return
    done_ids = progress_data["exam"]["schreiben_done"]

    def label(number):
        task = tasks[number]
        mark = "✅ " if goethe.schreiben_id(number) in done_ids else ""
        return f'{mark}Teil {task["teil"]} · {themen.info(task["thema"])["emoji"]} {task["thema"]}'

    left, right = st.columns([1.4, 1], gap="large")
    with left:
        number = st.selectbox("Задание", range(len(tasks)), format_func=label)
        task = tasks[number]
        points = "".join(f"<li>{ui.esc(point)}</li>" for point in task["punkte"])
        ui.show(f'<div class="card card-accent" style="--c:#EC4899">'
                f'<div class="muted">Teil {task["teil"]} · {task["min_words"]}–{task["max_words"]} слов</div>'
                f'<div style="margin:6px 0"><b>Ситуация:</b> {ui.esc(task["situation_ru"])}</div>'
                f'<div style="font-size:1.08rem">{ui.esc(task["aufgabe_de"])}</div><ul>{points}</ul></div>')
        text = st.text_area("Твой текст", height=220, key=f"schreiben-text-{number}",
                            placeholder="Liebe …,\n\n…\n\nViele Grüße\n…")

    with right:
        word_count = len(re.findall(r"[A-Za-zÄÖÜäöüß]+", text))
        lower = text.lower()
        in_range = task["min_words"] <= word_count <= task["max_words"]
        has_greeting = any(lower.strip().startswith(g) or ("\n" + g) in lower for g in GREETINGS)
        has_closing = any(c in lower for c in CLOSINGS)
        checks = [
            (in_range, f"Слов: {word_count} (нужно {task['min_words']}–{task['max_words']})"),
            (has_greeting, "Есть обращение (Liebe/Lieber/Hallo/Sehr geehrte…)"),
            (has_closing, "Есть завершение (Viele Grüße / Bis bald…)"),
        ]
        rows = "".join(f'<div>{"✅" if ok else "⬜"} {ui.esc(label_text)}</div>' for ok, label_text in checks)
        ui.show(f'<div class="card"><h3>🔎 Автопроверка</h3>{rows}'
                f'<div class="muted" style="margin-top:8px">Проверь сам, раскрыты ли все пункты:</div></div>')
        all_points = True
        for index, point in enumerate(task["punkte"]):
            if not st.checkbox(point, key=f"schreiben-point-{number}-{index}"):
                all_points = False

        if st.toggle("👀 Показать образец", key=f"schreiben-show-{number}"):
            ui.show(f'<div class="word-info"><div class="ex" style="white-space:pre-wrap">'
                    f'{ui.esc(task["musterloesung"])}</div></div>')

        task_id = goethe.schreiben_id(number)
        if task_id in done_ids:
            ui.show(ui.result_banner(True, "Задание сделано ✅"))
        elif st.button(f"✅ Готово (+{XP_SCHREIBEN} XP)", type="primary", width="stretch",
                       disabled=not (in_range and all_points), key=f"schreiben-done-{number}"):
            done_ids.append(task_id)
            progress.add_xp(progress_data, XP_SCHREIBEN)
            progress.save_progress(progress_data)
            st.balloons()
            st.rerun()

        email_phrases = [p for p in content["redemittel"] if p["kategorie"].startswith("E-Mail")]
        if email_phrases:
            with st.expander("💬 Фразы для письма"):
                for phrase in email_phrases:
                    ui.show(f'<b>{ui.esc(phrase["deutsch"])}</b> — {ui.esc(phrase["russisch"])}')


# ---------------------------------------------------------------
# Sprechen
# ---------------------------------------------------------------

def sprechen_done(progress_data):
    """Отмечает проработанную карточку устной части."""
    progress_data["exam"]["sprechen_done"] += 1
    progress.add_xp(progress_data, XP_SPRECHEN)
    progress.save_progress(progress_data)


def sprechen_tab(content, progress_data):
    ui.show(f'<div class="muted">Проработано карточек: <b>{progress_data["exam"]["sprechen_done"]}</b>. '
            f'Говори вслух! Сначала ответь сам, потом открой образец и послушай его.</div>')
    teil1, teil2, teil3 = st.tabs(["Teil 1 · вопросы по карточкам", "Teil 2 · о себе", "Teil 3 · договориться"])

    with teil1:
        cards = content["sprechen_teil1"]
        if not cards:
            st.info("Карточки не найдены.")
        else:
            if "sprechen1" not in st.session_state or st.session_state["sprechen1"] >= len(cards):
                st.session_state["sprechen1"] = random.randrange(len(cards))
            card = cards[st.session_state["sprechen1"]]
            info = themen.info(card["thema"])
            left, right = st.columns([1, 1.3], gap="large")
            with left:
                ui.show(f'<div class="q-card" style="--c:{info["color"]}"><div class="q-label">Thema: {ui.esc(card["thema"])}</div>'
                        f'<div class="q-word">{ui.esc(card["wort"])}</div>'
                        f'<div class="q-sub">Задай вопрос с этим словом, потом ответь на него</div></div>')
                if st.button("🎲 Следующая карточка", width="stretch", key="sprechen1-next"):
                    st.session_state["sprechen1"] = random.randrange(len(cards))
                    st.rerun()
            with right:
                ui.show('<div class="card"><div class="muted">💡 Как это работает на экзамене</div>'
                        'У тебя 4 карточки со словами. По каждой задаёшь партнёру вопрос, он отвечает, '
                        'потом наоборот. Пример: <b>Wohnort?</b> → «Wo wohnst du?» — «Ich wohne in Chișinău.»</div>')
                # Ключ зависит от номера карточки: у новой карточки образец снова скрыт
                if st.toggle("👀 Показать образец", key=f'sprechen1-show-{st.session_state["sprechen1"]}'):
                    ui.show(f'<div class="word-info"><div><b>Frage:</b> {ui.esc(card["frage"])}</div>'
                            f'<div><b>Antwort:</b> {ui.esc(card["antwort"])}</div></div>')
                    ui.speak_button(card["frage"] + " " + card["antwort"], "🔊 Послушать")
                    if st.button(f"✅ Проговорил (+{XP_SPRECHEN} XP)", key="sprechen1-done", type="primary"):
                        sprechen_done(progress_data)
                        st.session_state["sprechen1"] = random.randrange(len(cards))
                        st.rerun()

    with teil2:
        cards = content["sprechen_teil2"]
        if not cards:
            st.info("Карточки не найдены.")
        else:
            number = st.selectbox("Тема", range(len(cards)), key="sprechen2-select",
                                  format_func=lambda i: f'{themen.info(cards[i]["thema"])["emoji"]} {cards[i]["thema"]}')
            card = cards[number]
            left, right = st.columns([1, 1.3], gap="large")
            with left:
                points = "".join(f"<li>{ui.esc(point)}</li>" for point in card["stichpunkte"])
                ui.show(f'<div class="card card-accent" style="--c:#8B5CF6"><h3>{ui.esc(card["frage_de"])}</h3>'
                        f'<div class="muted">Расскажи 4–6 предложений, используя пункты:</div><ul>{points}</ul></div>')
            with right:
                if st.toggle("👀 Показать образец", key=f"sprechen2-show-{number}"):
                    ui.show(f'<div class="word-info"><div class="ex">{ui.esc(card["beispiel"])}</div></div>')
                    ui.speak_button(card["beispiel"], "🔊 Послушать")
                    if st.button(f"✅ Проговорил (+{XP_SPRECHEN} XP)", key=f"sprechen2-done-{number}", type="primary"):
                        sprechen_done(progress_data)
                        st.toast("Отлично! +5 XP")
                        st.rerun()

    with teil3:
        cards = content["sprechen_teil3"]
        if not cards:
            st.info("Ситуации не найдены.")
        else:
            number = st.selectbox("Ситуация", range(len(cards)), key="sprechen3-select",
                                  format_func=lambda i: cards[i]["situation_de"][:70])
            card = cards[number]
            left, right = st.columns([1, 1.3], gap="large")
            with left:
                ui.show(f'<div class="card card-accent" style="--c:#14B8A6"><h3>{ui.esc(card["situation_de"])}</h3>'
                        f'<div class="muted">{ui.esc(card["situation_ru"])}</div></div>')
            with right:
                if st.toggle("👀 Показать пример диалога", key=f"sprechen3-show-{number}"):
                    lines = "".join(f"<div>{ui.esc(line)}</div>" for line in card["beispiel_dialog"])
                    ui.show(f'<div class="word-info">{lines}</div>')
                    spoken = " ".join(re.sub(r"^[AB]:\s*", "", line) for line in card["beispiel_dialog"])
                    ui.speak_button(spoken, "🔊 Послушать диалог")
                    if st.button(f"✅ Проговорил (+{XP_SPRECHEN} XP)", key=f"sprechen3-done-{number}", type="primary"):
                        sprechen_done(progress_data)
                        st.toast("Отлично! +5 XP")
                        st.rerun()


# ---------------------------------------------------------------
# Hören
# ---------------------------------------------------------------

def hoeren_tab(words, progress_data):
    correct, total = progress.accuracy(words, progress_data, ["diktat"])
    accuracy = f"{round(correct / total * 100)}%" if total else "—"
    left, right = st.columns([1.3, 1], gap="large")
    with left:
        ui.show(f'<div class="card card-accent" style="--c:#14B8A6"><div class="big-emoji">🎧</div>'
                f'<h3>Диктант по примерам из словаря</h3>'
                f'<div>Браузер читает предложение по-немецки, ты пишешь его. Ошибки подсвечиваются по словам.</div>'
                f'<div class="muted" style="margin-top:6px">Диктантов: <b>{total}</b> · точность: <b>{accuracy}</b></div></div>')
        topic_names = themen.ordered_topics(words)
        topics = st.multiselect("Темы для диктанта", topic_names, placeholder="Все темы", key="hoeren-topics")
        if st.button("▶ Начать диктант", type="primary", key="hoeren-start"):
            common.start_lesson({"type": "practice", "kind": "diktat", "topics": topics}, words, progress_data)
    with right:
        ui.show('<div class="card"><h3>💡 Как готовиться к Hören</h3><ul>'
                '<li>Перед прослушиванием прочитай задание и подчеркни ключевые слова (время, место, цена).</li>'
                '<li>Числа, время и дни недели — самые частые ответы. Тренируй их на слух.</li>'
                '<li>Голос браузера — не настоящий экзамен. Добавь официальные аудио с goethe.de.</li>'
                '</ul></div>')


# ---------------------------------------------------------------
# Redemittel
# ---------------------------------------------------------------

def redemittel_tab(content):
    phrases = content["redemittel"]
    if not phrases:
        st.info("Фразы не найдены.")
        return
    categories = []
    for phrase in phrases:
        if phrase["kategorie"] not in categories:
            categories.append(phrase["kategorie"])

    left, right = st.columns([1, 2], gap="large")
    with left:
        category = st.radio("Категория", categories, key="redemittel-category")
        quiz = st.toggle("🙈 Режим проверки (скрыть немецкий)", key="redemittel-quiz")
    with right:
        for number, phrase in enumerate(p for p in phrases if p["kategorie"] == category):
            col_text, col_audio = st.columns([4, 1.3], vertical_alignment="center")
            with col_text:
                if quiz:
                    ui.show(f'<div class="word-info"><b>{ui.esc(phrase["russisch"])}</b></div>')
                    with st.expander("Показать по-немецки"):
                        ui.show(f'<b>{ui.esc(phrase["deutsch"])}</b>')
                else:
                    ui.show(f'<div class="word-info"><b>{ui.esc(phrase["deutsch"])}</b>'
                            f'<div class="muted">{ui.esc(phrase["russisch"])}</div></div>')
            with col_audio:
                ui.speak_button(phrase["deutsch"], "🔊")
