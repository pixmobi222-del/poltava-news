#!/usr/bin/env python3
"""Збирає новини з RSS-стрічок полтавських видань у файл news.json.

Зберігаємо тільки заголовок, дату, короткий анонс і посилання на першоджерело.
Повні тексти статей не копіюються.
"""
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime

# Джерела з робочим RSS. Порядок важливий: перше джерело має пріоритет при дублях.
SOURCES = [
    {"name": "Полтавщина", "url": "https://poltava.to/rss/news.xml"},
    {"name": "Коло", "url": "https://kolo.news/rss"},
]

OUT = "news.json"
MAX_ITEMS = 300        # скільки новин зберігати
MAX_SUMMARY = 280      # максимальна довжина анонсу, символів
UA = "Mozilla/5.0 (compatible; PoltavaNewsBot/1.0)"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def clean(text):
    """Прибирає HTML-теги та зайві пробіли."""
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_date(text):
    try:
        date = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return date.astimezone(timezone.utc)


def parse_feed(data, source):
    items = []
    root = ET.fromstring(data)
    for node in root.iter("item"):
        title = clean(node.findtext("title"))
        link = (node.findtext("link") or "").strip()
        date = parse_date(node.findtext("pubDate") or "")
        if not title or not link or not date:
            continue
        summary = clean(node.findtext("description"))[:MAX_SUMMARY]
        items.append({
            "title": title,
            "url": link,
            "summary": summary,
            "full": summary,
            "source": source["name"],
            "published": date.isoformat(),
            "also": [],
        })
    return items


def title_key(title):
    """Ключ для пошуку дублів: нижній регістр, без знаків, перші 60 символів."""
    return re.sub(r"[^\w]+", "", title.lower())[:60]


def dedupe(items):
    """Одна новина від кількох видань — одна картка. Інші видання записуємо в also."""
    seen = {}
    result = []
    for item in items:
        key = title_key(item["title"])
        if key in seen:
            seen[key]["also"].append(item["source"])
        else:
            seen[key] = item
            result.append(item)
    return result


def main():
    items = []
    errors = []
    for source in SOURCES:
        try:
            items += parse_feed(fetch(source["url"]), source)
        except Exception as error:  # одне джерело не має зупиняти весь збір
            errors.append(f"{source['name']}: {error}")

    if not items:
        # Нічого не отримали — залишаємо попередній news.json без змін
        print("Нових даних немає. Помилки:", errors)
        return

    result = dedupe(items)
    result.sort(key=lambda x: x["published"], reverse=True)
    result = result[:MAX_ITEMS]

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

    print(f"Збережено {len(result)} новин. Помилки: {errors or 'немає'}")


if __name__ == "__main__":
    main()
