"""
vocab.py — чтение и запись словаря (файл words.csv).

Каждое слово из CSV превращается в словарь Python (dict), например:
{
    "german": "Arzt",
    "article": "der",
    "plural": "die Ärzte",
    "russian": "врач",
    "english": "doctor",
    "perfekt": "",
    "thema": "Körper und Gesundheit",
    "lektion": "15",
    "example": "Der Arzt sagt: Sie müssen im Bett bleiben.",
    "key": "der Arzt",
}
"""

import csv
import io
import os

# Столбцы, которые должны быть в первой строке CSV-файла
COLUMNS = ["german", "article", "plural", "russian", "english", "lektion", "example"]

# Необязательные столбцы: если их нет в файле, будут пустыми
# thema   — тема экзамена Goethe A2 (например, "Wohnen")
# perfekt — для глаголов: вспомогательный глагол + Partizip II ("ist gefahren")
OPTIONAL_COLUMNS = ["thema", "perfekt"]

# Порядок столбцов для нового файла
ALL_COLUMNS = ["german", "article", "plural", "perfekt", "russian", "english", "thema", "lektion", "example"]

# Допустимые артикли
ARTICLES = ["der", "die", "das"]


def make_key(word):
    """Уникальное имя слова вместе с артиклем: 'der Arzt', 'gehen'.

    По этому ключу мы связываем слово с его прогрессом в progress.json.
    Артикль входит в ключ, потому что 'der See' (озеро) и 'die See' (море) — разные слова.
    """
    return (word["article"] + " " + word["german"]).strip()


def is_noun(word):
    """Существительное = слово, у которого указан артикль."""
    return word["article"] != ""


def detect_delimiter(first_line):
    """Определяет разделитель столбцов.

    Excel с русскими настройками сохраняет CSV через точку с запятой (;),
    а Google Sheets и большинство редакторов — через запятую (,).
    Поддерживаем оба варианта: смотрим, какого символа в заголовке больше.
    """
    if first_line.count(";") > first_line.count(","):
        return ";"
    return ","


def read_text(path):
    """Читает весь файл как текст. 'utf-8-sig' понимает и обычный UTF-8, и UTF-8 из Excel."""
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def load_words(path):
    """Читает CSV-файл. Возвращает два списка: (слова, предупреждения).

    Предупреждения — это понятные сообщения о проблемах в файле
    (неправильный артикль, пустой перевод, дубликат), чтобы ты мог их исправить.
    """
    words = []
    warnings = []

    if not os.path.exists(path):
        warnings.append(f"Файл {path} не найден.")
        return words, warnings

    try:
        text = read_text(path)
    except UnicodeDecodeError:
        warnings.append(
            f"Файл {path} сохранён не в кодировке UTF-8. "
            "В Excel выбери «Сохранить как → CSV UTF-8 (разделитель — запятая)»."
        )
        return words, warnings

    first_line = text.split("\n")[0]
    reader = csv.DictReader(io.StringIO(text), delimiter=detect_delimiter(first_line))

    # Проверяем, что в заголовке есть все нужные столбцы
    header = reader.fieldnames or []
    missing = [column for column in COLUMNS if column not in header]
    if missing:
        warnings.append(
            "В первой строке CSV не хватает столбцов: " + ", ".join(missing)
            + ". Нужна строка: " + ",".join(COLUMNS)
        )
        return words, warnings

    seen_keys = set()  # множество ключей, которые уже встречались (для поиска дубликатов)

    # enumerate считает строки; start=2, потому что строка 1 — это заголовок
    for line_number, row in enumerate(reader, start=2):
        # Собираем слово: берём каждый столбец и убираем пробелы по краям
        word = {}
        for column in COLUMNS + OPTIONAL_COLUMNS:
            value = row.get(column) or ""  # "or ''" — на случай, если в строке не хватает ячеек
            word[column] = value.strip()

        if word["german"] == "":
            continue  # пустую строку просто пропускаем

        word["article"] = word["article"].lower()

        # Частая ошибка: написать "der Arzt" прямо в столбце german. Исправляем сами.
        first_part = word["german"].split(" ")[0].lower()
        if word["article"] == "" and first_part in ARTICLES and " " in word["german"]:
            word["article"] = first_part
            word["german"] = word["german"].split(" ", 1)[1].strip()

        if word["article"] not in ARTICLES and word["article"] != "":
            warnings.append(
                f"Строка {line_number}: непонятный артикль «{word['article']}» у слова "
                f"«{word['german']}». Должно быть der, die, das или пусто. Артикль пропущен."
            )
            word["article"] = ""

        if word["russian"] == "":
            warnings.append(f"Строка {line_number}: у слова «{word['german']}» нет перевода — слово пропущено.")
            continue

        word["key"] = make_key(word)
        if word["key"] in seen_keys:
            warnings.append(f"Строка {line_number}: слово «{word['key']}» уже есть выше — дубликат пропущен.")
            continue

        seen_keys.add(word["key"])
        words.append(word)

    return words, warnings


def lesson_sort_key(lesson):
    """Помогает сортировать уроки как числа: 2 раньше 13 (а не '13' раньше '2', как у строк)."""
    if lesson.isdigit():
        return (0, int(lesson), "")
    return (1, 0, lesson)  # нечисловые названия уроков — в конец списка


def get_lessons(words):
    """Список всех уроков (Lektion), которые есть в словаре, без повторов."""
    lessons = set()
    for word in words:
        if word["lektion"] != "":
            lessons.add(word["lektion"])
    return sorted(lessons, key=lesson_sort_key)


def filter_by_lessons(words, lessons):
    """Оставляет только слова выбранных уроков. Если ничего не выбрано — все слова."""
    if not lessons:
        return words
    return [word for word in words if word["lektion"] in lessons]


def filter_by_topics(words, topics):
    """Оставляет только слова выбранных тем. Если ничего не выбрано — все слова."""
    if not topics:
        return words
    return [word for word in words if word["thema"] in topics]


def is_verb_with_perfekt(word):
    """Глагол, для которого в словаре указана форма Perfekt."""
    return word["perfekt"] != ""


def add_word(path, word):
    """Дописывает новое слово в конец CSV-файла (тем же разделителем, что уже в файле)."""
    if not os.path.exists(path):
        # Файла нет — создаём его с заголовком
        with open(path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(ALL_COLUMNS)

    text = read_text(path)
    delimiter = detect_delimiter(text.split("\n")[0])
    rows = list(csv.DictReader(io.StringIO(text), delimiter=delimiter))
    header = next(csv.reader(io.StringIO(text), delimiter=delimiter))
    header = [column.strip() for column in header]

    # В старом файле может не быть новых столбцов (thema, perfekt) — добавляем их,
    # переписав файл целиком, иначе новые данные потерялись бы
    missing = [column for column in ALL_COLUMNS if column not in header]
    if missing:
        header = header + missing
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=header, delimiter=delimiter, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        text = read_text(path)

    with open(path, "a", encoding="utf-8", newline="") as f:
        # Если файл не заканчивается переводом строки, новое слово прилипло бы к последнему
        if text != "" and not text.endswith("\n"):
            f.write("\n")
        writer = csv.DictWriter(f, fieldnames=header, delimiter=delimiter, extrasaction="ignore")
        writer.writerow(word)
