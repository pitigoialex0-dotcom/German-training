"""
dictionary.py — «Словарь»: все слова с поиском и форма добавления нового слова.
"""

import streamlit as st

import progress
import themen
import ui
import vocab


def box_label(progress_data, word, mode):
    """Номер коробки или «—», если слово в этом режиме ещё не тренировали."""
    if progress.card_id(word, mode) not in progress_data["cards"]:
        return "—"
    return str(progress.get_card(progress_data, word, mode)["box"])


def render(words, progress_data, words_file):
    ui.show(f'<div class="hero"><div><h1>📖 Словарь</h1>'
            f'<p>Все слова из words.csv. Добавляй свои слова из Menschen — они появятся на пути и в темах.</p></div>'
            f'<div class="hero-right"><span class="pill">📚 {len(words)} слов</span></div></div>')

    tab_list, tab_add = st.tabs(["📖 Все слова", "➕ Добавить слово"])

    with tab_list:
        col_search, col_topic = st.columns([2, 1])
        with col_search:
            search = st.text_input("🔍 Поиск (по-немецки, по-русски или по-английски)")
        with col_topic:
            topics = st.multiselect("Темы", themen.ordered_topics(words), placeholder="Все темы")

        rows = []
        for word in vocab.filter_by_topics(words, topics) if topics else words:
            text = (word["key"] + " " + word["russian"] + " " + word["english"]).lower()
            if search.lower() not in text:
                continue
            rows.append({
                "Слово": word["key"],
                "Мн. ч.": word["plural"],
                "Perfekt": word["perfekt"],
                "Перевод": word["russian"],
                "Тема": themen.topic_of(word),
                "Lektion": word["lektion"],
                "DE→RU": box_label(progress_data, word, "de_ru"),
                "RU→DE": box_label(progress_data, word, "ru_de"),
                "Выучено": "✅" if progress.is_learned(word, progress_data) else "",
            })
        st.caption(f"Найдено: {len(rows)}. В колонках DE→RU и RU→DE — номер коробки Лейтнера (1–5).")
        st.dataframe(rows, hide_index=True, width="stretch", height=520)

    with tab_add:
        add_form(words, words_file)


def add_form(words, words_file):
    topic_names = [thema["name"] for thema in themen.THEMEN]
    with st.form("add-word", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            german = st.text_input("Немецкое слово (без артикля) *", placeholder="Tisch")
            article = st.selectbox("Артикль", ["", "der", "die", "das"],
                                   format_func=lambda a: a if a else "— не существительное —")
            plural = st.text_input("Множественное число", placeholder="die Tische")
            perfekt = st.text_input("Perfekt (для глаголов)", placeholder="hat gekauft / ist gefahren")
        with col2:
            russian = st.text_input("Перевод на русский * (варианты через /)", placeholder="стол")
            english = st.text_input("Перевод на английский", placeholder="table")
            thema = st.selectbox("Тема", [""] + topic_names,
                                 format_func=lambda t: f'{themen.info(t)["emoji"]} {t}' if t else "📌 Мои слова")
            lektion = st.text_input("Lektion (Menschen)", placeholder="13")
        example = st.text_input("Пример предложения", placeholder="Der Tisch ist neu.")
        submitted = st.form_submit_button("Добавить ➕", type="primary")

    if submitted:
        new_word = {
            "german": german.strip(), "article": article, "plural": plural.strip(),
            "perfekt": perfekt.strip(), "russian": russian.strip(), "english": english.strip(),
            "thema": thema, "lektion": lektion.strip(), "example": example.strip(),
        }
        existing = [word["key"] for word in words]
        if new_word["german"] == "" or new_word["russian"] == "":
            st.error("Заполни хотя бы немецкое слово и перевод на русский.")
        elif vocab.make_key(new_word) in existing:
            st.error(f"Слово «{vocab.make_key(new_word)}» уже есть в словаре.")
        else:
            vocab.add_word(words_file, new_word)
            st.success(f"Добавлено: {vocab.make_key(new_word)} — {new_word['russian']}")
