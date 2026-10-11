"""
goethe.py — всё про экзамен Goethe-Zertifikat A2.

- загружает материалы из data/goethe_a2.json (формат экзамена, задания Schreiben
  и Sprechen, Redemittel — полезные фразы);
- считает примерную «готовность к экзамену» по твоей активности в приложении;
- считает дни до экзамена.
"""

import json
import os
from datetime import date

import progress
import themen

CONTENT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "goethe_a2.json")

# Сколько тренировок считаем «достаточными» для полной шкалы готовности
SPRECHEN_TARGET = 40   # карточек Sprechen
DIKTAT_TARGET = 30     # диктантов
GRAMMAR_TARGET = 60    # ответов в артиклях и Perfekt


def load_content(path=CONTENT_FILE):
    """Материалы экзамена. Если файла нет — пустые списки, приложение всё равно работает."""
    empty = {"exam_info": {}, "schreiben": [], "sprechen_teil1": [], "sprechen_teil2": [],
             "sprechen_teil3": [], "redemittel": []}
    if not os.path.exists(path):
        return empty
    with open(path, encoding="utf-8") as f:
        content = json.load(f)
    for key, value in empty.items():
        content.setdefault(key, value)
    return content


def schreiben_id(task_number):
    """Id задания Schreiben для сохранения отметки «сделано»."""
    return "schreiben-" + str(task_number)


def days_until_exam(progress_data, today=None):
    """Сколько дней до экзамена. None, если дата не задана."""
    exam_date = progress_data["exam"].get("date", "")
    if exam_date == "":
        return None
    today = today or date.today()
    return (date.fromisoformat(exam_date) - today).days


def mode_accuracy(words, progress_data, mode):
    """Возвращает (правильных, всего) по одному режиму."""
    return progress.accuracy(words, progress_data, [mode])


def readiness(words, progress_data, content):
    """Примерная готовность к каждой части экзамена (от 0 до 1).

    Это НЕ прогноз баллов, а оценка того, сколько ты уже натренировал:
    - Wortschatz — доля выученных слов из тем экзамена;
    - Grammatik — точность в артиклях и Perfekt × объём практики;
    - Schreiben — доля сделанных заданий на письмо;
    - Sprechen — сколько карточек устной части проработано;
    - Hören — точность диктантов × объём практики.
    """
    official = [thema["name"] for thema in themen.THEMEN]
    exam_words = [word for word in words if word["thema"] in official]
    learned = 0
    for word in exam_words:
        if progress.is_learned(word, progress_data):
            learned += 1
    wortschatz = learned / len(exam_words) if exam_words else 0

    correct, total = progress.accuracy(words, progress_data, ["article", "perfekt"])
    grammatik = (correct / total if total else 0) * min(1, total / GRAMMAR_TARGET)

    tasks = content["schreiben"]
    done = len(progress_data["exam"]["schreiben_done"])
    schreiben = min(1, done / len(tasks)) if tasks else 0

    sprechen = min(1, progress_data["exam"]["sprechen_done"] / SPRECHEN_TARGET)

    correct, total = progress.accuracy(words, progress_data, ["diktat"])
    hoeren = (correct / total if total else 0) * min(1, total / DIKTAT_TARGET)

    parts = {
        "📚 Wortschatz": wortschatz,
        "🧩 Grammatik": grammatik,
        "✍️ Schreiben": schreiben,
        "🗣️ Sprechen": sprechen,
        "🎧 Hören": hoeren,
    }
    overall = sum(parts.values()) / len(parts)
    return parts, overall


def words_per_day_needed(words, progress_data, today=None):
    """Сколько новых слов в день нужно учить, чтобы успеть пройти все слова до экзамена."""
    days = days_until_exam(progress_data, today)
    if days is None or days <= 0:
        return None
    not_learned = 0
    for word in words:
        if not progress.is_learned(word, progress_data):
            not_learned += 1
    return max(1, round(not_learned / days)) if not_learned else 0
