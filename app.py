"""
app.py — интерфейс приложения в браузере (Streamlit).
Запуск: streamlit run app.py

ГЛАВНОЕ ПРО STREAMLIT:
при каждом нажатии кнопки весь этот файл выполняется заново, сверху вниз.
Обычные переменные при этом «забываются». Всё, что нужно помнить между
нажатиями (текущая карточка, был ли уже ответ), хранится в st.session_state.
Это специальный словарь, который Streamlit не стирает.
"""

import json
import os

import streamlit as st
import streamlit.components.v1 as components

import checker
import progress
import vocab

# Файл словаря лежит рядом с app.py
WORDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "words.csv")

# Сколько ответов в день — твоя цель (поменяй, если хочешь)
DAILY_GOAL = 20

MODE_NAMES = {
    "de_ru": "Немецкий → русский",
    "ru_de": "Русский → немецкий",
    "article": "Артикли",
}

# Цвета артиклей: der — синий, die — красный, das — зелёный (так принято во многих учебниках)
ARTICLE_COLORS = {"der": "blue", "die": "red", "das": "green"}


# ---------------------------------------------------------------
# Маленькие помощники для отображения
# ---------------------------------------------------------------

def colored(word):
    """Немецкое слово с цветным артиклем в формате Streamlit: ':blue[der] Arzt'."""
    if word["article"] == "":
        return word["german"]
    color = ARTICLE_COLORS[word["article"]]
    return f":{color}[{word['article']}] {word['german']}"


def speak_button(text, label="🔊 Послушать"):
    """Кнопка, по которой браузер читает немецкий текст вслух.

    Используем голос, встроенный в браузер (Web Speech API), поэтому
    ничего устанавливать не нужно. Это маленький кусок JavaScript внутри Python.
    """
    text_for_js = json.dumps(text).replace("</", "<\\/")  # безопасно вставляем текст в JavaScript
    components.html(
        f"""
        <button onclick="speak()" style="font-size:15px; padding:4px 12px; cursor:pointer;
                border-radius:8px; border:1px solid #bbb; background:#fff;">{label}</button>
        <script>
        function speak() {{
            const utterance = new SpeechSynthesisUtterance({text_for_js});
            utterance.lang = "de-DE";
            utterance.rate = 0.9;
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(utterance);
        }}
        </script>
        """,
        height=42,
    )


def focus(selector, nonce):
    """Трюк с JavaScript: ставит курсор в нужный элемент, чтобы не тянуться к мышке.

    selector — «адрес» элемента на странице (поле ввода или кнопка).
    nonce — любая строка, которая меняется для каждой карточки. Без неё Streamlit
    решит, что кусок HTML не изменился, и не запустит скрипт повторно.
    """
    components.html(
        f"""
        <script>
        // {nonce}
        setTimeout(function() {{
            const element = window.parent.document.querySelector('{selector}');
            if (element) {{ element.focus(); }}
        }}, 150);
        </script>
        """,
        height=0,
    )


def show_word_details(word):
    """Полная информация о слове: артикль, множественное число, переводы, пример."""
    st.markdown(f"### {colored(word)}")
    if word["plural"] != "":
        st.markdown(f"**Мн. число:** {word['plural']}")
    translation = f"**Перевод:** {word['russian']}"
    if word["english"] != "":
        translation += f" · *{word['english']}*"
    st.markdown(translation)
    if word["example"] != "":
        st.markdown(f"> {word['example']}")

    left, right = st.columns(2)
    with left:
        speak_button(word["key"], "🔊 Слово")
    if word["example"] != "":
        with right:
            speak_button(word["example"], "🔊 Пример")


def show_result(result, word):
    """Показывает, правильно ли ответил, и куда переехала карточка."""
    status = result["status"]
    if status == "correct":
        st.success("✅ Richtig! Правильно!")
    elif status == "typo":
        st.success("✅ Засчитано (с опечаткой)")
    elif status == "wrong_article":
        st.error("❌ Ошибка в артикле")
    elif result["answer"].strip() == "":
        st.error("❌ Не знаю — ничего страшного, запоминаем:")
    else:
        st.error(f"❌ Falsch. Твой ответ: «{result['answer']}»")

    if result["hint"] != "":
        st.info(result["hint"])

    show_word_details(word)

    old_box, new_box = result["boxes"]
    days = progress.INTERVALS[new_box]
    if days == 0:
        when = "повторим ещё сегодня"
    else:
        when = f"следующий повтор через {days} дн."
    st.caption(f"Коробка {old_box} → {new_box}, {when}")


def show_nothing_due():
    """Сообщение, когда все слова на сегодня повторены."""
    st.success("🎉 На сегодня всё повторено! Gut gemacht!")
    st.info("Хочешь ещё? Сними галочку «Только слова к повторению» слева — "
            "тогда будут все слова, трудные чаще остальных.")


# ---------------------------------------------------------------
# Текущее задание (хранится в st.session_state)
# ---------------------------------------------------------------

def get_task(name, settings, words, progress_data, mode, only_due):
    """Возвращает текущее задание для страницы name.

    Задание — это словарь: какое слово показано, какой был результат ответа.
    Оно живёт в st.session_state и не меняется, пока не нажмёшь «Дальше».
    Если поменялись настройки (режим, уроки), начинаем новое задание.
    """
    if name not in st.session_state or st.session_state[name]["settings"] != settings:
        st.session_state[name] = {"settings": settings, "word": None, "result": None, "last_key": None}

    task = st.session_state[name]
    if task["word"] is None:
        task["word"] = progress.choose_next_word(words, progress_data, mode, only_due, task["last_key"])
    return task


def next_button(task):
    """Кнопка «Дальше»: забываем текущее слово, и при перезапуске выберется новое."""
    if st.button("Дальше ➡️", type="primary"):
        task["last_key"] = task["word"]["key"]
        task["word"] = None
        task["result"] = None
        st.rerun()  # перезапустить скрипт сразу, чтобы показать новую карточку
    # Курсор на кнопку «Дальше»: можно просто нажать Enter
    focus('button[kind="primary"], [data-testid="stBaseButton-primary"]', task["word"]["key"] + "next")


def save_answer(task, word, progress_data, mode, result, answer):
    """Записывает ответ в прогресс, сохраняет файл и запоминает результат в задании."""
    is_correct = checker.is_accepted(result)
    article_mistake = result["status"] == "wrong_article" or (mode == "article" and not is_correct)
    boxes = progress.record_answer(progress_data, word, mode, is_correct, article_mistake)
    progress.save_progress(progress_data)

    result["answer"] = answer
    result["boxes"] = boxes
    task["result"] = result
    st.rerun()


# ---------------------------------------------------------------
# Страницы приложения
# ---------------------------------------------------------------

def page_flashcards(words, progress_data, lessons, only_due):
    st.header("🃏 Карточки")

    # format_func говорит, как показывать вариант: "de_ru" → "Немецкий → русский"
    mode = st.radio("Направление", ["de_ru", "ru_de"], format_func=MODE_NAMES.get, horizontal=True)

    due = progress.count_due(words, progress_data, mode)
    st.caption(f"К повторению сегодня: {due} из {len(words)}")

    task = get_task("flashcards", (mode, tuple(lessons), only_due), words, progress_data, mode, only_due)
    word = task["word"]
    if word is None:
        show_nothing_due()
        return

    card = progress.get_card(progress_data, word, mode)

    # --- Вопрос ---
    with st.container(border=True):
        if task["result"] is None:
            st.caption(f"Коробка {card['box']} из {progress.MAX_BOX} · Lektion {word['lektion']}")
        if mode == "de_ru":
            st.markdown(f"## {colored(word)}")
            speak_button(word["key"])
            label = "Перевод на русский:"
        else:
            st.markdown(f"## {word['russian']}")
            if word["english"] != "":
                st.caption(f"англ.: {word['english']}")
            if vocab.is_noun(word):
                st.caption("Существительное — пиши с артиклем: der / die / das")
            label = "По-немецки:"

    # --- Ответ ---
    if task["result"] is None:
        # Форма: ответ отправляется по кнопке или по Enter
        with st.form("flashcard_form", clear_on_submit=True):
            answer = st.text_input(label, placeholder="Пустой ответ = «не знаю»")
            submitted = st.form_submit_button("Проверить ✔️")
        focus('[data-testid="stForm"] input', word["key"] + mode)

        if submitted:
            if mode == "de_ru":
                result = checker.check_answer(answer, word["russian"])
            else:
                result = checker.check_german(answer, word)
            save_answer(task, word, progress_data, mode, result, answer)
    else:
        show_result(task["result"], word)
        next_button(task)


def page_articles(words, progress_data, lessons, only_due):
    st.header("🎯 der, die или das?")

    nouns = [word for word in words if vocab.is_noun(word)]
    if not nouns:
        st.warning("В выбранных уроках нет существительных с артиклем.")
        return

    due = progress.count_due(nouns, progress_data, "article")
    st.caption(f"К повторению сегодня: {due} из {len(nouns)} существительных")

    task = get_task("articles", (tuple(lessons), only_due), nouns, progress_data, "article", only_due)
    word = task["word"]
    if word is None:
        show_nothing_due()
        return

    with st.container(border=True):
        st.markdown(f"## {word['german']}")
        st.caption(f"{word['russian']} · Lektion {word['lektion']}")

    if task["result"] is None:
        columns = st.columns(3)
        # enumerate даёт номер (0, 1, 2) и сам артикль
        for number, article in enumerate(checker.ARTICLES):
            if columns[number].button(article, width="stretch", key="article_" + article):
                if article == word["article"]:
                    result = {"status": "correct", "hint": ""}
                else:
                    result = {"status": "wrong", "hint": ""}
                save_answer(task, word, progress_data, "article", result, article)
    else:
        show_result(task["result"], word)
        next_button(task)


def page_stats(words, progress_data, lessons):
    st.header("📊 Статистика")
    if lessons:
        st.caption("Статистика по выбранным урокам: " + ", ".join(lessons))

    learned = 0
    for word in words:
        if progress.is_learned(word, progress_data):
            learned += 1

    correct, total = progress.accuracy(words, progress_data, ["de_ru", "ru_de"])
    article_correct, article_total = progress.accuracy(words, progress_data, ["article"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Выучено слов", f"{learned} / {len(words)}")
    col2.metric("Карточки верно", percent(correct, total), help=f"{correct} из {total} ответов")
    col3.metric("Артикли верно", percent(article_correct, article_total),
                help=f"{article_correct} из {article_total} ответов")
    col4.metric("Серия 🔥", f"{progress.streak(progress_data)} дн.")
    st.caption(f"Слово считается выученным, когда во всех режимах оно в коробке "
               f"{progress.LEARNED_BOX} или {progress.MAX_BOX}.")

    # --- Коробки Лейтнера ---
    st.subheader("📦 Коробки Лейтнера")
    mode = st.radio("Режим", progress.MODES, format_func=MODE_NAMES.get, horizontal=True)
    counts = progress.box_counts(words, progress_data, mode)
    columns = st.columns(6)
    columns[0].metric("Новые", counts["новые"])
    for box in range(1, progress.MAX_BOX + 1):
        columns[box].metric(f"Коробка {box}", counts[box])

    # --- Топ ошибок ---
    st.subheader("😈 Топ-10 трудных слов")
    rows = progress.mistakes_table(words, progress_data)
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.write("Ошибок пока нет. Или ты ещё не начинал 😉")

    # --- Активность по дням ---
    st.subheader("📅 Последние дни")
    days = sorted(progress_data["days"].keys())[-14:]  # последние 14 дней с занятиями
    if days:
        chart = {
            "День": days,
            "Ответов": [progress_data["days"][day]["answered"] for day in days],
        }
        st.bar_chart(chart, x="День", y="Ответов")
    else:
        st.write("Здесь появится график, когда начнёшь заниматься.")

    # --- Сброс ---
    with st.expander("⚠️ Сбросить весь прогресс"):
        sure = st.checkbox("Да, я хочу удалить весь прогресс")
        if st.button("Удалить прогресс", disabled=not sure):
            progress.reset_progress()
            st.session_state.clear()
            st.rerun()


def percent(part, total):
    """Процент в виде строки: 15 из 20 → '75%'. Если ответов нет — прочерк."""
    if total == 0:
        return "—"
    return f"{round(part / total * 100)}%"


def page_vocabulary(words, progress_data):
    st.header("📖 Словарь")
    search = st.text_input("🔍 Поиск (по-немецки, по-русски или по-английски)")

    rows = []
    for word in words:
        text = (word["key"] + " " + word["russian"] + " " + word["english"]).lower()
        if search.lower() not in text:
            continue
        row = {
            "Слово": word["key"],
            "Мн. ч.": word["plural"],
            "Перевод": word["russian"],
            "English": word["english"],
            "Lektion": word["lektion"],
        }
        for mode in progress.modes_for_word(word):
            row[MODE_NAMES[mode]] = box_label(progress_data, word, mode)
        rows.append(row)

    st.caption(f"Слов: {len(rows)}. В колонках режимов — номер коробки (1–5), «новое» — ещё не тренировал.")
    st.dataframe(rows, hide_index=True, width="stretch")


def box_label(progress_data, word, mode):
    """Подпись для таблицы словаря: номер коробки или «новое»."""
    if progress.card_id(word, mode) not in progress_data["cards"]:
        return "новое"
    return str(progress.get_card(progress_data, word, mode)["box"])


def page_add_word(all_words):
    st.header("➕ Добавить слово")
    st.caption("Слово допишется в конец words.csv. Можно и редактировать файл напрямую — см. README.")

    with st.form("add_word_form", clear_on_submit=True):
        german = st.text_input("Немецкое слово (без артикля) *", placeholder="Tisch")
        article = st.selectbox("Артикль", ["", "der", "die", "das"],
                               format_func=lambda a: a if a else "— не существительное —")
        plural = st.text_input("Множественное число", placeholder="die Tische")
        russian = st.text_input("Перевод на русский * (варианты через /)", placeholder="стол")
        english = st.text_input("Перевод на английский", placeholder="table")
        lektion = st.text_input("Lektion", placeholder="13")
        example = st.text_input("Пример предложения", placeholder="Der Tisch ist neu.")
        submitted = st.form_submit_button("Добавить ➕", type="primary")

    if submitted:
        new_word = {
            "german": german.strip(),
            "article": article,
            "plural": plural.strip(),
            "russian": russian.strip(),
            "english": english.strip(),
            "lektion": lektion.strip(),
            "example": example.strip(),
        }
        existing_keys = [word["key"] for word in all_words]

        if new_word["german"] == "" or new_word["russian"] == "":
            st.error("Заполни хотя бы немецкое слово и перевод на русский.")
        elif vocab.make_key(new_word) in existing_keys:
            st.error(f"Слово «{vocab.make_key(new_word)}» уже есть в словаре.")
        else:
            vocab.add_word(WORDS_FILE, new_word)
            st.success(f"Добавлено: {vocab.make_key(new_word)} — {new_word['russian']}")


# ---------------------------------------------------------------
# Боковая панель и запуск
# ---------------------------------------------------------------

def sidebar(all_words, progress_data):
    """Меню слева. Возвращает выбранную страницу, уроки и режим «только к повторению»."""
    st.sidebar.title("🇩🇪 Deutsch lernen")
    page = st.sidebar.radio(
        "Раздел",
        ["🃏 Карточки", "🎯 Артикли", "📊 Статистика", "📖 Словарь", "➕ Добавить слово"],
    )

    st.sidebar.divider()
    lessons = st.sidebar.multiselect("Lektion", vocab.get_lessons(all_words), placeholder="Все уроки")
    only_due = st.sidebar.checkbox(
        "Только слова к повторению",
        value=True,
        help="По системе Лейтнера: показываются только слова, которые пора повторить сегодня.",
    )

    st.sidebar.divider()
    today = progress.answered_today(progress_data)
    st.sidebar.markdown(f"🔥 Серия: **{progress.streak(progress_data)}** дн.")
    st.sidebar.progress(min(today / DAILY_GOAL, 1.0), text=f"Цель на сегодня: {today} / {DAILY_GOAL}")
    if today >= DAILY_GOAL:
        st.sidebar.success("Цель выполнена! 🎉")

    return page, lessons, only_due


def main():
    st.set_page_config(page_title="Deutsch lernen", page_icon="🇩🇪")

    all_words, warnings = vocab.load_words(WORDS_FILE)
    progress_data = progress.load_progress()
    page, lessons, only_due = sidebar(all_words, progress_data)

    for warning in warnings:
        st.warning(warning)

    if page == "➕ Добавить слово":
        page_add_word(all_words)
        return

    words = vocab.filter_by_lessons(all_words, lessons)
    if not words:
        st.error("Словарь пуст. Добавь слова в words.csv или на странице «Добавить слово».")
        return

    if page == "🃏 Карточки":
        page_flashcards(words, progress_data, lessons, only_due)
    elif page == "🎯 Артикли":
        page_articles(words, progress_data, lessons, only_due)
    elif page == "📊 Статистика":
        page_stats(words, progress_data, lessons)
    elif page == "📖 Словарь":
        page_vocabulary(words, progress_data)


main()
