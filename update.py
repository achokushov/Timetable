import json
import re
import urllib.request
from bs4 import BeautifulSoup

URLS = [
    "https://www.bis.kg/timetable/timetable.php?access=wip&t=110&view=sy",
    "https://www.bis.kg/timetable/timetable.php?access=wip&t=110&view=te",
    "https://www.bis.kg/timetable/timetable.php?access=wip&t=110&view=cr"
]

all_entries = []

for url in URLS:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')
        
        # Сканируем все таблицы расписания
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 5:
                    text_cols = [c.get_text(strip=True) for c in cols]
                    # Отсеиваем заголовки
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
        print(f"Ошибка при обработке {url}: {e}")

# Удаляем дубликаты
unique_entries = []
seen = set()
for item in all_entries:
    identifier = (item.get('Day'), item.get('Time'), item.get('Grade'), item.get('Room'), item.get('Teacher'))
    if identifier not in seen and item.get('Day'):
        seen.add(identifier)
        unique_entries.append(item)

# Сохраняем результат
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(unique_entries, f, ensure_ascii=False, indent=2)

print(f"Успешно сохранено {len(unique_entries)} записей.")
Нажми зеленую кнопку Commit changes.Шаг 2. Настраиваем робота автозапуска (.github/workflows/auto-update.yml)Нажми Add file $\rightarrow$ Create new file.В поле имени файла напиши слэши точно так, как здесь (GitHub сам создаст нужные папки):.github/workflows/auto-update.ymlВставь код робота:YAMLname: Auto Update BIS Timetable

on:
  schedule:
    # Запуск каждые 6 часов
    - cron: '0 */6 * * *'
  workflow_dispatch:

jobs:
  scrape-and-update:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install beautifulsoup4 requests

      - name: Run scraper
        run: python update.py

      - name: Commit and push changes
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add data.json
          git commit -m "Автоматическое обновление расписания BIS" || exit 0
          git push
