"""Traduit en francais les lecons qui ont du contenu anglais mais pas de version FR.

Usage : python manage.py shell -c "exec(open('translate_lessons.py', encoding='utf-8').read())"
        IDs dans LESSON_IDS ci-dessous (par defaut : la lecon pilote).
"""
from education.management.commands.generate_curriculum import (
    FR_TRANSLATION_PROMPT, ollama_chat, strip_fences)
from education.models import Lesson

LESSON_IDS = [15]

for lesson_id in LESSON_IDS:
    lesson = Lesson.objects.get(id=lesson_id)
    if not lesson.content:
        print(f'[SKIP] pas de contenu : {lesson.title}')
        continue
    if lesson.content_fr:
        print(f'[SKIP] deja traduite : {lesson.title}')
        continue
    print(f'[...] Traduction : {lesson.title}')
    raw = ollama_chat(
        [{'role': 'user',
          'content': FR_TRANSLATION_PROMPT.format(
              content_md=lesson.content[:5000])}],
        'gemma2:2b', temperature=0.2, max_tokens=2800)
    lesson.content_fr = strip_fences(raw)
    lesson.save()
    print(f'[OK] FR : {lesson.title} ({len(lesson.content_fr)} car.)')
