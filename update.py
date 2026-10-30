"""Собирает расписание BIS с трёх страниц (кабинеты / классы / учителя) и
сохраняет в data.json всё, что нужно для поиска свободных кабинетов.

Ничего не придумывается: названия кабинетов, дней и периодов берутся
только с сайта. Если структура страницы не распознана, скрипт завершается
с ошибкой и НЕ перезаписывает data.json.
"""
import datetime
import json
import pathlib
import re
import sys
import time
import urllib.request

from bs4 import BeautifulSoup

BASE = "https://www.bis.kg/timetable/timetable.php?access=wip&t=110&view="
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

SAVE_RAW = True  # сохранять сырой HTML в raw/ (для отладки парсера); потом поставить False

PERIOD_RE = re.compile(r"^\d+(st|nd|rd|th)\b", re.I)          # "1st | 08:00-08:45"
DAY_RE = re.compile(r"^(mon|tue|wed|thu|fri|sat|sun)[a-z]*\b", re.I)
PAREN_RE = re.compile(r"\(([^()]*)\)")


def fetch(view):
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(BASE + view, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            if SAVE_RAW:
                p = pathlib.Path("raw")
                p.mkdir(exist_ok=True)
                (p / f"{view}.html").write_text(html, encoding="utf-8")
            return html
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Не удалось скачать view={view}: {last}")


def is_empty(text):
    return not text.strip("  -–—")


def parse_tables(html):
    """Возвращает список таблиц: {title, days:[...], periods:[...], lessons:[(day, period, text)]}."""
    soup = BeautifulSoup(html, "html.parser")
    result = []
    for table in soup.find_all("table"):
        # На сайте часть тегов </table> не закрыта, поэтому таблицы вложены друг в друга.
        # Берём только строки и текст, которые принадлежат именно этой таблице.
        rows = []
        for tr in table.find_all("tr"):
            if tr.find_parent("table") is not table:
                continue
            cells = []
            for c in tr.find_all(["td", "th"]):
                if c.find_parent("tr") is not tr:
                    continue
                text = " ".join(x.strip() for x in c.strings
                                if x.find_parent("table") is table and x.strip())
                cells.append(text)
            rows.append(cells)

        # строка с названиями дней
        hdr_i = next((i for i, r in enumerate(rows)
                      if sum(bool(DAY_RE.match(c)) for c in r) >= 3), None)
        if hdr_i is None:
            continue
        header = rows[hdr_i]
        day_cols = {j: c for j, c in enumerate(header) if DAY_RE.match(c)}

        # якорь: ячейка "Periods" в шапке, иначе колонка перед первым днём
        anchor_h = next((j for j, c in enumerate(header) if c.lower() == "periods"),
                        min(day_cols) - 1)

        # название таблицы (кабинет / класс / учитель)
        title = None
        if anchor_h > 0 and header[0].strip() and not DAY_RE.match(header[0]):
            title = header[0].strip()
        if not title:
            for r in rows[:hdr_i]:
                cand = next((c for c in r if c.strip() and c.lower() != "periods"), None)
                if cand:
                    title = cand.strip()
                    break
        if not title:
            cap = table.find("caption")
            title = cap.get_text(" ", strip=True) if cap else None

        periods, lessons = [], []
        for r in rows[hdr_i + 1:]:
            anchor_r = next((j for j, c in enumerate(r) if PERIOD_RE.match(c)), None)
            if anchor_r is None:
                continue
            period = r[anchor_r].strip()
            periods.append(period)
            shift = anchor_r - anchor_h
            for j, day in day_cols.items():
                k = j + shift
                if 0 <= k < len(r) and not is_empty(r[k]):
                    lessons.append((day, period, r[k]))
        result.append({"title": title, "days": list(day_cols.values()),
                       "periods": periods, "lessons": lessons})
    return result


def main():
    cr = parse_tables(fetch("cr"))
    rooms, days, periods, busy = [], [], [], set()
    for t in cr:
        if not t["title"]:
            print("ВНИМАНИЕ: таблица без названия кабинета, пропущена", file=sys.stderr)
            continue
        if t["title"] not in rooms:
            rooms.append(t["title"])
        for d in t["days"]:
            if d not in days:
                days.append(d)
        for p in t["periods"]:
            if p not in periods:
                periods.append(p)
        for day, period, _ in t["lessons"]:
            busy.add((day, period, t["title"]))
    from_rooms = len(busy)

    if not rooms or not days or not periods:
        sys.exit("Страница кабинетов не распознана (кабинеты/дни/периоды не найдены). "
                 "Смотрите raw/cr.html — data.json не изменён.")

    # Страницы классов и учителей: если в уроке в скобках указан кабинет
    # (ТОЧНОЕ совпадение с названием кабинета со страницы кабинетов) — он тоже занят.
    room_set = set(rooms)
    warnings = []
    for view in ("sy", "te"):
        try:
            tables = parse_tables(fetch(view))
        except Exception as e:  # noqa: BLE001
            msg = f"view={view} пропущен: {e}"
            print("ВНИМАНИЕ:", msg, file=sys.stderr)
            warnings.append(msg)
            continue
        for t in tables:
            for day, period, text in t["lessons"]:
                for g in PAREN_RE.findall(text):
                    g = g.strip()
                    name = g if g in room_set else (
                        g.split("-", 1)[1].strip() if "-" in g and g.split("-", 1)[1].strip() in room_set else None)
                    if name:
                        busy.add((day, period, name))

    out = {
        "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "days": days,
        "periods": periods,
        "rooms": sorted(rooms, key=str.casefold),
        "busy": [list(x) for x in sorted(busy)],
        "warnings": warnings,
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"Кабинетов: {len(rooms)}, дней: {len(days)}, периодов: {len(periods)}")
    print(f"Занятых слотов: {len(busy)} (со страницы кабинетов: {from_rooms}, "
          f"добавлено из классов/учителей: {len(busy) - from_rooms})")


if __name__ == "__main__":
    err = pathlib.Path("raw/last_error.txt")
    try:
        main()
        err.unlink(missing_ok=True)
    except BaseException:  # noqa: BLE001
        import traceback
        err.parent.mkdir(exist_ok=True)
        err.write_text(datetime.datetime.now(datetime.timezone.utc).isoformat()
                       + "\n" + traceback.format_exc(), encoding="utf-8")
        raise
