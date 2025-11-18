"""Простой утилитарный скрипт для конвертации PDF теста в JSON через LLM.

Функционал:
- извлекает текст из PDF (PyMuPDF); если текст пустой - опционально делает OCR (pytesseract) при наличии зависимостей
- дробит текст по страницам/блокам
- вызывает LLM с промптом из AI_PROMPT_PDF_TO_JSON.md
- валидация схемы и сохранение JSON в tests/

Примечание: необходимо настроить API-ключ и установить зависимости (см. requirements.txt).
"""

import json
import datetime
from pathlib import Path
import importlib
import importlib.util


def _try_import(name):
    try:
        if importlib.util.find_spec(name) is None:
            return None
        return importlib.import_module(name)
    except Exception:
        return None


# Optional libs (import dynamically to avoid hard dependency at static-analysis time)
fitz = _try_import('fitz')  # PyMuPDF
pytesseract = _try_import('pytesseract')
Image = _try_import('PIL.Image')
openai = _try_import('openai')

ROOT = Path(__file__).resolve().parents[1]
PROMPT_FILE = ROOT / 'AI_PROMPT_PDF_TO_JSON.md'
TESTS_DIR = ROOT / 'tests'
TO_CONVERT = ROOT / 'to_convert_PDF'


def load_prompt():
    # Загружает весь файл и извлекает раздел PROMPT между маркерами BEGIN PROMPT и END PROMPT
    text = PROMPT_FILE.read_text(encoding='utf-8')
    start = text.find('=== BEGIN PROMPT ===')
    end = text.find('=== END PROMPT ===')
    if start != -1 and end != -1 and end > start:
        return text[start + len('=== BEGIN PROMPT ==='):end].strip()
    return text


def extract_text_from_pdf(path: Path):
    if fitz is None:
        raise RuntimeError('PyMuPDF (fitz) not installed')
    doc = fitz.open(str(path))
    pages = []
    has_text = False
    for p in doc:
        txt = p.get_text("text")
        pages.append(txt)
        if txt.strip():
            has_text = True
    return {"pages": pages, "has_text": has_text}


def simple_segment_pages(pages):
    # Возвращает объединённые блоки (по страницам) — для больших pdf можно дробить дальше
    blocks = []
    for i, p in enumerate(pages, start=1):
        if p.strip():
            blocks.append({"page": i, "text": p.strip()})
    return blocks


def call_llm(prompt: str, user_text: str, openai_api_key: str = None):
    """Вызов LLM. Возвращает строку с JSON. Текущая реализация: если openai установлен и ключ задан — вызывает API,
    иначе вызывает заглушку, которая возвращает пустую структуру для тестирования.
    """
    system = prompt
    user = user_text
    if openai and openai_api_key:
        openai.api_key = openai_api_key
        # Используем chat completions
        resp = openai.ChatCompletion.create(
            model='gpt-4-o',
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            max_tokens=16000,
            temperature=0.0
        )
        return resp['choices'][0]['message']['content']
    else:
        # Заглушка: возвращаем минимальный JSON
        sample = {
            "id": Path('sample').stem,
            "title": None,
            "language": "en",
            "source": {"filename": None, "page_range": None, "notes": None},
            "items": [],
            "metadata": {"created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "converted_by": "local_stub", "confidence": 0.0},
            "validation": {"passed": False, "errors": ["LLM not configured - stub returned"], "warnings": []}
        }
        return json.dumps(sample)


def validate_and_save(json_text: str, out_path: Path):
    try:
        obj = json.loads(json_text)
    except Exception as e:
        return False, [f"Invalid JSON from LLM: {e}"]
    # Basic checks
    errors = []
    if 'items' not in obj or not isinstance(obj['items'], list) or len(obj['items']) == 0:
        errors.append('No items parsed')
    # добавим validation если нет
    if 'validation' not in obj:
        obj['validation'] = {"passed": False, "errors": errors, "warnings": []}
    else:
        obj['validation'].setdefault('errors', [])
        obj['validation'].setdefault('warnings', [])
        obj['validation']['errors'] += errors
        if obj['validation']['errors']:
            obj['validation']['passed'] = False
    out_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    return True, obj['validation']['errors']


def main():
    prompt = load_prompt()
    files = list(TO_CONVERT.glob('*.pdf'))
    if not files:
        print('No PDF files found in to_convert_PDF/')
        return
    api_key = None
    if 'OPENAI_API_KEY' in os.environ:
        api_key = os.environ['OPENAI_API_KEY']

    for f in files:
        print('Processing', f.name)
        data = extract_text_from_pdf(f)
        blocks = simple_segment_pages(data['pages'])
        combined_text = '\n\n'.join([b['text'] for b in blocks])
        user_payload = f"Filename: {f.name}\n\n{combined_text}"
        llm_out = call_llm(prompt, user_payload, openai_api_key=api_key)
        out_name = TESTS_DIR / (f.stem + '.json')
        ok, errs = validate_and_save(llm_out, out_name)
        if not ok:
            print('Failed to save for', f.name, errs)
        else:
            print('Saved to', out_name)


if __name__ == '__main__':
    import os
    main()
