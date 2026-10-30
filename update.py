import json
import urllib.request
from bs4 import BeautifulSoup

URLS = [
    "https://www.bis.kg/timetable/timetable.php?access=wip&t=110&view=sy",
    "https://www.bis.kg/timetable/timetable.php?access=wip&t=110&view=te",
    "https://www.bis.kg/timetable/timetable.php?access=wip&t=110&view=cr"
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

all_entries = []

for url in URLS:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
                if len(cols) >= 4:
                    # Пропускаем заголовки
                    if any(header in cols[0] for header in ["Day", "Time", "День", "Время"]):
                        continue
                    
                    all_entries.append({
                        "Day": cols[0] if cols[0] else "Mon",
                        "Time": cols[1] if len(cols) > 1 else "08:30 - 09:15",
                        "Grade": cols[2] if len(cols) > 2 else "General",
                        "Subject": cols[3] if len(cols) > 3 else "Lesson",
                        "Teacher": cols[4] if len(cols) > 4 else "Staff",
                        "Room": cols[5] if len(cols) > 5 else "101"
                    })
    except Exception as e:
        print(f"Ошибка чтения {url}: {e}")

# Очистка и удаление дубликатов
unique_entries = []
seen = set()

for item in all_entries:
    key = (item["Day"], item["Time"], item["Grade"], item["Room"], item["Teacher"])
    if key not in seen:
        seen.add(key)
        unique_entries.append(item)

# Если с сайта ничего не собралось — создаём начальный набора данных для проверки сайта
if not unique_entries:
    print("Данные с внешнего сайта не найдены. Создаем резервное расписание...")
    unique_entries = [
        {"Day": "Mon", "Time": "08:30 - 09:15", "Grade": "Grade 1", "Subject": "Math", "Teacher": "Mr. Smith", "Room": "101"},
        {"Day": "Mon", "Time": "08:30 - 09:15", "Grade": "Grade 2", "Subject": "English", "Teacher": "Ms. Davis", "Room": "102"},
        {"Day": "Mon", "Time": "09:20 - 10:05", "Grade": "Grade 1", "Subject": "Science", "Teacher": "Mr. Smith", "Room": "103"},
        {"Day": "Tue", "Time": "08:30 - 09:15", "Grade": "Grade 3", "Subject": "History", "Teacher": "Mrs. Wilson", "Room": "201"}
    ]

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(unique_entries, f, ensure_ascii=False, indent=2)

print(f"Готово! Записано уроков: {len(unique_entries)}")
