"""
path.py — «Путь» к экзамену: разделы (по темам) и станции внутри них.

Раздел = одна тема Goethe A2 (Wohnen, Reisen und Verkehr, ...).
Станции раздела по порядку:
  📘 Слова 1, Слова 2, ...  — новые слова небольшими порциями
  🎯 Артикли               — der/die/das для существительных темы
  ⏪ Perfekt               — прошедшее время глаголов темы
  🏆 Чекпоинт              — итоговый тест по теме (нужно 80%)

Станция пройдена, когда урок по ней сдан хотя бы на 60% (чекпоинт — на 80%).
Следующая станция открывается, когда пройдена предыдущая.
"""

import progress
import themen
import vocab

WORDS_PER_STATION = 7      # сколько новых слов в одной станции
CHECKPOINT_PASS = 0.8      # сколько нужно для чекпоинта
STATION_PASS = 0.6         # сколько нужно для обычной станции

STATION_ICONS = {"words": "📘", "articles": "🎯", "perfekt": "⏪", "checkpoint": "🏆"}


def build_path(words):
    """Строит путь: список разделов, в каждом — список станций."""
    units = []
    for thema in themen.ordered_topics(words):
        topic_words = themen.words_of_topic(words, thema)
        stations = []

        # Слова ровными порциями примерно по WORDS_PER_STATION: 22 слова → 8 + 7 + 7,
        # а не 7 + 7 + 7 + 1 (станция из одного слова проваливается одной ошибкой)
        start = 0
        for number, size in enumerate(chunk_sizes(len(topic_words)), start=1):
            chunk = topic_words[start:start + size]
            stations.append(make_station(thema, "words", f"Слова {number}", chunk, number))
            start += size

        nouns = [word for word in topic_words if vocab.is_noun(word)]
        if len(nouns) >= 3:
            stations.append(make_station(thema, "articles", "Артикли", nouns))

        verbs = [word for word in topic_words if vocab.is_verb_with_perfekt(word)]
        if len(verbs) >= 3:
            stations.append(make_station(thema, "perfekt", "Perfekt", verbs))

        stations.append(make_station(thema, "checkpoint", "Чекпоинт", topic_words))
        units.append({"thema": thema, "info": themen.info(thema), "stations": stations})
    return units


def chunk_sizes(total):
    """Размеры порций: 22 → [8, 7, 7], 23 → [8, 8, 7], 12 → [6, 6], 5 → [5]."""
    if total == 0:
        return []
    count = max(1, round(total / WORDS_PER_STATION))   # сколько станций нужно
    base, extra = divmod(total, count)   # divmod(22, 3) → (7, 1)
    return [base + 1] * extra + [base] * (count - extra)


def make_station(thema, kind, title, words, number=None):
    """Одна станция: уникальный id, тип, название и ключи её слов."""
    station_id = thema + "|" + kind
    if number is not None:
        station_id += "|" + str(number)
    return {
        "id": station_id,
        "thema": thema,
        "kind": kind,
        "title": title,
        "icon": STATION_ICONS[kind],
        "keys": [word["key"] for word in words],
    }


def has_untrained_words(station, progress_data):
    """Есть ли в станции слова, которые ты ещё ни разу не тренировал
    (например, ты добавил новое слово в уже пройденную тему)."""
    for key in station["keys"]:
        if key + "|ru_de" not in progress_data["cards"] and key + "|de_ru" not in progress_data["cards"]:
            return True
    return False


def is_done(station, progress_data):
    """Пройдена ли станция."""
    if station["kind"] == "words" and has_untrained_words(station, progress_data):
        return False
    best = progress_data["stations"].get(station["id"], {}).get("best", 0)
    if station["kind"] == "checkpoint":
        return best >= CHECKPOINT_PASS
    return best >= STATION_PASS


def all_stations(units):
    """Все станции всех разделов одним списком по порядку."""
    result = []
    for unit in units:
        result.extend(unit["stations"])
    return result


def station_states(units, progress_data):
    """Состояние каждой станции: 'done' (пройдена), 'current' (следующая), 'locked' (закрыта).

    Идём по станциям по порядку: пройденные — 'done', первая непройденная — 'current',
    всё после неё — 'locked'.
    """
    states = {}
    found_current = False
    for station in all_stations(units):
        if is_done(station, progress_data):
            states[station["id"]] = "done"
        elif not found_current:
            states[station["id"]] = "current"
            found_current = True
        else:
            states[station["id"]] = "locked"
    return states


def current_station(units, progress_data):
    """Следующая станция, которую нужно пройти (или None, если пройден весь путь)."""
    states = station_states(units, progress_data)
    for station in all_stations(units):
        if states[station["id"]] == "current":
            return station
    return None


def unit_progress(unit, states):
    """Сколько станций раздела пройдено: (пройдено, всего)."""
    done = 0
    for station in unit["stations"]:
        if states[station["id"]] == "done":
            done += 1
    return done, len(unit["stations"])


def find_station(units, station_id):
    """Ищет станцию по id."""
    for station in all_stations(units):
        if station["id"] == station_id:
            return station
    return None


def unit_number(units, thema):
    """Номер раздела (с 1) для темы."""
    for number, unit in enumerate(units, start=1):
        if unit["thema"] == thema:
            return number
    return 0


def stars_text(progress_data, station):
    """Звёзды станции текстом: '⭐⭐☆'."""
    stars = progress.station_stars(progress_data, station["id"])
    return "⭐" * stars + "☆" * (3 - stars)
