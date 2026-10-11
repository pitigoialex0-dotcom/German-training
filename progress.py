"""
progress.py — интервальное повторение по системе Лейтнера и сохранение прогресса.

Система Лейтнера: есть 5 коробок.
- Новое слово лежит в коробке 1.
- Ответил правильно → слово переходит в следующую коробку и появится позже.
- Ошибся → слово возвращается в коробку 1 и появится снова уже сегодня.

Для одного слова есть несколько «карточек» — по одной на каждый режим:
'de_ru' (немецкий → русский), 'ru_de' (русский → немецкий), 'article' (der/die/das).
Так прогресс по направлениям считается отдельно: узнавать слово легче, чем вспоминать.

Всё хранится в файле progress.json примерно так:
{
  "cards": {
    "der Arzt|ru_de": {"box": 2, "next_review": "2026-10-12", "correct": 3,
                       "wrong": 1, "article_wrong": 1, "last_seen": "2026-10-11"}
  },
  "days": {
    "2026-10-11": {"answered": 25, "correct": 20}
  }
}
"""

import json
import os
import random
from datetime import date, timedelta

PROGRESS_FILE = "progress.json"

# Через сколько дней повторять слово из каждой коробки
INTERVALS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 21}
MAX_BOX = 5

# С какой коробки слово считаем выученным
LEARNED_BOX = 4

# Названия режимов (используются в ключах карточек)
MODES = ["de_ru", "ru_de", "article"]


def new_progress():
    """Пустой прогресс для первого запуска."""
    return {"cards": {}, "days": {}}


def load_progress(path=PROGRESS_FILE):
    """Загружает прогресс из JSON-файла. Если файла нет — начинаем с нуля."""
    if not os.path.exists(path):
        return new_progress()
    try:
        with open(path, encoding="utf-8") as f:
            progress = json.load(f)
    except json.JSONDecodeError:
        # Файл испорчен (например, его правили руками). Не удаляем, а откладываем в сторону.
        os.replace(path, path + ".broken")
        return new_progress()
    # setdefault добавит ключ, только если его ещё нет (на случай старого формата файла)
    progress.setdefault("cards", {})
    progress.setdefault("days", {})
    return progress


def save_progress(progress, path=PROGRESS_FILE):
    """Сохраняет прогресс. Сначала пишем во временный файл, потом подменяем старый.
    Так файл не испортится, если программа упадёт посреди записи."""
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


def card_id(word, mode):
    """Ключ карточки: слово + режим, например 'der Arzt|ru_de'."""
    return word["key"] + "|" + mode


def new_card(today):
    """Данные карточки, которую ещё ни разу не показывали."""
    return {
        "box": 1,
        "next_review": today.isoformat(),  # дата как строка '2026-10-11'
        "correct": 0,
        "wrong": 0,
        "article_wrong": 0,
        "last_seen": "",
    }


def get_card(progress, word, mode, today=None):
    """Возвращает данные карточки. Новую карточку не сохраняет — только показывает."""
    today = today or date.today()
    return progress["cards"].get(card_id(word, mode), new_card(today))


def is_due(card, today=None):
    """Пора ли повторять карточку. Даты в формате ГГГГ-ММ-ДД можно сравнивать как строки."""
    today = today or date.today()
    return card["next_review"] <= today.isoformat()


def record_answer(progress, word, mode, is_correct, article_mistake=False, today=None):
    """Записывает ответ: двигает карточку по коробкам и обновляет счётчики.
    Возвращает (старая коробка, новая коробка), чтобы показать это пользователю."""
    today = today or date.today()
    card = progress["cards"].setdefault(card_id(word, mode), new_card(today))
    old_box = card["box"]

    if is_correct:
        card["box"] = min(card["box"] + 1, MAX_BOX)
        card["correct"] += 1
    else:
        card["box"] = 1
        card["wrong"] += 1

    if article_mistake:
        card["article_wrong"] += 1

    card["next_review"] = (today + timedelta(days=INTERVALS[card["box"]])).isoformat()
    card["last_seen"] = today.isoformat()

    # Статистика по дням — для серии дней и дневной цели
    day = progress["days"].setdefault(today.isoformat(), {"answered": 0, "correct": 0})
    day["answered"] += 1
    if is_correct:
        day["correct"] += 1

    return old_box, card["box"]


def choose_next_word(words, progress, mode, only_due=True, avoid_key=None, today=None):
    """Выбирает следующее слово для тренировки.

    Чем ниже коробка, тем больше «вес» слова и тем чаще оно выпадает:
    коробка 1 → вес 5, коробка 5 → вес 1. Так трудные слова появляются чаще.
    """
    candidates = []
    weights = []
    for word in words:
        card = get_card(progress, word, mode, today)
        if only_due and not is_due(card, today):
            continue
        candidates.append(word)
        weights.append(MAX_BOX + 1 - card["box"])

    if not candidates:
        return None

    # Не показываем одно и то же слово два раза подряд (если есть из чего выбрать)
    if len(candidates) > 1:
        for i in range(len(candidates)):
            if candidates[i]["key"] == avoid_key:
                candidates.pop(i)
                weights.pop(i)
                break

    # random.choices выбирает случайный элемент с учётом весов и возвращает список из 1 элемента
    return random.choices(candidates, weights=weights)[0]


def count_due(words, progress, mode, today=None):
    """Сколько карточек ждут повторения сегодня."""
    count = 0
    for word in words:
        if is_due(get_card(progress, word, mode, today), today):
            count += 1
    return count


# ---------------------------------------------------------------
# Статистика
# ---------------------------------------------------------------

def modes_for_word(word):
    """Режимы, в которых тренируется слово: артикль — только у существительных."""
    if word["article"] != "":
        return ["de_ru", "ru_de", "article"]
    return ["de_ru", "ru_de"]


def is_learned(word, progress):
    """Слово выучено, если во всех его режимах карточка в коробке 4 или 5."""
    for mode in modes_for_word(word):
        if get_card(progress, word, mode)["box"] < LEARNED_BOX:
            return False
    return True


def accuracy(words, progress, modes):
    """Возвращает (правильных, всего ответов) по выбранным режимам."""
    correct = 0
    total = 0
    for word in words:
        for mode in modes:
            card = get_card(progress, word, mode)
            correct += card["correct"]
            total += card["correct"] + card["wrong"]
    return correct, total


def mistakes_table(words, progress, limit=10):
    """Топ слов, на которых чаще всего ошибаешься (по всем режимам вместе)."""
    rows = []
    for word in words:
        wrong = 0
        article_wrong = 0
        correct = 0
        for mode in MODES:
            card = get_card(progress, word, mode)
            wrong += card["wrong"]
            correct += card["correct"]
            article_wrong += card["article_wrong"]
        if wrong > 0:
            rows.append({
                "Слово": word["key"],
                "Перевод": word["russian"],
                "Ошибок": wrong,
                "Из них артикль": article_wrong,
                "Правильно": correct,
            })
    # Сортируем по числу ошибок: от большего к меньшему
    rows.sort(key=lambda row: row["Ошибок"], reverse=True)
    return rows[:limit]


def box_counts(words, progress, mode):
    """Сколько карточек в каждой коробке. Ещё не виденные считаем отдельно как «новые»."""
    counts = {"новые": 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for word in words:
        if mode == "article" and word["article"] == "":
            continue
        if card_id(word, mode) not in progress["cards"]:
            counts["новые"] += 1
        else:
            counts[get_card(progress, word, mode)["box"]] += 1
    return counts


def answered_today(progress, today=None):
    """Сколько ответов дано сегодня."""
    today = today or date.today()
    return progress["days"].get(today.isoformat(), {"answered": 0})["answered"]


def streak(progress, today=None):
    """Серия: сколько дней подряд ты занимаешься.
    Если сегодня ещё не занимался, серия не обрывается — считаем со вчерашнего дня."""
    today = today or date.today()
    day = today
    if answered_today(progress, today) == 0:
        day = today - timedelta(days=1)
    count = 0
    while answered_today(progress, day) > 0:
        count += 1
        day = day - timedelta(days=1)
    return count


def reset_progress(path=PROGRESS_FILE):
    """Удаляет весь прогресс (файл progress.json)."""
    if os.path.exists(path):
        os.remove(path)

