"""Локальный конвертер PDF (tasks + answers) -> JSON без LLM.

Алгоритм:
- Находит пары файлов: tasks-*.pdf и ans-*.pdf в папке to_convert_PDF/
- Извлекает текст через PyMuPDF
- Парсит вопросы по номерной нотации (1., 2), 1), 1)
- Парсит варианты ответа A-D
- Извлекает ключ ответов из ans-*.pdf (шаблоны: "1 B", "1. B", "1) B", "1-B")
- Формирует JSON в схеме, похожей на промпт: top-level id, title, language, source, items[].

Сохранение: tests/<tasks_stem>.json
"""

import re
import json
from pathlib import Path
import datetime

try:
    import fitz
except Exception as e:
    raise RuntimeError('PyMuPDF (fitz) required. Install with: pip install PyMuPDF') from e

ROOT = Path(__file__).resolve().parents[1]
TO_CONVERT = ROOT / 'to_convert_PDF'
TESTS_DIR = ROOT / 'tests'
TESTS_DIR.mkdir(exist_ok=True)

NUM_RE = re.compile(r'(^|\n)\s*(\d{1,3})[\.)]\s+', re.M)
OPTION_RE = re.compile(r'(^|\n)\s*([A-D])(?:[\).\s:-]+)')
ANS_RE = re.compile(r'(\d{1,3})[^A-Za-z0-9]*([A-D])', re.I)


def extract_text(pdf_path: Path):
    doc = fitz.open(str(pdf_path))
    pages = []
    for p in doc:
        pages.append(p.get_text("text"))
    return "\n\n".join(pages)


def split_questions(text: str):
    # naive split by top-level numbers
    parts = NUM_RE.split(text)
    # NUM_RE.split yields: [leading_text, sep1, num1, text1, sep2, num2, text2, ...]
    items = []
    if len(parts) < 3:
        return items
    # skip leading parts[0]
    i = 1
    while i < len(parts):
        # parts[i] is the separator leading (match group 1), parts[i+1] number, parts[i+2] text block
        num = parts[i+1].strip()
        block = parts[i+2].strip()
        items.append((int(num), block))
        i += 3
    return items


def parse_options(block: str):
    # find the start positions of options A-D
    # split by lines starting with A.-D. or (A)
    lines = block.splitlines()
    qtext_lines = []
    options = {}
    current_opt = None
    for ln in lines:
        m = re.match(r'\s*([A-D])(?:[\).:-]+)\s*(.*)', ln)
        if m:
            current_opt = m.group(1)
            options[current_opt] = m.group(2).strip()
        else:
            # continuation line
            if current_opt:
                options[current_opt] = (options[current_opt] + ' ' + ln.strip()).strip()
            else:
                qtext_lines.append(ln)
    qtext = '\n'.join(qtext_lines).strip()
    # convert options dict to list in order A-D if present
    opt_list = []
    for ch in ['A', 'B', 'C', 'D']:
        if ch in options:
            opt_list.append(options[ch])
    return qtext, opt_list


def parse_answer_key(ans_text: str):
    # find pairs like '1 B' or '1. B' or '1) B' or '1-B' or '1:B B' etc.
    mapping = {}
    # Normalize to uppercase letters A-D
    for m in ANS_RE.finditer(ans_text):
        q = int(m.group(1))
        a = m.group(2).upper()
        if a in ['A','B','C','D']:
            mapping[q] = a
    # also try lines like '1. A 2. B 3. C' in sequences without separators
    return mapping


def letter_to_index(letter):
    return ord(letter) - ord('A')


def build_json(test_id: str, filename: str, items_parsed, answers_map):
    items = []
    for num, block in items_parsed:
        qtext, opts = parse_options(block)
        raw_text = block
        if opts:
            qtype = 'multiple_choice'
            correct = []
            if num in answers_map:
                letter = answers_map[num]
                idx = letter_to_index(letter)
                if 0 <= idx < len(opts):
                    correct = [idx]
            confidence = 0.9 if opts and correct else (0.6 if opts else 0.2)
            answer_key = {"choices": opts, "correct": correct}
        else:
            qtype = 'open_answer'
            answer_key = {"sample_answer": None, "rubric": None}
            confidence = 0.4
        items.append({
            "id": f"Q{num}",
            "type": qtype,
            "prompt": qtext if qtext else block.splitlines()[0] if block else None,
            "points": None,
            "media": [],
            "answer_key": answer_key,
            "hints": None,
            "raw_text": raw_text,
            "parse_confidence": confidence
        })
    obj = {
        "id": test_id,
        "title": filename,
        "language": "en",
        "source": {"filename": filename, "page_range": None, "notes": None},
        "items": items,
        "metadata": {"created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "converted_by": "local_converter", "confidence": sum(i['parse_confidence'] for i in items)/len(items) if items else 0.0},
        "validation": {"passed": all(i['parse_confidence']>=0.6 for i in items) if items else False, "errors": [], "warnings": []}
    }
    # add errors if any question has no choices
    for it in items:
        if it['type']=='multiple_choice' and (not it['answer_key']['choices']):
            obj['validation']['errors'].append(f"Q {it['id']} has no parsed choices")
    if any(len(it['answer_key'].get('correct',[]))==0 and it['type']=='multiple_choice' for it in items):
        obj['validation']['warnings'].append('Some multiple_choice items have no correct index matched')
    return obj


def find_pairs():
    tasks = list(TO_CONVERT.glob('tasks-*.pdf'))
    answers = list(TO_CONVERT.glob('ans-*.pdf'))
    ans_map = {a.name.replace('ans-','').replace('.pdf',''): a for a in answers}
    pairs = []
    for t in tasks:
        key = t.name.replace('tasks-','').replace('.pdf','')
        if key in ans_map:
            pairs.append((t, ans_map[key]))
    return pairs


def main():
    pairs = find_pairs()
    if not pairs:
        print('No task-answer pairs found in to_convert_PDF/. Found tasks:', list(TO_CONVERT.glob('tasks-*.pdf')))
        return
    for tasks_pdf, ans_pdf in pairs:
        print('Processing pair:', tasks_pdf.name, '<->', ans_pdf.name)
        tasks_text = extract_text(tasks_pdf)
        ans_text = extract_text(ans_pdf)
        items = split_questions(tasks_text)
        answers_map = parse_answer_key(ans_text)
        test_id = tasks_pdf.stem
        obj = build_json(test_id, tasks_pdf.name, items, answers_map)
        out_path = TESTS_DIR / (test_id + '.json')
        out_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
        print('Wrote', out_path, 'questions:', len(obj['items']))

if __name__ == '__main__':
    main()

