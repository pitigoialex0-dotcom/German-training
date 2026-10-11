"""
Тесты для пути, уроков, очков опыта, Perfekt и диктанта.
Запуск: python -m pytest
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import checker
import goethe
import lesson
import path
import progress
import themen


def word(german, article="", russian="перевод", thema="Wohnen", perfekt="", example="Beispiel."):
    """Быстро создаёт слово для тестов."""
    result = {"german": german, "article": article, "plural": "", "perfekt": perfekt,
              "russian": russian, "english": "", "thema": thema, "lektion": "", "example": example}
    result["key"] = (article + " " + german).strip()
    return result


WORDS = [word(f"Wort{i}", "das", f"слово{i}") for i in range(9)] + [
    word("fahren", perfekt="ist gefahren", russian="ехать"),
    word("kaufen", perfekt="hat gekauft", russian="покупать"),
    word("wohnen", perfekt="hat gewohnt", russian="жить"),
    word("Tisch", "der", "стол", thema=""),
]


# ---------- checker: Perfekt и диктант ----------

def test_perfekt_correct():
    assert checker.check_perfekt("ist gefahren", WORDS[9])["status"] == "correct"


def test_perfekt_wrong_helper_is_not_a_typo():
    # hat/ist отличаются всего парой букв, но это грамматическая ошибка, а не опечатка
    result = checker.check_perfekt("hat gefahren", WORDS[9])
    assert result["status"] == "wrong"
    assert "sein" in result["hint"]


def test_perfekt_with_pronoun():
    assert checker.check_perfekt("er hat gekauft", WORDS[10])["status"] == "correct"


def test_sentence_ignores_punctuation():
    assert checker.check_sentence("ich bin muede", "Ich bin müde.")["status"] == "correct"


def test_sentence_diff_marks_missing_word():
    marks = checker.sentence_diff("Ich bin müde", "Ich bin sehr müde.")
    assert marks == [("Ich", True), ("bin", True), ("sehr", False), ("müde.", True)]


# ---------- темы ----------

def test_topics_order_and_my_words():
    assert themen.ordered_topics(WORDS) == ["Wohnen", themen.MY_WORDS]


# ---------- путь ----------

def test_path_stations():
    units = path.build_path(WORDS)
    kinds = [station["kind"] for station in units[0]["stations"]]
    # 12 слов темы Wohnen → 2 станции слов по 7, артикли, Perfekt, чекпоинт
    assert kinds == ["words", "words", "articles", "perfekt", "checkpoint"]


def test_path_states_unlock_in_order():
    data = progress.new_progress()
    units = path.build_path(WORDS)
    first = units[0]["stations"][0]
    states = path.station_states(units, data)
    assert states[first["id"]] == "current"
    assert states[units[0]["stations"][1]["id"]] == "locked"

    progress.save_station_result(data, first["id"], 0.9)
    states = path.station_states(units, data)
    assert states[first["id"]] == "done"
    assert states[units[0]["stations"][1]["id"]] == "current"


def test_checkpoint_needs_80_percent():
    data = progress.new_progress()
    station = {"id": "Wohnen|checkpoint", "kind": "checkpoint"}
    progress.save_station_result(data, station["id"], 0.7)
    assert not path.is_done(station, data)
    progress.save_station_result(data, station["id"], 0.85)
    assert path.is_done(station, data)


# ---------- уроки ----------

def test_new_words_get_intro_and_choice():
    data = progress.new_progress()
    station = path.build_path(WORDS)[0]["stations"][0]
    new = lesson.build_station_lesson(station, WORDS, data)
    kinds = [task["kind"] for task in new["queue"]]
    assert kinds[:2] == ["intro", "choice"]
    assert kinds.count("intro") == 7
    assert new["scored"] == 14  # 7 выборов + 7 переводов


def test_choice_options_contain_answer():
    task = lesson.make_choice_task(WORDS[0], WORDS)
    assert WORDS[0]["russian"] in task["options"]
    assert len(task["options"]) == 4


def test_mistake_goes_to_end_of_queue():
    tasks = [lesson.make_task("de_ru", WORDS[0]), lesson.make_task("de_ru", WORDS[1])]
    current = lesson.new_lesson("test", tasks)
    lesson.answer(current, False)
    assert [task["key"] for task in current["queue"]] == ["das Wort1", "das Wort0"]
    assert current["combo"] == 0
    assert not current["finished"]


def test_lesson_xp_and_accuracy():
    tasks = [lesson.make_task("de_ru", w) for w in WORDS[:5]]
    current = lesson.new_lesson("test", tasks)
    total = 0
    for _ in range(5):
        total += lesson.answer(current, True)
    # 5 × 10 XP + бонус за 5 подряд
    assert total == 5 * progress.XP_CORRECT + progress.XP_COMBO_BONUS
    assert current["finished"]
    assert lesson.accuracy(current) == 1.0


def test_finish_saves_stars_once():
    data = progress.new_progress()
    current = lesson.new_lesson("test", [lesson.make_task("de_ru", WORDS[0])], station_id="Wohnen|words|1")
    lesson.answer(current, True)
    lesson.finish(current, data)
    lesson.finish(current, data)  # второй вызов ничего не должен добавить
    assert progress.station_stars(data, "Wohnen|words|1") == 3
    assert data["xp"] == progress.XP_LESSON_DONE + progress.XP_PERFECT


def test_task_dropped_after_max_tries():
    current = lesson.new_lesson("test", [lesson.make_task("de_ru", WORDS[0])])
    for _ in range(lesson.MAX_TRIES):
        lesson.answer(current, False)
    assert current["finished"]
    assert lesson.accuracy(current) == 0


def test_review_only_seen_words():
    data = progress.new_progress()
    assert lesson.build_review_lesson(WORDS, data)["queue"] == []
    progress.record_answer(data, WORDS[0], "de_ru", False)
    review = lesson.build_review_lesson(WORDS, data)
    assert [task["key"] for task in review["queue"]] == ["das Wort0"]


# ---------- XP и уровни ----------

def test_levels():
    assert progress.level_info(0) == (1, 0, 100)
    assert progress.level_info(100) == (2, 0, 200)
    assert progress.level_info(350) == (3, 50, 300)


def test_old_progress_file_gets_new_fields(tmp_path):
    old = tmp_path / "progress.json"
    old.write_text('{"cards": {}, "days": {"2026-10-10": {"answered": 3, "correct": 2}}}', encoding="utf-8")
    data = progress.load_progress(str(old))
    assert data["xp"] == 0
    assert data["settings"]["daily_xp"] == progress.DAILY_XP_GOAL
    progress.add_xp(data, 10, today=date(2026, 10, 10))
    assert data["days"]["2026-10-10"]["xp"] == 10


# ---------- Goethe ----------

def test_days_until_exam():
    data = progress.new_progress()
    assert goethe.days_until_exam(data) is None
    data["exam"]["date"] = "2026-12-01"
    assert goethe.days_until_exam(data, today=date(2026, 11, 1)) == 30


def test_readiness_is_zero_without_practice():
    content = {"schreiben": [{}], "redemittel": []}
    parts, overall = goethe.readiness(WORDS, progress.new_progress(), content)
    assert overall == 0
