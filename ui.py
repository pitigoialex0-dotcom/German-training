"""
ui.py — готовые «кирпичики» интерфейса: баннеры, плитки, полоски, карточки, звук, озвучка.

Большинство функций возвращают кусок HTML (строку), а функция show() выводит его
на страницу. Внешний вид задаётся классами из style.css (например, class="tile").

html.escape() превращает символы < > & в безопасный вид, чтобы текст из CSV-файла
не мог случайно сломать разметку страницы.
"""

import html
import json
import os

import streamlit as st
import streamlit.components.v1 as components

STYLE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style.css")

ARTICLE_COLORS = {"der": "#2563EB", "die": "#E11D48", "das": "#16A34A"}


def inject_css():
    """Подключает style.css ко всей странице."""
    with open(STYLE_FILE, encoding="utf-8") as f:
        css = f.read()
    st.html(f"<style>{css}</style>")


def show(markup):
    """Выводит HTML на страницу."""
    st.markdown(markup, unsafe_allow_html=True)


def esc(text):
    """Короткое имя для html.escape."""
    return html.escape(str(text))


# ---------------------------------------------------------------
# Строительные блоки (возвращают HTML-строку)
# ---------------------------------------------------------------

def bar(fraction, color="#7C3AED", height=14):
    """Полоска прогресса. fraction — от 0 до 1."""
    percent = max(0, min(100, round(fraction * 100)))
    return (f'<div class="bar" style="--h:{height}px">'
            f'<div style="width:{percent}%; --c:{color}; background:{color}"></div></div>')


def tile(icon, value, label, color="#7C3AED"):
    """Плитка со значением: иконка, большое число, подпись."""
    return (f'<div class="tile" style="--c:{color}"><div class="icon">{icon}</div>'
            f'<div class="value">{esc(value)}</div><div class="label">{esc(label)}</div></div>')


def tiles(items, min_width=170):
    """Ряд плиток. items — список HTML-строк от tile(). Плитки переносятся, если не влезают."""
    return (f'<div class="tiles" style="grid-template-columns: repeat(auto-fit, minmax({min_width}px, 1fr))">'
            + "".join(items) + "</div>")


def article_html(word):
    """Немецкое слово с цветным артиклем: <span class="der">der</span> Arzt."""
    if word["article"] == "":
        return esc(word["german"])
    return f'<span class="{word["article"]}">{word["article"]}</span> {esc(word["german"])}'


def chip(text, color="#7C3AED"):
    """Маленькая цветная метка."""
    return f'<span class="chip" style="--c:{color}">{esc(text)}</span>'


def word_info(word, color="#7C3AED"):
    """Карточка с полной информацией о слове."""
    parts = [f'<div class="word-info" style="--c:{color}"><div class="w">{article_html(word)}</div>']
    details = []
    if word["plural"]:
        details.append(f"<b>Мн. ч.:</b> {esc(word['plural'])}")
    if word["perfekt"]:
        details.append(f"<b>Perfekt:</b> {esc(word['perfekt'])}")
    details.append(f"<b>Перевод:</b> {esc(word['russian'])}" +
                   (f" · <i>{esc(word['english'])}</i>" if word["english"] else ""))
    parts.append("<div>" + " &nbsp;·&nbsp; ".join(details) + "</div>")
    if word["example"]:
        parts.append(f'<div class="ex">{esc(word["example"])}</div>')
    parts.append("</div>")
    return "".join(parts)


def result_banner(ok, title, body=""):
    """Зелёный (верно) или красный (ошибка) баннер с результатом."""
    css_class = "res-ok" if ok else "res-bad"
    return f'<div class="res {css_class}"><div class="big">{title}</div>{body}</div>'


def info_banner(title, body=""):
    """Фиолетовый информационный баннер."""
    return f'<div class="res res-info"><div class="big">{title}</div>{body}</div>'


def week_chart(days_xp, goal):
    """Столбики XP за неделю. days_xp — список пар (дата, XP)."""
    names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    biggest = max([xp for _, xp in days_xp] + [goal, 1])
    columns = []
    for number, (day, xp) in enumerate(days_xp):
        height = max(3, round(xp / biggest * 100))
        today_class = " today" if number == len(days_xp) - 1 else ""
        columns.append(
            f'<div class="col"><div class="v">{xp}</div>'
            f'<div class="b{today_class}" style="height:{height}%"></div>'
            f'<div class="d">{names[day.weekday()]}</div></div>'
        )
    return '<div class="week">' + "".join(columns) + "</div>"


# ---------------------------------------------------------------
# JavaScript: озвучка, фокус, звуки, горячие клавиши
# ---------------------------------------------------------------

def speak_button(text, label="🔊 Послушать", key_hint=""):
    """Кнопка, по которой браузер читает немецкий текст вслух (голос встроен в браузер).
    Если key_hint не пустой, текст ещё и прочитается автоматически при показе."""
    text_for_js = json.dumps(text).replace("</", "<\\/")
    autoplay = "speak();" if key_hint else ""
    components.html(
        f"""
        <button onclick="speak()" style="font: 800 15px Nunito, system-ui, sans-serif; padding: 8px 16px;
                cursor: pointer; border-radius: 999px; border: 2px solid #DDD6FE; background: #F5F3FF;
                color: #5B21B6; box-shadow: 0 3px 0 #DDD6FE;">{html.escape(label)}</button>
        <script>
        // {html.escape(key_hint)}
        function speak() {{
            const u = new SpeechSynthesisUtterance({text_for_js});
            u.lang = "de-DE";
            u.rate = 0.9;
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(u);
        }}
        {autoplay}
        </script>
        """,
        height=48,
    )


def focus(selector, nonce):
    """Ставит курсор в элемент страницы (поле ввода или кнопку), чтобы не тянуться к мышке.
    nonce должен меняться — иначе Streamlit не запустит скрипт заново."""
    components.html(
        f"""<script>
        // {html.escape(nonce)}
        setTimeout(function() {{
            const el = window.parent.document.querySelector('{selector}');
            if (el) {{ el.focus(); }}
        }}, 150);
        </script>""",
        height=0,
    )


def play_sound(ok, nonce):
    """Короткий звук: весёлый — за верный ответ, низкий — за ошибку. Звук синтезирует браузер."""
    notes = "[660, 880]" if ok else "[220, 180]"
    components.html(
        f"""<script>
        // {html.escape(nonce)}
        try {{
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            {notes}.forEach(function(freq, i) {{
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = "{'sine' if ok else 'square'}";
                osc.frequency.value = freq;
                gain.gain.setValueAtTime(0.08, ctx.currentTime + i * 0.12);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.12 + 0.18);
                osc.connect(gain); gain.connect(ctx.destination);
                osc.start(ctx.currentTime + i * 0.12);
                osc.stop(ctx.currentTime + i * 0.12 + 0.2);
            }});
        }} catch (e) {{}}
        </script>""",
        height=0,
    )


def keyboard_shortcuts():
    """Горячие клавиши в уроке: 1–4 нажимают варианты ответа, 1–3 — der/die/das.
    Обработчик ставится один раз и при каждом нажатии ищет кнопки на странице заново."""
    components.html(
        """<script>
        const doc = window.parent.document;
        if (!window.parent.__deutschKeys) {
            window.parent.__deutschKeys = true;
            doc.addEventListener("keydown", function(e) {
                const tag = (e.target.tagName || "").toLowerCase();
                if (tag === "input" || tag === "textarea") { return; }
                const map = {"1": ["opt-1", "art-der"], "2": ["opt-2", "art-die"], "3": ["opt-3", "art-das"], "4": ["opt-4"]};
                const names = map[e.key];
                if (!names) { return; }
                for (const name of names) {
                    const btn = doc.querySelector(".st-key-" + name + " button");
                    if (btn) { btn.click(); return; }
                }
            });
        }
        </script>""",
        height=0,
    )
