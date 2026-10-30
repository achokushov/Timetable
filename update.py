import json
import urllib.request
from bs4 import BeautifulSoup

URLS = [
    "https://www.bis.kg/timetable/timetable.php?access=wip&t=110&view=sy",
    "https://www.bis.kg/timetable/timetable.php?access=wip&t=110&view=te",
    "https://www.bis.kg/timetable/timetable.php?access=wip&t=110&view=cr"
]

all_entries = []

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

for url in URLS:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 5:
                    text_cols = [c.get_text(strip=True) for c in cols]
                    if "Day" in text_cols[0] or "Time" in text_cols[1]:
                        continue
                    
                    all_entries.append({
                        "Day": text_cols[0],
                        "Time": text_cols[1],
                        "Grade": text_cols[2],
                        "Subject": text_cols[3] if len(text_cols) > 3 else "",
                        "Teacher": text_cols[4] if len(text_cols) > 4 else "",
                        "Room": text_cols[5] if len(text_cols) > 5 else "N/A"
                    })
    except Exception as e:
        print(f"Предупреждение при обработке {url}: {e}")

# Удаление дубликатов
unique_entries = []
seen = set()
for item in all_entries:
    identifier = (item.get('Day'), item.get('Time'), item.get('Grade'), item.get('Room'), item.get('Teacher'))
    if identifier not in seen and item.get('Day'):
        seen.add(identifier)
        unique_entries.append(item)

# Создание безопасного фоллбека, если сайты не вернули данные
if not unique_entries:
    print("Не удалось получить данные с внешних сайтов. Создаётся базовая структура...")
    unique_entries = [
        {"Day": "Mon", "Time": "08:30 - 09:15", "Grade": "Sample", "Subject": "Data Loading", "Teacher": "N/A", "Room": "101"}
    ]

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(unique_entries, f, ensure_ascii=False, indent=2)

print(f"Готово! Сохранено записей: {len(unique_entries)}")
