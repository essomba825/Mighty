"""Interroge Codex (OpenAI) avec le contexte du projet.

Usage :
    python manage.py codex_chat --models
    python manage.py codex_chat "Que manque-t-il dans le module education ?"
    python manage.py codex_chat --prompt-file docs/brief.md --out docs/reponse.md
    python manage.py codex_chat --context docs/brief.md "Redonne le plan de cours"

Sans argument positionnel, la commande lit stdin : on peut donc lui piping
un long prompt sansBAT perler de guillemets dans PowerShell.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from education import codex_client as cx


class Command(BaseCommand):
    help = "Interroge un modele Codex/OpenAI avec le contexte du projet"

    def add_arguments(self, parser):
        parser.add_argument('question', nargs='?', default='',
                            help='Question ou tache (sinon stdin)')
        parser.add_argument('--context', default='',
                            help='Fichier de contexte prependu au prompt')
        parser.add_argument('--prompt-file', default='',
                            help='Fichier contenant le prompt complet')
        parser.add_argument('--model', default=cx.MODEL_DEFAULT)
        parser.add_argument('--effort', default=cx.EFFORT_DEFAULT,
                            choices=['low', 'medium', 'high'],
                            help='Effort de raisonnement : cout vs qualite')
        parser.add_argument('--system', default='',
                            help='Instruction systeme')
        parser.add_argument('--out', default='',
                            help='Ecrit la reponse dans ce fichier')
        parser.add_argument('--max-tokens', type=int, default=8000)
        parser.add_argument('--models', action='store_true',
                            help='Liste les modeles accessibles et quitte')
        parser.add_argument('--timeout', type=int, default=600)

    def handle(self, *args, **options):
        if options['models']:
            for nom in cx.list_models():
                self.stdout.write(nom)
            return

        question = options['question'].strip()
        if not question:
            import sys
            question = sys.stdin.read().strip()
        if not question and not options['prompt_file']:
            raise CommandError('Donne une question, --prompt-file, ou pipe stdin.')

        if options['prompt_file']:
            question = Path(options['prompt_file']).read_text(
                encoding='utf-8') + '\n\n' + question

        if options['context']:
            contexte = Path(options['context']).read_text(encoding='utf-8')
            question = (
                f'# Contexte du projet Mighty Pulse\n\n{contexte}\n\n'
                f'# Demande\n\n{question}')

        try:
            resultat = cx.chat(question, system=options['system'] or None,
                               model=options['model'], effort=options['effort'],
                               max_output_tokens=options['max_tokens'],
                               timeout=options['timeout'])
        except cx.CodexError as exc:
            raise CommandError(str(exc)) from exc

        texte = resultat['text']
        if options['out']:
            Path(options['out']).write_text(texte, encoding='utf-8')
            self.stdout.write(self.style.SUCCESS(f'[OK] {options["out"]}'))
        else:
            self.stdout.write(texte)

        usage = resultat.get('usage') or {}
        self.stderr.write(self.style.WARNING(
            f'modele={resultat.get("model")} '
            f'tokens_in={usage.get("input_tokens")} '
            f'tokens_out={usage.get("output_tokens")}'))

    def _prefix(self):
        return f'[{settings.BASE_DIR}] '