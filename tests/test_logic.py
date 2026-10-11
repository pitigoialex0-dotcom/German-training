"""
Автоматические тесты. Запуск: python -m pytest
Каждая функция test_... проверяет одну вещь. assert = «утверждаю, что это правда».
Если утверждение ложно, pytest покажет, где именно ошибка.
"""

import os
import sys
from datetime import date

# Чтобы тесты нашли наши модули в папке выше
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import checker
import progress
import vocab

ARZT = {"german": "Arzt", "article": "der", "russian": "врач", "key": "der Arzt"}
GEHEN = {"german": "gehen", "article": "", "russian": "идти/ходить", "key": "gehen"}


# ---------- checker.py ----------

def test_exact_answer():
    assert checker.check_answer("Straße", "Straße")["status"] == "correct"


def test_umlaut_replacements():
    assert checker.check_answer("Strasse", "Straße")["status"] == "correct"
    assert checker.check_answer("Broetchen", "Brötchen")["status"] == "correct"
    assert checker.check_answer("schoen", "schön")["status"] == "correct"


def test_yo_letter():
    assert checker.check_answer("елка", "ёлка")["status"] == "correct"


def test_one_typo_in_long_word_is_accepted():
    assert checker.check_answer("Wonung", "Wohnung")["status"] == "typo"


def test_typo_in_short_word_is_wrong():
    # В коротком слове одна буква — уже другое слово
    assert checker.check_answer("Rick", "Rock")["status"] == "wrong"


def test_variants():
    assert checker.check_answer("ходить", "идти/ходить")["status"] == "correct"


def test_empty_answer_is_wrong():
    assert checker.check_answer("   ", "врач")["status"] == "wrong"


def test_noun_with_correct_article():
    assert checker.check_german("der Arzt", ARZT)["status"] == "correct"


def test_noun_with_wrong_article():
    assert checker.check_german("die Arzt", ARZT)["status"] == "wrong_article"


def test_noun_without_article():
    assert checker.check_german("Arzt", ARZT)["status"] == "wrong_article"


def test_verb_needs_no_article():
    assert checker.check_german("gehen", GEHEN)["status"] == "correct"


def test_count_typos():
    assert checker.count_typos("kopf", "kopf") == 0
    assert checker.count_typos("kopf", "kopp") == 1
    assert checker.count_typos("", "abc") == 3


# ---------- progress.py ----------

def test_leitner_boxes():
    data = progress.new_progress()
    today = date(2026, 10, 11)

    progress.record_answer(data, ARZT, "ru_de", True, today=today)
    card = progress.get_card(data, ARZT, "ru_de", today)
    assert card["box"] == 2
    assert card["next_review"] == "2026-10-12"  # коробка 2 → через 1 день

    progress.record_answer(data, ARZT, "ru_de", False, today=today)
    card = progress.get_card(data, ARZT, "ru_de", today)
    assert card["box"] == 1  # ошибка → обратно в коробку 1
    assert progress.is_due(card, today)  # и повторяем уже сегодня


def test_streak():
    data = progress.new_progress()
    data["days"] = {
        "2026-10-09": {"answered": 5, "correct": 5},
        "2026-10-10": {"answered": 3, "correct": 1},
    }
    # Сегодня (11-е) ещё не занимались, но серия из 2 дней не обрывается
    assert progress.streak(data, date(2026, 10, 11)) == 2


def test_choose_next_word_skips_not_due():
    data = progress.new_progress()
    today = date(2026, 10, 11)
    progress.record_answer(data, ARZT, "de_ru", True, today=today)  # следующий повтор — завтра
    word = progress.choose_next_word([ARZT, GEHEN], data, "de_ru", only_due=True, today=today)
    assert word["key"] == "gehen"


def test_last_due_word_is_shown_again():
    data = progress.new_progress()
    word = progress.choose_next_word([ARZT], data, "de_ru", avoid_key="der Arzt")
    assert word["key"] == "der Arzt"


def test_save_and_load(tmp_path):
    path = str(tmp_path / "progress.json")
    data = progress.new_progress()
    progress.record_answer(data, ARZT, "article", False, article_mistake=True)
    progress.save_progress(data, path)
    loaded = progress.load_progress(path)
    assert loaded["cards"]["der Arzt|article"]["article_wrong"] == 1


# ---------- vocab.py ----------

def test_load_template_csv():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "words.csv")
    words, warnings = vocab.load_words(path)
    assert len(words) == 10
    assert warnings == []


def test_semicolon_csv_and_article_in_german_column(tmp_path):
    path = tmp_path / "words.csv"
    path.write_text(
        "german;article;plural;russian;english;lektion;example\n"
        "der Tisch;;die Tische;стол;table;13;Der Tisch ist neu.\n",
        encoding="utf-8",
    )
    words, warnings = vocab.load_words(str(path))
    assert words[0]["article"] == "der"
    assert words[0]["german"] == "Tisch"
    assert words[0]["key"] == "der Tisch"


def test_add_word(tmp_path):
    path = str(tmp_path / "words.csv")
    new = {"german": "Tisch", "article": "der", "plural": "die Tische", "russian": "стол",
           "english": "table", "lektion": "13", "example": "Der Tisch ist neu, aber klein."}
    vocab.add_word(path, new)
    words, warnings = vocab.load_words(path)
    assert words[0]["example"] == "Der Tisch ist neu, aber klein."  # запятая внутри примера не ломает CSV


def test_lessons_sorted_as_numbers():
    words = [{"lektion": "13"}, {"lektion": "2"}, {"lektion": "13"}]
    assert vocab.get_lessons(words) == ["2", "13"]
