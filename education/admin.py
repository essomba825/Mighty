from django.contrib import admin

from .models import (Chapter, Choice, Concept, ConceptState, ExerciseAttempt,
                     Hint, Lesson, LessonMastery, LessonProgress, Question,
                     Quiz, QuizAttempt, Resource, Step, Subject, TutorMessage)



@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'slug', 'icon')
    list_filter = ('level',)
    prepopulated_fields = {'slug': ('name',)}


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    show_change_link = True
    fields = ('order', 'title', 'kind', 'status')


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'order')
    list_filter = ('subject',)
    ordering = ('subject', 'order')
    inlines = [LessonInline]


class ResourceInline(admin.StackedInline):
    model = Resource
    extra = 0
    fields = ('order', 'kind', 'title', 'title_fr', 'url', 'file',
              'source_name', 'license_note')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'chapter', 'order', 'kind', 'status', 'is_public')
    list_filter = ('status', 'kind', 'is_public', 'chapter__subject')
    list_editable = ('is_public',)
    search_fields = ('title', 'content')
    inlines = [ResourceInline]
    actions = ['publish']
    fieldsets = (
        (None, {'fields': ('chapter', 'order', 'kind', 'status', 'teacher',
                           'estimated_minutes')}),
        # La case est isolee : c'est une decision commerciale (ouvrir la
        # pedagogie au public), pas un detail de saisie, et la HelpText du
        # modele explique pourquoi elle est decochee par defaut.
        ('Visibilité publique', {
            'fields': ('is_public',),
            'description': '§4 et §10 : un visiteur doit pouvoir consulter les '
                           'ressources éducatives « sélectionnées ». Cochez la '
                           'leçon pour qu\'elle s\'ouvre sans compte.'}),
        ('Titres', {'fields': ('title', 'title_fr', 'summary', 'summary_fr')}),
        ('Objectifs', {'fields': ('objectives',)}),
        ('Contenu (Markdown)', {'fields': ('content', 'content_fr'),
                                'classes': ('collapse',)}),
        ('Média', {'fields': ('video_url',)}),
    )

    @admin.action(description='Publier les leçons sélectionnées')
    def publish(self, request, queryset):
        queryset.update(status='published')


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 3


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1
    show_change_link = True


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ('text', 'quiz', 'order')


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    inlines = [QuestionInline]
    list_display = ('title', 'lesson', 'pass_score')


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'quiz', 'score', 'total', 'percentage', 'submitted_at')
    list_filter = ('quiz',)


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'student', 'completed_at')
    list_filter = ('lesson__chapter__subject',)


@admin.register(TutorMessage)
class TutorMessageAdmin(admin.ModelAdmin):
    list_display = ('student', 'lesson', 'role', 'created_at')
    list_filter = ('role', 'lesson__chapter__subject')
    search_fields = ('content', 'student__username')


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'order', 'kind', 'title')
    list_filter = ('kind', 'lesson__chapter__subject')


@admin.register(Concept)
class ConceptAdmin(admin.ModelAdmin):
    list_display = ('chapter', 'order', 'title', 'bloom_level')
    list_filter = ('bloom_level', 'chapter__subject')


@admin.register(Hint)
class HintAdmin(admin.ModelAdmin):
    list_display = ('question', 'order', 'text')


@admin.register(ExerciseAttempt)
class ExerciseAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'question', 'is_correct', 'tries', 'created_at')
    list_filter = ('is_correct', 'created_at')


@admin.register(ConceptState)
class ConceptStateAdmin(admin.ModelAdmin):
    list_display = ('student', 'concept', 'box', 'due_at')
    list_filter = ('box', 'due_at')


@admin.register(LessonMastery)
class LessonMasteryAdmin(admin.ModelAdmin):
    list_display = ('student', 'lesson', 'validated', 'required')

