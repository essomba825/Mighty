from accounts.journal import record
from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (Chapter, Choice, Concept, ConceptState, ExerciseAttempt,
                     Hint, Lesson, LessonMastery, LessonProgress, Question, Quiz,
                     QuizAttempt, Subject, TutorMessage)
from .review import due_questions
from .serializers import (ChapterSerializer, HintSerializer, LessonListSerializer,
                          LessonMasterySerializer, LessonSerializer,
                          QuizAttemptSerializer, QuizSerializer, QuizSubmissionSerializer,
                          StepSerializer, SubjectSerializer)


class IsTeacherOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and (user.is_staff or user.role == 'teacher')


class CanManageLesson(permissions.BasePermission):
    """Un enseignant ne modifie que ses leçons ; l'admin gère tout."""
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff or obj.teacher == request.user


class SubjectViewSet(viewsets.ModelViewSet):
    serializer_class = SubjectSerializer
    queryset = Subject.objects.all()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    @action(detail=True, permission_classes=[permissions.AllowAny])
    def curriculum(self, request, pk=None):
        """Programme complet d'une matière : chapitres + fiches leçons publiées."""
        subject = self.get_object()
        chapters = Chapter.objects.filter(subject=subject).prefetch_related('lessons')
        return Response(ChapterSerializer(
            chapters, many=True, context={'request': request}).data)

    @action(detail=True, methods=['get'],
            permission_classes=[permissions.AllowAny])
    def path(self, request, pk=None):
        """Parcours de l'eleve dans cette matiere : maitrise par chapitre,
        et le point de depart recommande.

        Aucun blocage : l'eleve choisit librement, meme sans compte. La progression
        est alors vide (0 %) plutot qu'une erreur 500 : `request.user` vaut
        `AnonymousUser` pour un visiteur non connecte, ce qui fait echouer le
        filtre sur `student`.
        """
        from django.utils import timezone
        subject = self.get_object()
        chapters = Chapter.objects.filter(subject=subject).prefetch_related(
            'lessons', 'concepts').order_by('order')

        if request.user.is_authenticated:
            attempts = ExerciseAttempt.objects.filter(
                student=request.user,
                question__step__lesson__chapter__subject=subject)
            solved_ids = set(attempts.filter(is_correct=True)
                             .values_list('question_id', flat=True))
        else:
            solved_ids = set()

        rows = []
        for chapter in chapters:
            lessons = chapter.lessons.filter(status='published')
            done = total = 0
            for lesson in lessons:
                required = [s.question_id for s in lesson.steps.filter(required=True)]
                total += len(required)
                done += sum(1 for qid in required if qid in solved_ids)
            rows.append({
                'chapter_id': chapter.id,
                'title': chapter.title,
                'title_fr': chapter.title_fr,
                'order': chapter.order,
                'lessons_count': lessons.count(),
                'steps_done': done,
                'steps_total': total,
                'mastery': round(done / total * 100) if total else 0,
            })

        # Recommande : premiere lecon dont une etape-required reste a faire
        recommended = None
        for chapter in chapters:
            for lesson in chapter.lessons.filter(status='published').order_by('order'):
                required = [s.question_id for s in lesson.steps.filter(required=True)]
                if not required:
                    continue
                done_here = sum(1 for qid in required if qid in solved_ids)
                if done_here < len(required):
                    recommended = {
                        'lesson_id': lesson.id,
                        'title': lesson.title,
                        'title_fr': lesson.title_fr,
                        'subject_slug': subject.slug,
                        'steps_total': len(required),
                        'steps_done': done_here,
                    }
                    break
            if recommended:
                break

        if request.user.is_authenticated:
            mastered = LessonMastery.objects.filter(
                student=request.user, lesson__chapter__subject=subject,
                mastered_at__isnull=False).count()
            due = ConceptState.objects.filter(
                student=request.user, concept__chapter__subject=subject,
                due_at__lte=timezone.localdate()).count()
        else:
            mastered = due = 0

        return Response({
            'subject': SubjectSerializer(subject, context={'request': request}).data,
            'chapters': rows,
            'recommended': recommended,
            'due_reviews': due,
            'mastered_lessons': mastered,
        })


class LessonViewSet(viewsets.ModelViewSet):
    """Catalogue et programme publics ; lecture du contenu reservee, sauf
    lecons explicitement ouvertes (`is_public`)."""

    def _est_enseignant(self, user):
        return bool(user and user.is_authenticated
                    and (user.is_staff or user.role == 'teacher'))

    def get_serializer_class(self):
        if self.action == 'list':
            return LessonListSerializer
        return LessonSerializer

    # Ecriture reservee au staff ou a l'enseignant auteur.
    ACTIONS_ENSEIGNANT = {'publish', 'reject', 'quality_check', 'add_quiz',
                          'validate'}

    # Actions qui portent sur la progression ou la conversation d'un eleve.
    # Elles exigent un compte, GET compris : `LessonMastery(student=AnonymousUser)`
    # n'existe pas, et une invite a se connecter est plus utile qu'une 500.
    ACTIONS_ETUDIANT = {'progress', 'complete', 'tutor', 'tutor_history',
                        'my_progress'}

    # Actions qui livrent le CONTENU d'une lecon. Un visiteur non connecte y
    # a acces seulement si la lecon est cochee publique ; le catalogue, lui,
    # reste ouvert pour qu'il puisse decouvrir l'offre avant de s'inscrire.
    ACTIONS_CONTENU = {'retrieve', 'steps', 'resources'}

    def get_permissions(self):
        if self.action == 'create':
            return [IsTeacherOrAdmin()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), CanManageLesson()]
        if self.action in self.ACTIONS_ENSEIGNANT:
            return [IsTeacherOrAdmin()]
        if self.action in self.ACTIONS_ETUDIANT:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = Lesson.objects.select_related('chapter__subject', 'teacher')
        user = self.request.user
        enseignant = self._est_enseignant(user)

        if not enseignant:
            # Le catalogue public ne montre que les lecons publiees : ni
            # brouillon, ni attente, quel que soit le lesson demandee.
            qs = qs.filter(status='published')

        subject = self.request.query_params.get('subject')
        chapter = self.request.query_params.get('chapter')
        status_param = self.request.query_params.get('status')
        if subject:
            qs = qs.filter(chapter__subject_id=subject)
        if chapter:
            qs = qs.filter(chapter_id=chapter)
        if status_param in dict(Lesson.Status.choices) and enseignant:
            qs = qs.filter(status=status_param)

        # Contenu : la porte reste fermee pour qui n'a pas de compte et que la lecon
        # n'a pas ouverte. Tout membre connecte, en revanche, lit les lecons
        # publiees : c'est le sens du §10, et une fois le catalogue public le
        # cache n'apporterait plus rien. Seul le brouillon et l'attente
        # restent reserves aux enseignants, ce que le filtre du dessus fait
        # deja.
        if self.action in self.ACTIONS_CONTENU and not (
                user and user.is_authenticated):
            qs = qs.filter(is_public=True)
        return qs

    def create(self, request, *args, **kwargs):
        """Creation d'une lecon par un prof (brouillon) ; le chapitre se choisit
        ou se cree dans la foulee. On supprime les champs d'ecriture qui ne sont
        pas des colonnes de Lesson."""
        data = dict(request.data)
        chapter = None
        if data.get('chapter'):
            chapter = Chapter.objects.filter(pk=data['chapter']).first()
        elif data.get('new_chapter_title') and data.get('subject_id_write'):
            subject = Subject.objects.filter(pk=data['subject_id_write']).first()
            if subject:
                chapter = Chapter.objects.create(
                    subject=subject,
                    order=(Chapter.objects.filter(subject=subject).count() + 1),
                    title=data['new_chapter_title'],
                    title_fr=data.get('new_chapter_title_fr', ''))
        if chapter is None:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                'chapter': 'Choisir un chapitre existant '
                           '(ou bien "new_chapter_title" et "subject_id_write").'})
        # rien que le modele connait
        lesson_fields = {k: v for k, v in data.items()
                         if k in ('title', 'title_fr', 'summary', 'summary_fr',
                                  'content', 'content_fr', 'video_url', 'kind',
                                  'order', 'estimated_minutes',
                                  'objectives', 'objectives_fr')}
        lesson = Lesson.objects.create(
            chapter=chapter, **lesson_fields,
            order=lesson_fields.get('order') or (
                Lesson.objects.filter(chapter=chapter).count() + 1),
            teacher=request.user,
            status='published' if request.user.is_staff else 'pending')
        return Response(
            self.get_serializer(lesson).data, status=status.HTTP_201_CREATED)

    # Les actions admin sur le cycle de vie d'une lecon sont reservees au staff et admins.
    def _is_staff(self, request):
        return bool(
            request.user.is_authenticated and (
                request.user.is_staff or 
                request.user.is_superuser or 
                getattr(request.user, 'role', '') in ('admin', 'teacher')
            )
        )

    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """Publie une lecon en attente, apres controle qualite.

        On n'appuie pas sur le bouton sans verifier : le controle qualite doit
        passer avant la mise en ligne, sinon on garde la lecon en attente et
        on explique pourquoi.
        """
        if not self._is_staff(request):
            return Response({'detail': 'Reserve au personnel.'}, status=403)
        lesson = self.get_object()
        if lesson.status != 'pending':
            return Response(
                {'detail': f"Statut inattendu ({lesson.status}). "
                           f"Seule une lecon en attente peut etre publiee."},
                status=400)
        from django.db.models import Count
        from education.content_quality import check_lesson

        lesson = (Lesson.objects.filter(pk=lesson.pk)
                  .prefetch_related(
                      'steps__question__choices', 'steps__question__hints',
                      'quizzes__questions__choices', 'quizzes__questions__hints')
                  .annotate(step_count=Count('steps', distinct=True)).first())
        errors, warnings = [], []
        check_lesson(lesson, errors, warnings)
        if errors:
            return Response({'errors': errors, 'warnings': warnings}, status=400)
        lesson.status = 'published'
        lesson.save(update_fields=['status'])
        record(request, action='publish', model_name='Lesson',
               object_id=lesson.pk,
               summary=f'Publication de « {lesson.title} »')
        return Response({'status': 'published', 'warnings': warnings})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Rejette une lecon en attente (retourne en brouillon)."""
        if not self._is_staff(request):
            return Response({'detail': 'Reserve au personnel.'}, status=403)
        lesson = self.get_object()
        if lesson.status != 'pending':
            return Response({'detail': 'Statut inattendu.'}, status=400)
        lesson.status = 'draft'
        lesson.save(update_fields=['status'])
        record(request, action='reject', model_name='Lesson',
               object_id=lesson.pk,
               summary=f'Rejet de « {lesson.title} » vers brouillon')
        return Response({'status': 'draft'})

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Liste des lecons en attente de validation, pour l'admin."""
        if not self._is_staff(request):
            return Response({'detail': 'Reserve au personnel.'}, status=403)
        qs = self.filter_queryset(
            Lesson.objects.filter(status='pending')
            .select_related('chapter__subject', 'teacher')
            .order_by('created_at'))
        return Response(LessonListSerializer(
            qs, many=True, context={'request': request}).data)

    @action(detail=True, methods=['get'])
    def quality_check(self, request, pk=None):
        """Controle qualite d'une lecon sans la publier. Reserve au staff."""
        if not self._is_staff(request):
            return Response({'detail': 'Reserve au personnel.'}, status=403)
        from django.db.models import Count
        from education.content_quality import check_lesson
        lesson = (Lesson.objects.filter(pk=pk)
                  .prefetch_related(
                      'steps__question__choices', 'steps__question__hints',
                      'quizzes__questions__choices', 'quizzes__questions__hints')
                  .annotate(step_count=Count('steps', distinct=True)).first())
        if lesson is None:
            return Response({'detail': 'Lecon introuvable.'}, status=404)
        errors, warnings = [], []
        check_lesson(lesson, errors, warnings)
        return Response({'errors': errors, 'warnings': warnings,
                         'step_count': lesson.step_count})

    @action(detail=True, methods=['post'])
    def add_quiz(self, request, pk=None):
        """Ajoute un quiz multi-choix a une lecon en attente ou en brouillon.

        Le formateur saisit en texte une question par ligne :
        `Question | bonne reponse | option1 | option2 | option3`
        La premiere option est la bonne ; le front les melange a l'affichage.
        """
        lesson = self.get_object()
        user = request.user
        if not (user.is_staff or (user.role == 'teacher' and lesson.teacher_id == user.id)):
            return Response({'detail': 'Reserve a l auteur ou au personnel.'}, status=403)
        if lesson.status == 'published':
            return Response({'detail': 'La lecon est deja publiee; demander a un admin.'},
                            status=400)

        raw_lines = request.data.get('questions_text', '').strip()
        if not raw_lines:
            return Response({'detail': 'Aucune question fournie.'}, status=400)

        quiz, _ = Quiz.objects.get_or_create(
            lesson=lesson, defaults={'title': lesson.title})
        quiz.title_fr = lesson.title_fr or lesson.title
        quiz.save()

        crees = 0
        for order, line in enumerate(raw_lines.splitlines(), start=1):
            line = line.strip()
            if not line or '|' not in line:
                continue
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) < 2:
                continue
            text_en = parts[0]
            correct = parts[1]
            wrongs = parts[2:5]
            question = Question.objects.create(
                quiz=quiz, order=order, kind=Question.Kind.MCQ, text=text_en,
                explanation='')
            for idx, choice_text in enumerate([correct] + wrongs):
                Choice.objects.create(
                    question=question, text=choice_text,
                    is_correct=(idx == 0))
            crees += 1
        return Response({'created': crees}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def steps(self, request, pk=None):
        """Micro-etapes de la lecon : le parcours du LessonPlayer.

        Renvoie aussi l'avancement de l'eleve sur chaque etape pour qu'il
        reprenne exactement ou il s'etait arrete.
        """
        lesson = self.get_object()
        steps = lesson.steps.prefetch_related('question__choices').all()
        data = StepSerializer(steps, many=True, context={'request': request}).data
        solved = set()
        if request.user.is_authenticated:
            solved = set(ExerciseAttempt.objects
                         .filter(student=request.user, question__step__lesson=lesson,
                                 is_correct=True)
                         .values_list('question_id', flat=True))
        for step in data:
            step['solved'] = bool(step.get('question') and step['question']['id'] in solved)
        return Response(data)

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Etat de l'eleve sur cette lecon : etapes resolues, maitrise."""
        lesson = self.get_object()
        steps = list(lesson.steps.all())
        mastery, _ = LessonMastery.objects.get_or_create(
            student=request.user, lesson=lesson,
            defaults={'required': sum(1 for s in steps if s.required)})
        required_ids = [s.question_id for s in steps if s.required and s.question_id]
        solved = set(ExerciseAttempt.objects
                     .filter(student=request.user, question_id__in=required_ids,
                             is_correct=True)
                     .values_list('question_id', flat=True))
        mastery.validated = len(solved)
        mastery.required = len(required_ids)
        if mastery.is_mastered and not mastery.mastered_at:
            from django.utils import timezone
            mastery.mastered_at = timezone.now()
        elif not mastery.is_mastered:
            mastery.mastered_at = None
        mastery.save()
        return Response({
            'mastery': LessonMasterySerializer(mastery).data,
            'required_total': len(required_ids),
            'required_solved': len(solved),
            'xp': 10 * len(solved),
        })

    @action(detail=True, methods=['post', 'delete'])
    def complete(self, request, pk=None):
        """Marque la leçon comme terminée (POST) ou retire la marque (DELETE)."""
        if request.method == 'POST':
            LessonProgress.objects.get_or_create(
                lesson=self.get_object(), student=request.user)
            return Response({'completed': True}, status=status.HTTP_201_CREATED)
        LessonProgress.objects.filter(lesson_id=pk, student=request.user).delete()
        return Response({'completed': False}, status=status.HTTP_200_OK)

    @action(detail=False)
    def my_progress(self, request):
        """Progression de l'utilisateur connecté, groupee par matiere."""
        progress = (LessonProgress.objects
                    .filter(student=request.user)
                    .select_related('lesson__chapter__subject'))
        lessons = LessonListSerializer(
            [p.lesson for p in progress], many=True,
            context={'request': request}).data
        return Response([
            {'lesson': lesson, 'completed_at': str(p.completed_at)}
            for lesson, p in zip(lessons, progress)
        ])

    @action(detail=True, methods=['post'])
    def tutor(self, request, pk=None):
        """Répétiteur IA local (Ollama) – conversation pédagogique sur la leçon.

        POST {message: "..."} -> {"reply": "..."}
        Max : 30 messages par leçon par élève (protection contre la gourmandise).
        """
        from django.conf import settings
        from .management.commands.generate_curriculum import ollama_chat

        lesson = self.get_object()
        message = (request.data.get('message') or '').strip()
        if not message:
            return Response({'detail': 'Message vide.'}, status=400)
        if len(message) > 2000:
            return Response({'detail': 'Message trop long (2000 caractères max).'}, status=400)

        count = TutorMessage.objects.filter(lesson=lesson, student=request.user).count()
        if count >= 60:
            return Response({
                'detail': "Limite de conversation atteinte pour cette leçon.",
            }, status=429)

        history = list(TutorMessage.objects.filter(
            lesson=lesson, student=request.user)
            .order_by('-created_at')[:16])[::-1]
        messages = [{
            'role': 'system',
            'content': (
                "Tu es 'Mighty', le répétiteur bienveillant de l'association Mega Mighty "
                "Sixers. Tu aides un élève sur la leçon ci-dessous. Réponds en français "
                "clair, concis (max 150 mots), avec des exemples concrets si utile. "
                "Encourage, ne donne jamais la réponse brute d'un exercice : guide.\n\n"
                f"LEÇON : {lesson.title}\n"
                f"OBJECTIF : {'; '.join(lesson.objectives or [])}\n"
                f"CONTENU :\n{lesson.content[:2500]}\n"
                f"CONTENU (français) :\n{lesson.content_fr[:1500]}"
            ),
        }]
        for msg in history:
            messages.append({
                'role': 'user' if msg.role == 'student' else 'assistant',
                'content': msg.content,
            })
        messages.append({'role': 'user', 'content': message})

        try:
            reply = ollama_chat(messages, 'gemma2:2b', temperature=0.5, max_tokens=600)
        except Exception as e:
            return Response({'detail': f'Tutor IA indisponible : {e}'}, status=503)

        TutorMessage.objects.bulk_create([
            TutorMessage(lesson=lesson, student=request.user, role='student', content=message),
            TutorMessage(lesson=lesson, student=request.user, role='tutor', content=reply),
        ])
        return Response({'reply': reply, 'messages_left': 60 - count - 2})

    @action(detail=True, methods=['get'])
    def tutor_history(self, request, pk=None):
        """Historique de la conversation (les 16 derniers échanges)."""
        lesson = self.get_object()
        msgs = list(TutorMessage.objects.filter(
            lesson=lesson, student=request.user)
            .order_by('-created_at')[:32])[::-1]
        return Response([{
            'role': m.role, 'content': m.content,
            'created_at': str(m.created_at),
        } for m in msgs])


LEITNER_DAYS = [1, 2, 4, 8, 16]


def _update_spacing(student, question, is_correct):
    """Repetition espacee (boites de Leitner) sur le concept rattache.

    L'exercice n'etant pas forcement rattache a un Concept, on retombe sur le
    chapitre de la lecon : c'est deja une unite de revision plus fine que la
    matiere, et ca evite d'exiger le lien concept/question tant que le contenu
    n'a pas ete reecrit.
    """
    chapter_id = None
    if question.quiz_id:
        chapter_id = question.quiz.lesson.chapter_id
    elif getattr(question, 'step', None):
        chapter_id = question.step.lesson.chapter_id
    if not chapter_id:
        return
    concepts = Concept.objects.filter(chapter_id=chapter_id, required=True)[:1]
    if not concepts:
        return
    concept = concepts[0]
    state, _ = ConceptState.objects.get_or_create(student=student, concept=concept)
    from django.utils import timezone
    state.seen_count += 1
    state.last_seen = timezone.now()
    if is_correct:
        state.correct_count += 1
        state.box = min(state.box + 1, len(LEITNER_DAYS) - 1)
    else:
        state.box = max(state.box - 1, 0)
    state.strength = round(state.correct_count / state.seen_count, 3) if state.seen_count else 0.0
    state.due_at = timezone.localdate() + timezone.timedelta(
        days=LEITNER_DAYS[state.box])
    state.save()


class ExerciseViewSet(viewsets.ViewSet):
    """Exercices interactifs du LessonPlayer.

    Regles :
    - l'indice ne s'obtient qu'a la demande, un par un (principe Khan) ;
    - l'eleve peut reessayer indefiniment, l'echec n'est jamais puni ;
    - `explanation` n'est renvoyee qu'apres une tentative.
    """

    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _visible_questions(request):
        """Questions accessibles a cet utilisateur.

        Une lecon non publiee n'existe pas pour un eleve : sans ce filtre, il
        suffit de deviner un id pour obtenir la bonne reponse et l'explication
        d'un contenu encore en relecture. L'enseignant, lui, doit pouvoir
        tester les etapes d'un brouillon avant de le publier.
        """
        qs = Question.objects.all()
        if request.user.is_authenticated and (request.user.is_staff
                                             or request.user.role == 'teacher'):
            return qs
        return qs.filter(quiz__lesson__status='published') | qs.filter(
            step__lesson__status='published')

    def _question(self, request, pk):
        return self._visible_questions(request).filter(pk=pk).select_related(
            'step').first()

    @action(detail=False, methods=['get'])
    def review(self, request):
        """Queue de revision quotidienne : les questions deja travaillees qui
        sont a refaire (echec recent ou succes qui remonte a trop longtemps).

        Ne s'appuie pas sur les Concept, quasi vides en base, mais sur
        `ExerciseAttempt`, qui est la seule donnee reelle au niveau question.
        Chaque tentative met a jour la queue ; l'eleve n'a pas besoin de
        s'inscrire.
        """
        from .serializers import QuestionPublicSerializer

        queue = due_questions(request.user)
        data = [
            {
                'question': QuestionPublicSerializer(
                    q, context={'request': request}).data,
                'lesson_id': (q.step.lesson_id if getattr(q, 'step', None)
                              else q.quiz.lesson_id if q.quiz else None),
                'lesson_title': (q.step.lesson.title if getattr(q, 'step', None)
                                 else q.quiz.lesson.title if q.quiz else None),
                'lesson_title_fr': (q.step.lesson.title_fr
                                    if getattr(q, 'step', None)
                                    else q.quiz.lesson.title_fr if q.quiz else None),
                'subject_slug': (q.step.lesson.chapter.subject.slug
                                 if getattr(q, 'step', None)
                                 else q.quiz.lesson.chapter.subject.slug
                                 if q.quiz else None),
                'box': box,
                'overdue_days': overdue,
                'is_retry': is_retry,
            }
            for q, box, overdue, is_retry in queue
        ]
        return Response({
            'count': len(data),
            'failed_count': sum(1 for r in data if r['is_retry']),
            'questions': data,
        })

    @action(detail=True, methods=['get'])
    def reveal_hint(self, request, pk=None):
        """Rend l'indice suivant, un par un (principe Khan/Brilliant).

        L'index vient de l'etape courante : on ne lit pas les indices d'un
        autre essai, et l'eleve peut toujours redescendre la piste.
        """
        question = self._question(request, pk)
        if not question:
            return Response({'detail': 'Exercice introuvable.'}, status=404)
        total = question.hints.count()
        step = request.query_params.get('step')
        try:
            n = int(step)
        except (TypeError, ValueError):
            n = 1
        if n < 1:
            n = 1
        hint = question.hints.filter(order=n).first()
        if not hint:
            return Response({'hint': None, 'step_number': n,
                             'hints_left': 0, 'hints_total': total})
        return Response({'hint': HintSerializer(hint).data, 'step_number': n,
                         'hints_left': max(total - n, 0), 'hints_total': total})

    @action(detail=True, methods=['post'])
    def attempt(self, request, pk=None):
        """Corrige une reponse, met a jour la maitrise et la repetition espacee."""
        from .grading import grade

        question = self._question(request, pk)
        if not question:
            return Response({'detail': 'Exercice introuvable.'}, status=404)

        given = request.data.get('answer')
        if not isinstance(given, dict):
            return Response({'detail': 'Reponse invalide.'}, status=400)
        hints_used = max(int(request.data.get('hints_used') or 0), 0)
        tries = max(int(request.data.get('tries') or 1), 1)
        time_spent_ms = max(int(request.data.get('time_spent_ms') or 0), 0)

        is_correct = grade(question, given)
        # « premier essai » = aucune tentative precedente et reponse juste
        previous_attempts = ExerciseAttempt.objects.filter(
            student=request.user, question=question).count()
        is_first_try = is_correct and previous_attempts == 0
        ExerciseAttempt.objects.create(
            student=request.user, question=question, given=given,
            is_correct=is_correct, is_first_try=is_first_try,
            hints_used=hints_used, tries=tries, time_spent_ms=time_spent_ms)
        _update_spacing(request.user, question, is_correct)

        # Maitrise de la lecon : recalculee a partir des etapes-required
        mastery = None
        step = getattr(question, 'step', None)
        if step:
            required_ids = [s.question_id for s in step.lesson.steps.all()
                            if s.required and s.question_id]
            solved = set(ExerciseAttempt.objects.filter(
                student=request.user, question_id__in=required_ids,
                is_correct=True).values_list('question_id', flat=True))
            from django.utils import timezone
            mastery, _ = LessonMastery.objects.get_or_create(
                student=request.user, lesson=step.lesson,
                defaults={'required': len(required_ids)})
            mastery.required = len(required_ids)
            mastery.validated = len(solved)
            if mastery.is_mastered and not mastery.mastered_at:
                mastery.mastered_at = timezone.now()
            elif not mastery.is_mastered:
                mastery.mastered_at = None
            mastery.save()

        return Response({
            'is_correct': is_correct,
            'first_try': is_first_try,
            'explanation': question.explanation,
            'explanation_fr': question.explanation_fr,
            'hints_used': hints_used,
            # la reponse correcte n'est envoyee qu'apres tentative
            'correct_choice_id': (question.choices.filter(is_correct=True)
                                  .values_list('id', flat=True).first()
                                  if question.kind == Question.Kind.MCQ else None),
            'mastery': LessonMasterySerializer(mastery).data if mastery else None,
        }, status=status.HTTP_200_OK)


class QuizViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Quiz.objects.filter(
            lesson__status='published').prefetch_related('questions__choices')

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Corrige les réponses et renvoie la revue détaillée (bonne réponse + explication)."""
        quiz = self.get_object()
        serializer = QuizSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answers = serializer.validated_data['answers']

        questions = {q.id: q for q in quiz.questions.prefetch_related('choices')}
        score = 0
        review = []
        for q in questions.values():
            choice_id = answers.get(str(q.id)) or answers.get(q.id)
            chosen = q.choices.filter(id=choice_id).first()
            correct = q.choices.filter(is_correct=True).first()
            is_ok = correct is not None and chosen == correct
            score += 1 if is_ok else 0
            review.append({
                'question_id': q.id,
                'text': q.text,
                'text_fr': q.text_fr,
                'explanation': q.explanation,
                'explanation_fr': q.explanation_fr,
                'choice_id': chosen.id if chosen else None,
                'choice_text': chosen.text if chosen else None,
                'choice_text_fr': chosen.text_fr if chosen else None,
                'correct_choice_text': correct.text if correct else None,
                'correct_choice_text_fr': correct.text_fr if correct else None,
                'is_correct': is_ok,
            })

        attempt = QuizAttempt.objects.create(
            quiz=quiz, student=request.user, score=score, total=len(questions))
        data = QuizAttemptSerializer(attempt).data
        data['review'] = review
        return Response(data, status=status.HTTP_201_CREATED)


class QuizAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    """Suivi de progression : l'élève voit ses résultats, l'admin/prof voit tout."""
    serializer_class = QuizAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = QuizAttempt.objects.select_related(
            'quiz__lesson__chapter__subject', 'student')
        user = self.request.user
        if user.is_staff or user.role == 'teacher':
            return qs
        return qs.filter(student=user)
