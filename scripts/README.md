Как использовать scripts/pdf2json.py

1) Установите зависимости (виртуальное окружение рекомендуется):

pip install -r scripts/requirements.txt

2) (Опционально) Установите Tesseract OCR и добавьте в PATH, если ожидается OCR обработка сканов.

3) Установите переменную окружения OPENAI_API_KEY если хотите использовать OpenAI:

# Windows PowerShell
$env:OPENAI_API_KEY = 'sk-...'

4) Поместите PDF файлы в папку to_convert_PDF/ (в корне проекта).

5) Запустите:

python scripts/pdf2json.py

Результат сохраняется в tests/<имя-файла>.json

Примечание: скрипт использует промпт из AI_PROMPT_PDF_TO_JSON.md. Если LLM не настроена, скрипт создаст заглушку и пометит validation.failed.
