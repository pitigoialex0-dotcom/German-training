"""
checker.py — проверка ответа.

Что прощаем:
- большие/маленькие буквы, лишние пробелы, точку в конце;
- ae/oe/ue/ss вместо ä/ö/ü/ß и «е» вместо «ё»;
- мелкие опечатки (1–2 буквы в длинных словах).

Каждая функция проверки возвращает словарь с результатом, например:
{"status": "typo", "hint": "Засчитано, но правильно пишется: Brötchen"}

Возможные статусы:
- "correct"       — правильно;
- "typo"          — засчитано, но есть опечатка;
- "wrong_article" — слово правильное, а артикль нет (это ошибка);
- "wrong"         — неправильно.
"""

import re

ARTICLES = ["der", "die", "das"]

# Какие буквы на что заменяем перед сравнением
REPLACEMENTS = {
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    "ß": "ss",
    "ё": "е",
}


def normalize(text):
    """Приводит текст к простому виду: 'Straße.' → 'strasse'."""
    text = text.lower().strip()
    for letter, replacement in REPLACEMENTS.items():
        text = text.replace(letter, replacement)
    text = text.strip(".!?")
    text = " ".join(text.split())  # несколько пробелов подряд → один пробел
    return text


def split_variants(correct):
    """Если правильных ответов несколько ('идти/ходить'), возвращает список ['идти', 'ходить'].

    Пояснение в скобках необязательно: для 'билет (на транспорт)' подойдёт и просто 'билет'.
    """
    for separator in [",", ";"]:
        correct = correct.replace(separator, "/")
    variants = []
    for part in correct.split("/"):
        part = part.strip()
        if part == "":
            continue
        variants.append(part)
        if "(" in part:
            without_brackets = re.sub(r"\(.*?\)", "", part).strip()
            if without_brackets != "":
                variants.append(without_brackets)
    return variants


def count_typos(a, b):
    """Сколько букв нужно вставить, удалить или заменить, чтобы из a получить b.

    Это «расстояние Левенштейна». Пример: 'kopf' → 'kopp' = 1 опечатка.
    Идея: идём по буквам слова a и для каждой буквы помним, сколько правок
    нужно, чтобы превратить начало слова a в каждое начало слова b.
    """
    previous_row = list(range(len(b) + 1))  # [0, 1, 2, ...]: из пустой строки в начало b
    for i, letter_a in enumerate(a, start=1):
        current_row = [i]
        for j, letter_b in enumerate(b, start=1):
            delete = previous_row[j] + 1
            insert = current_row[j - 1] + 1
            replace = previous_row[j - 1] + (letter_a != letter_b)  # True считается как 1
            current_row.append(min(delete, insert, replace))
        previous_row = current_row
    return previous_row[-1]


def allowed_typos(word):
    """Сколько опечаток прощаем. В коротких словах одна буква меняет слово (Rock → Rick)."""
    if len(word) <= 4:
        return 0
    if len(word) <= 8:
        return 1
    return 2


def check_answer(user_answer, correct):
    """Сравнивает ответ с правильным вариантом (или с одним из вариантов через '/')."""
    user = normalize(user_answer)
    if user == "":
        return {"status": "wrong", "hint": "Пустой ответ — считаем как «не знаю»."}

    variants = split_variants(correct)

    # 1. Точное совпадение с каким-то вариантом
    for variant in variants:
        if user_answer.strip() == variant:
            return {"status": "correct", "hint": ""}

    # 2. Совпадение после упрощения (регистр, ae вместо ä и т.п.)
    for variant in variants:
        if user == normalize(variant):
            return {"status": "correct", "hint": f"Правильно. Точное написание: {variant}"}

    # 3. Мелкая опечатка
    for variant in variants:
        clean_variant = normalize(variant)
        if count_typos(user, clean_variant) <= allowed_typos(clean_variant):
            return {"status": "typo", "hint": f"Засчитано, но с опечаткой. Правильно: {variant}"}

    return {"status": "wrong", "hint": ""}


def check_german(user_answer, word):
    """Проверка ответа «русский → немецкий». У существительных нужен артикль: 'der Arzt'."""
    if word["article"] == "":
        return check_answer(user_answer, word["german"])

    # Отделяем артикль от слова: 'der Arzt' → 'der' и 'Arzt'
    parts = user_answer.strip().split(maxsplit=1)
    if len(parts) == 2 and parts[0].lower() in ARTICLES:
        user_article = parts[0].lower()
        user_word = parts[1]
    else:
        user_article = ""
        user_word = user_answer

    result = check_answer(user_word, word["german"])

    if result["status"] != "wrong" and user_article != word["article"]:
        if user_article == "":
            text = "Слово верно, но ты забыл артикль."
        else:
            text = f"Слово верно, но артикль не «{user_article}»."
        return {"status": "wrong_article", "hint": f"{text} Правильно: {word['key']}"}

    return result


def is_accepted(result):
    """Засчитан ли ответ (правильно или с опечаткой)."""
    return result["status"] in ["correct", "typo"]


def check_perfekt(user_answer, word):
    """Проверка формы Perfekt: правильный ответ, например, 'ist gefahren'.

    Сначала проверяем вспомогательный глагол (haben/sein), потом причастие.
    Перепутать haben и sein — самая частая ошибка на A2, поэтому опечаткой её не считаем.
    """
    correct = word["perfekt"]
    correct_parts = correct.split(maxsplit=1)
    user_parts = user_answer.strip().split()

    # Можно написать с местоимением: 'er ist gefahren' — местоимение просто убираем
    if len(user_parts) > 0 and user_parts[0].lower() in ["er", "sie", "es"]:
        user_parts = user_parts[1:]

    if len(user_parts) == 0:
        return {"status": "wrong", "hint": f"Пустой ответ. Правильно: {correct}"}
    if len(correct_parts) < 2:
        return check_answer(" ".join(user_parts), correct)
    if len(user_parts) < 2:
        return {"status": "wrong", "hint": f"Нужны вспомогательный глагол и причастие. Правильно: {correct}"}

    same_helper = normalize(user_parts[0]) == normalize(correct_parts[0])
    rest = check_answer(" ".join(user_parts[1:]), correct_parts[1])

    if same_helper and rest["status"] != "wrong":
        if rest["hint"] != "":
            rest["hint"] = f"{rest['hint'].split(':')[0]}: {correct}"
        return rest
    if not same_helper and rest["status"] != "wrong":
        helper = "sein" if normalize(correct_parts[0]) == "ist" else "haben"
        return {"status": "wrong", "hint": f"Причастие верное, но вспомогательный глагол — {helper}: {correct}"}
    return {"status": "wrong", "hint": f"Правильно: {correct}"}


def sentence_words(text):
    """Разбивает предложение на слова без знаков препинания: 'Ich bin müde.' → ['ich', 'bin', 'muede']."""
    for mark in ".,!?;:\"„“«»()–—":
        text = text.replace(mark, " ")
    return normalize(text).split()


def check_sentence(user_answer, correct):
    """Проверка диктанта: сравниваем предложения целиком, прощая знаки препинания и опечатки.
    На каждые 12 букв прощаем одну опечатку."""
    user = " ".join(sentence_words(user_answer))
    target = " ".join(sentence_words(correct))
    if user == "":
        return {"status": "wrong", "hint": "Пустой ответ — считаем как «не расслышал»."}
    if user == target:
        return {"status": "correct", "hint": ""}
    if count_typos(user, target) <= max(1, len(target) // 12):
        return {"status": "typo", "hint": "Почти идеально — посмотри на подсвеченные слова."}
    return {"status": "wrong", "hint": ""}


def sentence_diff(user_answer, correct):
    """Для каждого слова правильного предложения говорит, написал ли ты его верно.

    Возвращает список пар (слово, верно_ли): [('Ich', True), ('bin', False), ...].
    Используется, чтобы подсветить ошибки в диктанте.
    """
    user_words = sentence_words(user_answer)
    result = []
    for original in correct.split():
        clean = sentence_words(original)
        if len(clean) == 0:
            result.append((original, True))  # отдельный знак препинания, например «–»
            continue
        found = None
        for user_word in user_words:
            if count_typos(user_word, clean[0]) <= allowed_typos(clean[0]):
                found = user_word
                break
        if found is not None:
            user_words.remove(found)  # каждое слово ответа засчитываем только один раз
        result.append((original, found is not None))
    return result
