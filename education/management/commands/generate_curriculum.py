"""Generation de cours reels via Ollama (IA locale - zero cout token API).

Usage :
    python manage.py generate_curriculum education/curricula/mathematics_ol.json
    python manage.py generate_curriculum education/curricula/computer_science_ol.json --limit 2
    python manage.py generate_curriculum ... --chapter 1 --lesson 2 --fr --dry-run

Le pipeline :
1. Injecte le sommaire (matiere, chapitres, lecons) en base si absent - statut 'draft'.
2. Pour chaque lecon marquee "generate": true, appelle Ollama en local :
   a. Un appel produit le cours en Markdown brut (le plus fiable avec un petit modele).
   b. Un second appel produit le quiz QCM en JSON (petit, facile a parser).
3. Le contenu est sauvegarde en base en statut 'pending' pour validation humaine ;
   un administrateur le valide ensuite dans l'admin Django (-> 'published').
4. --fr : demande aussi la version francaise du cours (stockee en content_fr).

Aucune connexion externe payante : tout se fait en local avec Ollama.
"""
import json
import urllib.request

from django.core.management.base import BaseCommand, CommandError

OLLAMA_URL = 'http://localhost:11434/api/chat'
DEFAULT_MODEL = 'gemma2:2b'

CONTENT_PROMPT = """\
You are an experienced {subject_name} teacher preparing a lesson for {level} students.

TOPIC : {title}
LEARNING OBJECTIVE : {objective_en}
TARGET DURATION : {minutes} minutes of study.

Write the lesson directly in Markdown (plain text, NO JSON, NO code fences), 450-700 words,
simple language a teenager can follow. Strict structure :
## Learning Objectives
(3 bullet points)
## Explanation
(short sub-sections, concrete step-by-step examples)
## Worked Example
(one exercise solved step by step)
## Common Mistakes
(2-3 bullet points)
## Key Takeaways
(3-5 bullet points, then STOP writing)
"""

QUIZ_PROMPT = """\
You are a teacher. Write a quiz for the lesson below.

LESSON : {title}
OBJECTIVE : {objective_en}

Respond with ONLY this JSON (no code fences, no other text) :
{{"questions": [
  {{"text": "...", "choices": [
    {{"text": "...", "is_correct": true}},
    {{"text": "...", "is_correct": false}},
    {{"text": "...", "is_correct": false}},
    {{"text": "...", "is_correct": false}}]}}
]}}

Rules : exactly 6 questions, exactly 4 choices each, EXACTLY ONE correct choice per question.
Progressive difficulty : definition -> simple application -> short worded problem.
"""

FR_TRANSLATION_PROMPT = """\
You are a translator. Translate the following English lesson to very clear French.
Return ONLY the translated Markdown, preserving headings, formatting and math.
Translate section titles : Learning Objectives -> Objectifs d'apprentissage,
Explanation -> Explication, Worked Example -> Exemple resolu,
Common Mistakes -> Erreurs frequentes, Key Takeaways -> Points cles.
After the Key Takeaways bullet list, STOP.

ENGLISH LESSON :
{content_md}
"""


def clean_json(text):
    """Extrait le premier bloc JSON { ... } meme si le modele ajoute du texte."""
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1:
        raise ValueError("aucun JSON trouve dans la reponse")
    # strict=False : tolere les sauts de ligne bruts dans les chaines
    return json.loads(text[start:end + 1], strict=False)


def ollama_chat(messages, model, temperature=0.4, max_tokens=2800):
    body = json.dumps({
        'model': model,
        'messages': messages,
        'stream': False,
        'options': {
            'temperature': temperature,
            'num_predict': max_tokens,
            'num_ctx': 8192,          # gemma2 coupe a 2048 par defaut
            'repeat_penalty': 1.15,   # evite les boucles infinies
        },
    }).encode('utf-8')
    req = urllib.request.Request(
        OLLAMA_URL, data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=2500) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    return data['message']['content']


def strip_fences(text):
    """Retire des balises ```markdown ... ``` si le modele en ajoute."""
    t = text.strip()
    if t.startswith('```'):
        t = t.split('\n', 1)[1] if '\n' in t else t
        if t.rstrip().endswith('```'):
            t = t.rstrip()[:-3]
    return t.strip()


class Command(BaseCommand):
    help = "Genere des cours reels (Markdown + quiz) via Ollama local"

    def add_arguments(self, parser):
        parser.add_argument('curriculum', help="Fichier JSON du curriculum")
        parser.add_argument('--model', default=DEFAULT_MODEL,
                            help="Modele Ollama a utiliser")
        parser.add_argument('--chapter', type=int,
                            help="Limiter a un chapitre (order)")
        parser.add_argument('--lesson', type=int, help="Limiter a une lecon (order)")
        parser.add_argument('--limit', type=int, help="Nombre max de lecons a generer")
        parser.add_argument('--fr', action='store_true',
                            help="Generer aussi la traduction francaise")
        parser.add_argument('--dry-run', action='store_true',
                            help="N'ecrit pas en base - affiche ce qui serait fait")

    def handle(self, *args, **options):
        from education.models import (Chapter, Choice, Lesson, Question, Quiz,
                                      Subject)

        path = options['curriculum']
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'Fichier introuvable : {path}')

        # 1) Structure en base
        subj = data['subject']
        subject, created = Subject.objects.get_or_create(
            slug=subj['slug'],
            defaults={
                'name': subj['name'],
                'level': subj['level'],
                'description': subj.get('description', ''),
                'icon': subj.get('icon', 'mdi-book-outline'),
                'color': subj.get('color', '#c9a227'),
            })
        msg = 'Creee' if created else 'Existante'
        self.stdout.write(f"[{msg.upper()}] Matiere : {subject} ({subject.slug})")

        generated = 0
        for chap in data['chapters']:
            if options['chapter'] and chap['order'] != options['chapter']:
                continue
            chapter, _ = Chapter.objects.get_or_create(
                subject=subject, order=chap['order'],
                defaults={'title': chap['title'],
                          'title_fr': chap.get('title_fr', ''),
                          'description': chap.get('description', '')})

            for les in chap['lessons']:
                if options['lesson'] and les['order'] != options['lesson']:
                    continue
                lesson, _ = Lesson.objects.get_or_create(
                    chapter=chapter, order=les['order'],
                    defaults={'title': les['title'],
                              'title_fr': les.get('title_fr', ''),
                              'estimated_minutes': les.get('estimated_minutes', 20),
                              'status': 'draft'})

                if not les.get('generate'):
                    continue
                if lesson.content:
                    self.stdout.write(f"[SKIP] Deja generee : {lesson.title}")
                    continue
                if options['limit'] and generated >= options['limit']:
                    self.stdout.write('[STOP] Limite atteinte')
                    return

                self.stdout.write(f"[...] Generation : {lesson.title} ...")
                if options['dry_run']:
                    continue

                # 2) Generation anglaise (texte Markdown brut - le plus robuste)
                prompt = CONTENT_PROMPT.format(
                    subject_name=subject.name, level=subject.get_level_display(),
                    title=les['title'],
                    objective_en=les['objective_en'],
                    minutes=les.get('estimated_minutes', 20))
                try:
                    raw = ollama_chat(
                        [{'role': 'user', 'content': prompt}], options['model'])
                    lesson.content = strip_fences(raw)
                except Exception as e:
                    raise CommandError(
                        f"[ERREUR] Ollama sur '{les['title']}' : {e}")
                if len(lesson.content) < 400:
                    self.stderr.write(
                        f"[ATTENTION] Contenu anormalement court "
                        f"({len(lesson.content)} car.)")
                lesson.status = 'pending'
                lesson.save()
                self.stdout.write(f"  + Contenu : {len(lesson.content)} car.")

                # 3) Quiz (petit JSON separe - plus fiable pour les petits modeles)
                quiz_prompt = QUIZ_PROMPT.format(
                    title=les['title'], objective_en=les['objective_en'])
                for attempt in range(2):
                    try:
                        raw_q = ollama_chat(
                            [{'role': 'user', 'content': quiz_prompt}],
                            options['model'], temperature=0.3, max_tokens=1800)
                        quiz_data = clean_json(raw_q)
                        questions = quiz_data.get('questions', [])
                        if not questions:
                            raise ValueError('pas de questions')
                        quiz = Quiz.objects.create(
                            lesson=lesson, title=f"Quiz - {lesson.title}",
                            pass_score=60)
                        for i, q in enumerate(questions, start=1):
                            question = Question.objects.create(
                                quiz=quiz, text=q['text'], order=i)
                            choices = q.get('choices', [])
                            corrects = [i for i, ct in enumerate(choices)
                                        if ct.get('is_correct')]
                            if not corrects:
                                if choices:
                                    corrects = [0]
                            elif len(corrects) > 1:
                                corrects = corrects[:1]  # 1 seule bonne reponse
                            for i, ch in enumerate(choices):
                                Choice.objects.create(
                                    question=question, text=ch['text'],
                                    is_correct=i in corrects)
                        self.stdout.write(f"  + Quiz : {len(questions)} questions")
                        break
                    except Exception as e:
                        if attempt == 1:
                            self.stderr.write(
                                f"  [ATTENTION] Quiz non genere pour "
                                f"'{lesson.title}' : {e}")

                # 4) Traduction francaise
                if options['fr'] and lesson.content:
                    self.stdout.write("  [...] Traduction francaise...")
                    raw_fr = ollama_chat(
                        [{'role': 'user',
                          'content': FR_TRANSLATION_PROMPT.format(
                              content_md=lesson.content[:5000])}],
                        options['model'], temperature=0.2, max_tokens=2800)
                    lesson.content_fr = strip_fences(raw_fr)
                    lesson.save()

                generated += 1
                self.stdout.write(self.style.SUCCESS(
                    f"[OK] Lecon prete : {lesson.title}"))

        self.stdout.write(self.style.SUCCESS(
            f"\n[TERMINE] {generated} lecons generees "
            "(statut 'pending' - valider depuis l'admin)."))
