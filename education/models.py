from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Level(models.TextChoices):
    ORDINARY = 'ol', 'GCE Ordinary Level'
    ADVANCED = 'al', 'GCE Advanced Level'


class Subject(models.Model):
    """Matière : Mathematics, Computer Science, Physics..."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    level = models.CharField(max_length=2, choices=Level.choices)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=60, default='mdi-book-outline',
                            verbose_name="Icône (MDI)")
    color = models.CharField(max_length=9, default='#c9a227',
                             verbose_name="Couleur de la matière", help_text="Hex, ex. #e05252")
    image_url = models.URLField(blank=True, default='', verbose_name="Image de couverture",
                                help_text="URL hotlink (Wikimedia Commons, libre de droits)")

    class Meta:
        ordering = ['level', 'name']
        unique_together = ('name', 'level')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f'{self.name}-{self.level}')
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.get_level_display()})'


class Chapter(models.Model):
    """Chapitre au sein d'une matière."""

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='chapters')
    order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200, verbose_name="Titre (anglais prioritaire)")
    title_fr = models.CharField(max_length=200, blank=True, verbose_name="Titre (français)")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['subject', 'order']

    def __str__(self):
        return f'{self.subject.slug} — {self.order}. {self.title}'


class Lesson(models.Model):
    """Leçon : contenu structuré bilingue (anglais prioritaire) + ressources + quiz."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Brouillon'
        PENDING = 'pending', "En attente de validation"
        PUBLISHED = 'published', 'Publié'

    class Kind(models.TextChoices):
        LESSON = 'lesson', 'Leçon'
        EXAM_PAPER = 'exam_paper', "Ancien sujet d'examen"

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='lessons')
    order = models.PositiveIntegerField(default=1)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.LESSON)
    title = models.CharField(max_length=200)
    title_fr = models.CharField(max_length=200, blank=True, verbose_name="Titre (français)")
    summary = models.TextField(blank=True, verbose_name="Résumé (anglais)")
    summary_fr = models.TextField(blank=True, verbose_name="Résumé (français)")
    objectives = models.JSONField(default=list, blank=True,
                                  verbose_name="Objectifs d'apprentissage (liste)")
    objectives_fr = models.JSONField(default=list, blank=True,
                                     verbose_name="Objectifs d'apprentissage (français)")
    content = models.TextField(blank=True, verbose_name="Cours (Markdown, anglais)")
    content_fr = models.TextField(blank=True, verbose_name="Cours (Markdown, français)")
    video_url = models.URLField(blank=True, verbose_name="Vidéo YouTube principale")
    estimated_minutes = models.PositiveIntegerField(default=20, verbose_name="Durée estimée (min)")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    is_public = models.BooleanField(
        default=False,
        verbose_name="Accessible sans compte",
        help_text="§4 et §10 : le visiteur doit pouvoir consulter les ressources "
                  "educatives « selectionnees ». Par defaut NON, parce qu ouvrir "
                  "toute la pedagogie au public est une decision de "
                  "l'association, pas un effet de bord du statut publie. "
                  "L'enseignant ou l'admin coche la lecon qu il souhaite "
                  "exposer.")
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                null=True, blank=True, related_name='lessons',
                                verbose_name="Auteur")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['chapter', 'order']

    def __str__(self):
        return f'{self.chapter} — {self.order}. {self.title}'


class Resource(models.Model):
    """Ressource libre de droits attachée à une leçon : vidéo, PDF, lien externe."""

    class Kind(models.TextChoices):
        VIDEO = 'video', 'Vidéo'
        PDF = 'pdf', 'PDF'
        LINK = 'link', 'Lien externe'
        EXAM_PAPER = 'exam_paper', "Ancien sujet d'examen"

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='resources')
    order = models.PositiveIntegerField(default=1)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.LINK)
    title = models.CharField(max_length=200)
    title_fr = models.CharField(max_length=200, blank=True)
    url = models.URLField(blank=True, verbose_name="Lien externe")
    file = models.FileField(upload_to='resources/', blank=True, null=True,
                            verbose_name="Fichier hébergé (PDF libre de droits)")
    source_name = models.CharField(max_length=150, blank=True, verbose_name="Source")
    license_note = models.CharField(max_length=200, blank=True,
                                    verbose_name="Licence / attribution")

    class Meta:
        ordering = ['lesson', 'order']

    def __str__(self):
        return f'{self.get_kind_display()} — {self.title}'


class LessonProgress(models.Model):
    """Une leçon marquée comme terminée par un élève."""

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='lesson_progress')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('lesson', 'student')
        ordering = ['-completed_at']

    def __str__(self):
        return f'{self.student} — {self.lesson.title}'


class Quiz(models.Model):
    """Quiz rattaché à une leçon."""

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=200)
    title_fr = models.CharField(max_length=200, blank=True)
    pass_score = models.PositiveIntegerField(default=50, verbose_name="Score de réussite (%)")

    def __str__(self):
        return self.title


class Question(models.Model):
    """Exercice.

    Un exercice appartient soit à un `Quiz` (bilan de fin de module),
    soit directement à une `Step` (vérification immédiate pendant la leçon).
    """

    class Kind(models.TextChoices):
        MCQ = 'mcq', 'Choix multiples'
        NUMERIC = 'numeric', 'Réponse numérique'
        TEXT = 'text', 'Texte court'
        ORDERED = 'ordered', 'Remise en ordre'
        PAIRING = 'pairing', 'Appariement'

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions',
                             null=True, blank=True)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.MCQ)
    text = models.TextField(verbose_name="Question")
    text_fr = models.TextField(blank=True, verbose_name="Question (français)")
    explanation = models.TextField(blank=True,
                                   verbose_name="Explication (affichée après correction)")
    explanation_fr = models.TextField(blank=True, verbose_name="Explication (français)")
    hint_prompt = models.CharField(max_length=200, blank=True,
                                   verbose_name="Question affichée avant les indices")
    hint_prompt_fr = models.CharField(max_length=200, blank=True,
                                      verbose_name="Question avant indices (français)")
    config = models.JSONField(default=dict, blank=True,
                              verbose_name="Règle de correction selon le type",
                              help_text="numeric: {accepted:[..], tolerance:n} | "
                                        "text: {accepted:[..], case_sensitive:false} | "
                                        "ordered: {items:[..]} | pairing: {pairs:[[a,b]]}")
    order = models.PositiveIntegerField(default=1)
    difficulty = models.PositiveSmallIntegerField(default=1, verbose_name="Difficulté (1-3)")

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text[:80]


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=300, verbose_name="Choix")
    text_fr = models.CharField(max_length=300, blank=True, verbose_name="Choix (français)")
    is_correct = models.BooleanField(default=False, verbose_name="Bonne réponse")

    def __str__(self):
        return self.text[:80]


class Hint(models.Model):
    """Piste d'aide. La dernière doit être la réponse (principe Khan/Brilliant).

    Les indices ne sont jamais obligatoires pour réussir : ils aident l'élève
    bloqué, ils ne conditionnent pas la validation.
    """

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='hints')
    order = models.PositiveIntegerField(default=1)
    text = models.TextField()
    text_fr = models.TextField(blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'Indice {self.order}'


class ExerciseAttempt(models.Model):
    """Une réponse d'élève sur un exercice : la matière pour la maîtrise,
    la répétition espacée et le pilotage pédagogique."""

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='exercise_attempts')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='attempts')
    given = models.JSONField(default=dict, blank=True,
                             verbose_name="Réponse donnée")
    is_correct = models.BooleanField(default=False)
    is_first_try = models.BooleanField(default=True,
                                       verbose_name="Bonne du premier coup")
    hints_used = models.PositiveIntegerField(default=0)
    tries = models.PositiveIntegerField(default=1)
    time_spent_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.student} — {self.question} : {self.is_correct}'


class Step(models.Model):
    """Micro-étape d'une leçon : 1 écran, 1 objectif.

    Principe de segmentation (Mayer) : une leçon n'est jamais un mur de texte.
    Chaque étape de cours est suivie de sa vérification.
    """

    class Kind(models.TextChoices):
        CONCEPT = 'concept', "Nouveau concept"
        EXPLAIN = 'explain', "Explication"
        EXAMPLE = 'example', "Exemple résolu"
        PRACTICE = 'practice', "Exercice guidé"
        QUESTION = 'question', "Vérification"
        SUMMARY = 'summary', "Bilan"

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='steps')
    order = models.PositiveIntegerField(default=1)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.CONCEPT)
    title = models.CharField(max_length=200, blank=True)
    title_fr = models.CharField(max_length=200, blank=True)
    content = models.TextField(blank=True, verbose_name="Contenu court (Markdown)")
    content_fr = models.TextField(blank=True, verbose_name="Contenu court (Markdown, français)")
    video_url = models.URLField(blank=True)
    image_url = models.URLField(blank=True)
    question = models.OneToOneField(Question, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='step')
    required = models.BooleanField(default=False,
                                   verbose_name="Doit être réussi pour valider la leçon")
    xp = models.PositiveIntegerField(default=10)

    class Meta:
        ordering = ['lesson', 'order']

    def __str__(self):
        return f'{self.lesson_id}.{self.order} [{self.kind}] {self.title or self.pk}'


class Concept(models.Model):
    """Objectif d'apprentissage d'un chapitre (niveau Bloom révisé).

    Sert de référence pédagogique (congruence objectifs/activités/évaluation)
    et de support à la répétition espacée.
    """

    class Bloom(models.TextChoices):
        REMEMBER = 'remember', "Mémoriser"
        UNDERSTAND = 'understand', "Comprendre"
        APPLY = 'apply', "Appliquer"
        ANALYZE = 'analyze', "Analyser"
        EVALUATE = 'evaluate', "Évaluer"

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='concepts')
    order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200)
    title_fr = models.CharField(max_length=200, blank=True)
    bloom_level = models.CharField(max_length=12, choices=Bloom.choices,
                                   default=Bloom.UNDERSTAND)
    required = models.BooleanField(default=True)

    class Meta:
        ordering = ['chapter', 'order']

    def __str__(self):
        return f'{self.chapter_id}.{self.order} {self.title}'


class ConceptState(models.Model):
    """État de mémorisation d'un concept pour un élève (répétition espacée).

    v1 : boîtes de Leitner (1, 2, 4, 8, 16 jours). `strength` sert de transition
    vers un modèle de demi-vie quand le volume de données le justifie.
    """

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='concept_states')
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name='states')
    box = models.PositiveSmallIntegerField(default=0)
    strength = models.FloatField(default=0.0, verbose_name="Force estimée (0-1)")
    seen_count = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveIntegerField(default=0)
    due_at = models.DateField(default=timezone.localdate)
    last_seen = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'concept')
        ordering = ['due_at']

    def __str__(self):
        return f'{self.student} — {self.concept} (boîte {self.box})'


class LessonMastery(models.Model):
    """Maîtrise d'une leçon : ratio d'étapes-required réussies.

    Remplace la case à cocher, qui pouvait être validée sans lire.
    """

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='lesson_mastery')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='mastery')
    validated = models.PositiveIntegerField(default=0)
    required = models.PositiveIntegerField(default=0)
    mastered_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'lesson')

    @property
    def ratio(self):
        return round(self.validated / self.required * 100) if self.required else 0

    @property
    def is_mastered(self):
        return bool(self.required and self.validated >= self.required)

    def __str__(self):
        return f'{self.student} — {self.lesson} : {self.ratio}%'


class QuizAttempt(models.Model):
    """Résultat d'un élève à un quiz (suivi de progression)."""

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='quiz_attempts')
    score = models.PositiveIntegerField(verbose_name="Bonnes réponses")
    total = models.PositiveIntegerField(verbose_name="Nombre de questions")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    @property
    def percentage(self):
        return round(self.score / self.total * 100) if self.total else 0

    def __str__(self):
        return f'{self.student} — {self.quiz} : {self.percentage}%'


class TutorMessage(models.Model):
    """Échange avec le répétiteur IA local (Ollama) sur une leçon précise."""

    class Role(models.TextChoices):
        STUDENT = 'student', 'Élève'
        TUTOR = 'tutor', 'Tuteur'

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='tutor_messages')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='tutor_messages')
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.student} [{self.role}] {self.content[:60]}'
