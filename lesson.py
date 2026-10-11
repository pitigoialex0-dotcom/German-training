"""
lesson.py — урок в стиле Duolingo: очередь заданий, прогресс, очки и повтор ошибок.

Урок — это словарь. Главное в нём — очередь заданий "queue" (список).
Задание — тоже словарь: {"kind": "ru_de", "key": "der Arzt", "tries": 0}.

Как идёт урок:
- показываем первое задание очереди;
- ответил верно → задание убирается из очереди, +XP;
- ошибся → задание переезжает в конец очереди (как в Duolingo),
  но не больше MAX_TRIES раз;
- очередь пуста → урок окончен, считаем звёзды и бонусы.

Здесь нет ничего про Streamlit, поэтому эту логику легко проверять тестами.
"""

import random

import progress
import vocab

LESSON_SIZE = 15   # сколько заданий в обычной тренировке
MAX_TRIES = 3      # сколько раз задание может вернуться после ошибки

# Все виды заданий и их заголовки
TASK_TITLES = {
    "intro": "Новое слово",
    "choice": "Выбери перевод",
    "de_ru": "Переведи на русский",
    "ru_de": "Переведи на немецкий",
    "article": "der, die или das?",
    "perfekt": "Поставь в Perfekt",
    "diktat": "Диктант: напиши, что слышишь",
}


# ---------------------------------------------------------------
# Задания
# ---------------------------------------------------------------

def make_task(kind, word):
    """Одно задание урока."""
    return {"kind": kind, "key": word["key"], "tries": 0}


def make_choice_task(word, pool):
    """Задание с выбором из 4 вариантов перевода. Варианты выбираем сразу,
    чтобы они не менялись при каждом перезапуске страницы."""
    task = make_task("choice", word)
    wrong = []
    for other in pool:
        if other["russian"] != word["russian"] and other["russian"] not in wrong:
            wrong.append(other["russian"])
    options = random.sample(wrong, min(3, len(wrong))) + [word["russian"]]
    random.shuffle(options)
    task["options"] = options
    return task


def kinds_for(word):
    """Какие виды заданий подходят слову."""
    kinds = ["de_ru", "ru_de"]
    if vocab.is_noun(word):
        kinds.append("article")
    if vocab.is_verb_with_perfekt(word):
        kinds.append("perfekt")
    return kinds


def is_new(word, progress_data):
    """Слово новое, если его ещё ни разу не тренировали в карточках."""
    for mode in ["de_ru", "ru_de"]:
        if progress.card_id(word, mode) in progress_data["cards"]:
            return False
    return True


def weakest_first(words, progress_data, mode):
    """Сортирует слова: сначала те, что пора повторять, и из самых младших коробок.
    random.random() в конце ключа перемешивает слова с одинаковыми коробками."""
    def sort_key(word):
        card = progress.get_card(progress_data, word, mode)
        return (not progress.is_due(card), card["box"], random.random())
    return sorted(words, key=sort_key)


# ---------------------------------------------------------------
# Урок
# ---------------------------------------------------------------

def new_lesson(title, tasks, station_id=None, color="#7C3AED"):
    """Создаёт урок из списка заданий."""
    scored = 0
    for task in tasks:
        if task["kind"] != "intro":
            scored += 1
    return {
        "title": title,
        "station": station_id,   # id станции пути (или None для свободной тренировки)
        "color": color,
        "queue": tasks,
        "total": len(tasks),     # для полоски прогресса
        "done": 0,               # сколько заданий уже закрыто
        "scored": scored,        # сколько заданий оцениваются (без «новых слов»)
        "first_try": 0,          # сколько решено с первой попытки
        "combo": 0,              # правильных ответов подряд сейчас
        "best_combo": 0,
        "xp": 0,                 # XP за этот урок
        "mistakes": [],          # слова, в которых были ошибки
        "result": None,          # результат последнего ответа (для показа)
        "finished": False,
        "saved": False,          # итоги урока уже записаны в прогресс
    }


def current_task(lesson):
    """Текущее задание (первое в очереди) или None, если очередь пуста."""
    if lesson["queue"]:
        return lesson["queue"][0]
    return None


def skip_intro(lesson):
    """Закрывает карточку «Новое слово» (её не нужно решать)."""
    lesson["queue"].pop(0)
    lesson["done"] += 1
    if not lesson["queue"]:
        lesson["finished"] = True


def answer(lesson, is_correct):
    """Записывает ответ на текущее задание. Возвращает заработанные XP."""
    task = lesson["queue"].pop(0)
    task["tries"] += 1
    xp = 0

    if is_correct:
        lesson["done"] += 1
        lesson["combo"] += 1
        lesson["best_combo"] = max(lesson["best_combo"], lesson["combo"])
        if task["tries"] == 1:
            lesson["first_try"] += 1
            xp = progress.XP_CORRECT
        else:
            xp = progress.XP_RETRY
        if lesson["combo"] % 5 == 0:
            xp += progress.XP_COMBO_BONUS  # каждые 5 подряд — бонус
    else:
        lesson["combo"] = 0
        if task["key"] not in lesson["mistakes"]:
            lesson["mistakes"].append(task["key"])
        if task["tries"] < MAX_TRIES:
            lesson["queue"].append(task)   # повторим в конце урока
        else:
            lesson["done"] += 1            # хватит мучить это слово

    lesson["xp"] += xp
    if not lesson["queue"]:
        lesson["finished"] = True
    return xp


def accuracy(lesson):
    """Доля заданий, решённых с первой попытки (от 0 до 1)."""
    if lesson["scored"] == 0:
        return 1.0
    return lesson["first_try"] / lesson["scored"]


def finish(lesson, progress_data):
    """Подводит итоги урока: бонусные XP и звёзды станции. Срабатывает один раз."""
    if lesson["saved"]:
        return
    bonus = progress.XP_LESSON_DONE
    if accuracy(lesson) == 1.0 and lesson["scored"] > 0:
        bonus += progress.XP_PERFECT
    progress.add_xp(progress_data, bonus)
    lesson["xp"] += bonus
    lesson["bonus"] = bonus
    lesson["stars"] = progress.stars_for(accuracy(lesson))
    if lesson["station"] is not None:
        progress.save_station_result(progress_data, lesson["station"], accuracy(lesson))
    lesson["saved"] = True


# ---------------------------------------------------------------
# Сборка уроков
# ---------------------------------------------------------------

def build_station_lesson(station, words, progress_data):
    """Урок для станции пути."""
    by_key = {word["key"]: word for word in words}
    station_words = [by_key[key] for key in station["keys"] if key in by_key]
    kind = station["kind"]
    tasks = []

    if kind == "words":
        intro_tasks = []
        practice_tasks = []
        for word in station_words:
            if is_new(word, progress_data):
                # Новое слово: знакомство → выбор перевода → потом написать самому
                intro_tasks.append(make_task("intro", word))
                intro_tasks.append(make_choice_task(word, words))
                practice_tasks.append(make_task("ru_de", word))
            else:
                practice_tasks.append(make_task("de_ru", word))
                practice_tasks.append(make_task("ru_de", word))
        random.shuffle(practice_tasks)
        tasks = intro_tasks + practice_tasks
    elif kind == "articles":
        for word in weakest_first(station_words, progress_data, "article")[:LESSON_SIZE]:
            tasks.append(make_task("article", word))
    elif kind == "perfekt":
        for word in weakest_first(station_words, progress_data, "perfekt")[:LESSON_SIZE]:
            tasks.append(make_task("perfekt", word))
    else:  # checkpoint — смешанный тест по теме
        tasks = mixed_tasks(station_words, progress_data, 12)

    return new_lesson(station["title"], tasks, station_id=station["id"])


def mixed_tasks(words, progress_data, size):
    """Смешанные задания: для каждого слова случайный подходящий вид задания."""
    tasks = []
    chosen = weakest_first(words, progress_data, "ru_de")[:size]
    for word in chosen:
        tasks.append(make_task(random.choice(kinds_for(word)), word))
    random.shuffle(tasks)
    return tasks


def build_practice_lesson(kind, words, progress_data, size=LESSON_SIZE):
    """Свободная тренировка одного вида (карточки, артикли, Perfekt, диктант) или микс."""
    if kind == "mix":
        return new_lesson("Микс", mixed_tasks(words, progress_data, size))

    if kind == "article":
        candidates = [word for word in words if vocab.is_noun(word)]
    elif kind == "perfekt":
        candidates = [word for word in words if vocab.is_verb_with_perfekt(word)]
    elif kind == "diktat":
        candidates = [word for word in words if word["example"] != ""]
    else:
        candidates = list(words)

    tasks = []
    for word in weakest_first(candidates, progress_data, kind)[:size]:
        tasks.append(make_task(kind, word))
    return new_lesson(TASK_TITLES[kind], tasks)


def build_review_lesson(words, progress_data, size=LESSON_SIZE):
    """«Повторение дня»: карточки, которые пора повторить по Лейтнеру (во всех режимах)."""
    due = []
    for word in words:
        for mode in kinds_for(word):
            if progress.card_id(word, mode) not in progress_data["cards"]:
                continue  # новые слова учим на пути, а здесь только повторение
            card = progress.get_card(progress_data, word, mode)
            if progress.is_due(card):
                due.append((card["box"], random.random(), mode, word))
    due.sort(key=lambda item: (item[0], item[1]))  # сначала самые трудные

    tasks = [make_task(mode, word) for box, _, mode, word in due[:size]]
    return new_lesson("Повторение дня", tasks)


def count_review_due(words, progress_data):
    """Сколько карточек ждут повторения сегодня (только уже знакомые слова)."""
    count = 0
    for word in words:
        for mode in kinds_for(word):
            if progress.card_id(word, mode) in progress_data["cards"]:
                if progress.is_due(progress.get_card(progress_data, word, mode)):
                    count += 1
    return count


def build_topic_lesson(title, topic_words, all_words, progress_data, size=8):
    """Урок по теме: берём самые слабые слова темы.
    Новые слова — через знакомство и выбор, знакомые — случайным видом задания."""
    intro_tasks = []
    practice_tasks = []
    for word in weakest_first(topic_words, progress_data, "ru_de")[:size]:
        if is_new(word, progress_data):
            intro_tasks.append(make_task("intro", word))
            intro_tasks.append(make_choice_task(word, all_words))
            practice_tasks.append(make_task("ru_de", word))
        else:
            for kind in random.sample(kinds_for(word), 2):
                practice_tasks.append(make_task(kind, word))
    random.shuffle(practice_tasks)
    return new_lesson(title, intro_tasks + practice_tasks)
