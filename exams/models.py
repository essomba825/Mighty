import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from education.models import Subject


class ExamPaper(models.Model):
    """An exam PDF and its canonical GCE identity."""

    class Session(models.TextChoices):
        JUNE = 'june', 'June'
        MOCK = 'mock', 'Mock / regional'
        OTHER = 'other', 'Other / unknown'

    class PaperType(models.TextChoices):
        OFFICIAL = 'official', 'Official GCE'
        MOCK = 'mock', 'Mock / regional'

    subject = models.ForeignKey(Subject, on_delete=models.PROTECT,
                                related_name='exam_papers')
    subject_code = models.CharField(max_length=12, blank=True)
    route = models.CharField(max_length=40, blank=True,
                             help_text='Ex. mechanics ou statistics pour A/L Mathematics.')
    year = models.PositiveSmallIntegerField(validators=[MinValueValidator(1900),
                                                        MaxValueValidator(2200)])
    session = models.CharField(max_length=12, choices=Session.choices,
                               default=Session.OTHER)
    paper_number = models.PositiveSmallIntegerField(default=1)
    paper_type = models.CharField(max_length=12, choices=PaperType.choices,
                                  default=PaperType.OFFICIAL)
    title = models.CharField(max_length=240)
    source_name = models.CharField(max_length=260)
    source_pdf = models.FileField(upload_to='exams/papers/', blank=True)
    source_url = models.URLField(blank=True)
    source_sha256 = models.CharField(max_length=64, unique=True, db_index=True)
    duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    total_marks = models.DecimalField(max_digits=7, decimal_places=2,
                                      null=True, blank=True)
    imported_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['subject__level', 'subject__name', '-year', 'session',
                    'route', 'paper_number']
        indexes = [
            models.Index(fields=['year', 'paper_number']),
            models.Index(fields=['subject', 'year']),
        ]

    def __str__(self):
        route = f' ({self.route})' if self.route else ''
        return f'{self.subject} — {self.year} {self.session} P{self.paper_number}{route}'


class ExamQuestion(models.Model):
    """A question/sub-question as it appears in a particular paper."""

    class Kind(models.TextChoices):
        MCQ = 'mcq', 'Multiple choice'
        NUMERIC = 'numeric', 'Numeric'
        SHORT = 'short', 'Short response'
        STRUCTURED = 'structured', 'Structured response'
        ESSAY = 'essay', 'Extended response'
        DIAGRAM = 'diagram', 'Diagram / drawing'
        DATA = 'data', 'Data / graph interpretation'
        UNKNOWN = 'unknown', 'To classify'

    paper = models.ForeignKey(ExamPaper, on_delete=models.CASCADE,
                              related_name='questions')
    parent = models.ForeignKey('self', null=True, blank=True,
                               on_delete=models.CASCADE, related_name='parts')
    number = models.CharField(max_length=24)
    order = models.PositiveSmallIntegerField(default=1)
    kind = models.CharField(max_length=16, choices=Kind.choices,
                            default=Kind.UNKNOWN)
    statement = models.TextField()
    statement_fr = models.TextField(blank=True)
    raw_ocr = models.TextField(blank=True)
    choices = models.JSONField(default=list, blank=True)
    source_pages = models.JSONField(default=list, blank=True)
    source_region = models.JSONField(default=dict, blank=True,
                                     help_text='Coordonnées normalisées si disponibles.')
    marks = models.DecimalField(max_digits=6, decimal_places=2,
                                 null=True, blank=True)
    extraction_confidence = models.DecimalField(max_digits=4, decimal_places=3,
                                                null=True, blank=True,
                                                validators=[MinValueValidator(0),
                                                            MaxValueValidator(1)])
    needs_human_review = models.BooleanField(default=True)
    review_flags = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['paper', 'order']
        constraints = [models.UniqueConstraint(fields=['paper', 'number'],
                                                name='exam_question_number_per_paper')]

    def __str__(self):
        return f'{self.paper} — {self.number}'


class PaperCorrection(models.Model):
    """Versioned marking scheme; generated versions may be published for pilot use."""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published for pilot'
        ARCHIVED = 'archived', 'Archived'

    paper = models.ForeignKey(ExamPaper, on_delete=models.CASCADE,
                              related_name='correction_versions')
    correction_pdf = models.FileField(upload_to='exams/corrections/', blank=True)
    version = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=12, choices=Status.choices,
                              default=Status.DRAFT)
    generated_by = models.CharField(max_length=100, blank=True)
    generation_model = models.CharField(max_length=100, blank=True)
    is_machine_generated = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name='exam_corrections_created')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL,
                                    related_name='exam_corrections_reviewed')
    reviewer_notes = models.TextField(blank=True)
    generation_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['paper', '-version']
        constraints = [models.UniqueConstraint(fields=['paper', 'version'],
                                                name='exam_correction_version_per_paper')]

    def save(self, *args, **kwargs):
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.paper} — correction v{self.version} ({self.status})'


class QuestionCorrection(models.Model):
    """Expected answer and bilingual explanation for one question in one version."""

    version = models.ForeignKey(PaperCorrection, on_delete=models.CASCADE,
                                related_name='question_corrections')
    question = models.ForeignKey(ExamQuestion, on_delete=models.CASCADE,
                                 related_name='corrections')
    answer = models.JSONField(default=dict, blank=True)
    explanation_en = models.TextField(blank=True)
    explanation_fr = models.TextField(blank=True)
    solution_steps = models.JSONField(default=list, blank=True)
    confidence = models.DecimalField(max_digits=4, decimal_places=3,
                                     null=True, blank=True,
                                     validators=[MinValueValidator(0),
                                                 MaxValueValidator(1)])
    needs_human_review = models.BooleanField(default=True)
    review_flags = models.JSONField(default=list, blank=True)
    source_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['question__order']
        constraints = [models.UniqueConstraint(fields=['version', 'question'],
                                                name='exam_question_correction_per_version')]

    def __str__(self):
        return f'{self.question} — {self.version}'


class MarkCriterion(models.Model):
    """One independently inspectable mark or partial-credit rule."""

    class CriterionType(models.TextChoices):
        METHOD = 'method', 'Method'
        WORKING = 'working', 'Working / substitution'
        ACCURACY = 'accuracy', 'Accuracy'
        ANSWER = 'answer', 'Final answer'
        UNIT = 'unit', 'Unit / notation'
        COMMUNICATION = 'communication', 'Scientific communication'
        OTHER = 'other', 'Other'

    correction = models.ForeignKey(QuestionCorrection, on_delete=models.CASCADE,
                                   related_name='criteria')
    order = models.PositiveSmallIntegerField(default=1)
    key = models.CharField(max_length=60, blank=True)
    criterion_type = models.CharField(max_length=16, choices=CriterionType.choices,
                                      default=CriterionType.OTHER)
    description_en = models.TextField()
    description_fr = models.TextField(blank=True)
    marks = models.DecimalField(max_digits=5, decimal_places=2,
                                validators=[MinValueValidator(0)])
    accepted_answers = models.JSONField(default=list, blank=True)
    follow_through = models.BooleanField(default=False)
    depends_on = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ['correction', 'order']

    def __str__(self):
        return f'{self.correction.question.number} — {self.marks} marks: {self.key}'
