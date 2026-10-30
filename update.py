import json
import urllib.request
from bs4 import BeautifulSoup

URLS = [
    "https://www.bis.kg/timetable/timetable.php?access=wip&t=110&view=sy",
    "https://www.bis.kg/timetable/timetable.php?access=wip&t=110&view=te",
    "https://www.bis.kg/timetable/timetable.php?access=wip&t=110&view=cr"
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

all_entries = []

for url in URLS:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                text_cols = [c.get_text(strip=True) for c in cols]
                
                # Пропускаем строки с заголовками или пустые
                if not text_cols or "Day" in text_cols[0] or "Time" in text_cols[0]:
                    continue
                
                # Если в строке есть данные урока
                if len(text_cols) >= 5:
                    all_entries.append({
                        "Day": text_cols[0],
                        "Time": text_cols[1],
                        "Grade": text_cols[2] if text_cols[2] else "N/A",
                        "Subject": text_cols[3] if len(text_cols) > 3 else "Lesson",
                        "Teacher": text_cols[4] if len(text_cols) > 4 else "N/A",
                        "Room": text_cols[5] if len(text_cols) > 5 and text_cols[5] else "N/A"
                    })
    except Exception as e:
        print(f"Ошибка при скачивании {url}: {e}")

# Фильтруем дубликаты
unique_entries = []
seen = set()

for item in all_entries:
    # Исключаем служебные записи
    if item["Day"] in ["Mon", "Tue", "Wed", "Thu", "Fri", "Пн", "Вт", "Ср", "Чт", "Пт"]:
        key = (item["Day"], item["Time"], item["Grade"], item["Room"], item["Teacher"])
        if key not in seen:
            seen.add(key)
            unique_entries.append(item)

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(unique_entries, f, ensure_ascii=False, indent=2)

print(f"Успешно собрано {len(unique_entries)} уроков.")
