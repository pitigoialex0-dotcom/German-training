"""
themen.py — темы экзамена Goethe-Zertifikat A2.

Порядок тем в списке = порядок разделов на «Пути».
Каждая тема — словарь: немецкое название (оно же пишется в столбец thema
в words.csv), русское название, эмодзи и цвет для интерфейса.
"""

THEMEN = [
    {"name": "Person und Familie", "ru": "Я и семья", "emoji": "👨‍👩‍👧", "color": "#F43F5E"},
    {"name": "Wohnen", "ru": "Жильё", "emoji": "🏠", "color": "#F59E0B"},
    {"name": "Essen und Trinken", "ru": "Еда и напитки", "emoji": "🍽️", "color": "#EF4444"},
    {"name": "Einkaufen und Kleidung", "ru": "Покупки и одежда", "emoji": "🛍️", "color": "#EC4899"},
    {"name": "Alltag und Zeit", "ru": "День и время", "emoji": "⏰", "color": "#8B5CF6"},
    {"name": "Freizeit und Hobbys", "ru": "Досуг и хобби", "emoji": "⚽", "color": "#10B981"},
    {"name": "Körper und Gesundheit", "ru": "Тело и здоровье", "emoji": "🩺", "color": "#06B6D4"},
    {"name": "Arbeit und Beruf", "ru": "Работа", "emoji": "💼", "color": "#3B82F6"},
    {"name": "Schule und Lernen", "ru": "Учёба", "emoji": "📚", "color": "#6366F1"},
    {"name": "Reisen und Verkehr", "ru": "Путешествия и транспорт", "emoji": "🚆", "color": "#14B8A6"},
    {"name": "Stadt und Dienstleistungen", "ru": "Город и услуги", "emoji": "🏙️", "color": "#F97316"},
    {"name": "Wetter und Natur", "ru": "Погода и природа", "emoji": "🌦️", "color": "#22C55E"},
    {"name": "Feste und Feiern", "ru": "Праздники", "emoji": "🎉", "color": "#D946EF"},
    {"name": "Medien und Kommunikation", "ru": "Медиа и общение", "emoji": "📱", "color": "#0EA5E9"},
]

# Для слов без темы и для тем, которых нет в списке выше
MY_WORDS = "Meine Wörter"


def info(name):
    """Информация о теме по её названию. Для неизвестной темы — серый цвет и булавка."""
    for thema in THEMEN:
        if thema["name"] == name:
            return thema
    if name == "" or name == MY_WORDS:
        return {"name": MY_WORDS, "ru": "Мои слова", "emoji": "📌", "color": "#64748B"}
    return {"name": name, "ru": name, "emoji": "📌", "color": "#64748B"}


def topic_of(word):
    """Тема слова. Пустая тема → «Мои слова»."""
    if word["thema"] == "":
        return MY_WORDS
    return word["thema"]


def ordered_topics(words):
    """Все темы, которые есть в словаре: сначала темы экзамена по порядку, потом твои."""
    present = set()
    for word in words:
        present.add(topic_of(word))

    result = []
    for thema in THEMEN:
        if thema["name"] in present:
            result.append(thema["name"])
    # Темы, которые ты придумал сам (их нет в THEMEN), — по алфавиту
    official = [thema["name"] for thema in THEMEN]
    for name in sorted(present):
        if name not in official and name != MY_WORDS:
            result.append(name)
    if MY_WORDS in present:
        result.append(MY_WORDS)
    return result


def words_of_topic(words, name):
    """Все слова одной темы."""
    return [word for word in words if topic_of(word) == name]
