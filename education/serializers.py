from rest_framework import serializers

from .models import (Chapter, Choice, Concept, ConceptState, ExerciseAttempt, Hint,
                     Lesson, LessonMastery, LessonProgress, Question, Quiz,
                     QuizAttempt, Resource, Step, Subject)


class SubjectSerializer(serializers.ModelSerializer):
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    lessons_count = serializers.SerializerMethodField()
    lessons_completed = serializers.SerializerMethodField()
    weak_lessons_count = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['id', 'name', 'slug', 'level', 'level_display', 'description',
                  'icon', 'color', 'image_url', 'lessons_count', 'lessons_completed',
                  'weak_lessons_count']

    def get_lessons_count(self, obj):
        return Lesson.objects.filter(chapter__subject=obj, status='published').count()

    def get_lessons_completed(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return 0
        return LessonProgress.objects.filter(
            student=user, lesson__chapter__subject=obj,
            lesson__status='published').count()

    def get_weak_lessons_count(self, obj):
        """Nb de leçons où l'élève a obtenu moins de 70 % à un quiz (à retravailler)."""
        user = self.context['request'].user
        if not user.is_authenticated:
            return 0
        from .models import QuizAttempt
        attempts = (QuizAttempt.objects
                    .filter(student=user, quiz__lesson__chapter__subject=obj)
                    .order_by('quiz__lesson_id')
                    .values_list('quiz__lesson_id', 'score', 'total'))
        best = {}
        for lesson_id, score, total in attempts:
            pct = round(score / total * 100) if total else 0
            best[lesson_id] = max(best.get(lesson_id, 0), pct)
        return sum(1 for pct in best.values() if pct < 70)


class ResourceSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source='get_kind_display', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Resource
        fields = ['id', 'kind', 'kind_display', 'title', 'title_fr', 'url', 'file_url',
                  'source_name', 'license_note', 'order']

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get('request')
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url


class LessonListSerializer(serializers.ModelSerializer):
    """Leçon dans le catalogue : pas de contenu, juste la fiche."""
    kind_display = serializers.CharField(source='get_kind_display', read_only=True)
    quizzes_count = serializers.IntegerField(source='quizzes.count', read_only=True)
    completed = serializers.SerializerMethodField()
    best_score = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ['id', 'order', 'kind', 'kind_display', 'title', 'title_fr',
                  'summary', 'summary_fr', 'objectives', 'objectives_fr',
'video_url', 'estimated_minutes', 'quizzes_count',
'completed', 'best_score', 'is_public']

    def get_completed(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and obj.progress.filter(student=user).exists()

    def get_best_score(self, obj):
        """Meilleur % de l'élève sur les quiz de cette leçon (utile pour les lacunes)."""
        user = self.context['request'].user
        if not user.is_authenticated:
            return None
        from .models import QuizAttempt
        best = (QuizAttempt.objects
                .filter(student=user, quiz__lesson=obj)
                .order_by('-score', 'total').first())
        return best.percentage if best else None


class ChapterSerializer(serializers.ModelSerializer):
    lessons = LessonListSerializer(many=True, read_only=True)

    class Meta:
        model = Chapter
        fields = ['id', 'order', 'title', 'title_fr', 'description', 'lessons']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        qs = instance.lessons.filter(status='published')
        user = self.context['request'].user
        if user.is_authenticated and (user.is_staff or user.role == 'teacher'):
            qs = instance.lessons.exclude(status='draft')
        data['lessons'] = LessonListSerializer(
            qs, many=True, context=self.context).data
        return data


class ChoicePublicSerializer(serializers.ModelSerializer):
    """Choix sans révéler la bonne réponse."""
    class Meta:
        model = Choice
        fields = ['id', 'text', 'text_fr']


class QuestionPublicSerializer(serializers.ModelSerializer):
    """Exercice vu par l'eleve AVANT de repondre.

    `explanation` est volontairement absent : elle n'est renvoyee qu'apres
    correction (endpoint `attempt`) pour ne pas donner la reponse avant que
    l'eleve ait tente. `hints_count` indique combien d'indices existent sans
    les reveler.

    Chaque champ texte est double (`text` / `text_fr`) : le cote client choisit
    selon la langue active et retombe sur l'anglais si le francais manque.
    """
    choices = ChoicePublicSerializer(many=True, read_only=True)
    hints_count = serializers.SerializerMethodField()
    ordered_items = serializers.SerializerMethodField()
    ordered_items_fr = serializers.SerializerMethodField()
    pair_items = serializers.SerializerMethodField()
    pair_items_fr = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ['id', 'kind', 'text', 'text_fr', 'order', 'difficulty',
                  'hint_prompt', 'hint_prompt_fr', 'choices', 'hints_count',
                  'ordered_items', 'ordered_items_fr', 'pair_items', 'pair_items_fr']
        read_only_fields = fields

    def get_hints_count(self, obj):
        return obj.hints.count()

    def get_ordered_items(self, obj):
        if obj.kind != Question.Kind.ORDERED:
            return None
        return list((obj.config or {}).get('items') or [])

    def get_ordered_items_fr(self, obj):
        if obj.kind != Question.Kind.ORDERED:
            return None
        return list((obj.config or {}).get('items_fr') or []) or None

    def get_pair_items(self, obj):
        if obj.kind != Question.Kind.PAIRING:
            return None
        return _pairs_from_config(obj.config, 'pairs')

    def get_pair_items_fr(self, obj):
        if obj.kind != Question.Kind.PAIRING:
            return None
        return _pairs_from_config(obj.config, 'pairs_fr')


def _pairs_from_config(config, key):
    """Transforme {key: [[a, b], ...]} en {left: [...], right: [...]}."""
    left, right = [], []
    for a, b in (config or {}).get(key) or []:
        left.append(a)
        right.append(b)
    return {'left': left, 'right': right} if left else None


class HintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hint
        fields = ['order', 'text', 'text_fr']


class StepSerializer(serializers.ModelSerializer):
    """Une micro-etape. Les indices ne sont PAS envoyes ici : ils se revelent
    a la demande pour que l'eleve essaie seul d'abord."""
    question = serializers.SerializerMethodField()
    xp = serializers.IntegerField(read_only=True)

    class Meta:
        model = Step
        fields = ['id', 'order', 'kind', 'title', 'title_fr', 'content',
                  'content_fr', 'video_url', 'image_url', 'required', 'xp', 'question']

    def get_question(self, obj):
        if not obj.question:
            return None
        return QuestionPublicSerializer(obj.question, context=self.context).data


class LessonMasterySerializer(serializers.ModelSerializer):
    ratio = serializers.IntegerField(read_only=True)
    is_mastered = serializers.BooleanField(read_only=True)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)

    class Meta:
        model = LessonMastery
        fields = ['lesson', 'lesson_title', 'ratio', 'required', 'validated',
                  'is_mastered']


class QuizListSerializer(serializers.ModelSerializer):
    """Quiz dans une fiche leçon : pas les questions."""
    questions_count = serializers.IntegerField(source='questions.count', read_only=True)

    class Meta:
        model = Quiz
        fields = ['id', 'title', 'title_fr', 'pass_score', 'questions_count']


class QuizSerializer(QuizListSerializer):
    """Quiz complet pour la page d'exercice."""
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    questions = QuestionPublicSerializer(many=True, read_only=True)

    class Meta(QuizListSerializer.Meta):
        fields = QuizListSerializer.Meta.fields + ['lesson', 'lesson_title', 'questions']


class LessonSerializer(LessonListSerializer):
    """Détail complet d'une leçon (contenu + ressources + quiz) — login requis."""
    subject_id = serializers.IntegerField(source='chapter.subject_id', read_only=True)
    subject = serializers.CharField(source='chapter.subject.name', read_only=True)
    subject_slug = serializers.CharField(source='chapter.subject.slug', read_only=True)
    subject_color = serializers.CharField(source='chapter.subject.color', read_only=True)
    subject_icon = serializers.CharField(source='chapter.subject.icon', read_only=True)
    subject_image = serializers.CharField(source='chapter.subject.image_url',
                                          read_only=True)
    chapter_title = serializers.CharField(source='chapter.title', read_only=True)
    chapter_title_fr = serializers.CharField(source='chapter.title_fr', read_only=True)
    resources = ResourceSerializer(many=True, read_only=True)
    quizzes = QuizListSerializer(many=True, read_only=True)
    author_name = serializers.CharField(source='teacher.get_full_name',
                                        read_only=True, allow_null=True)
    prev_lesson_id = serializers.SerializerMethodField()
    next_lesson_id = serializers.SerializerMethodField()

    # Champ d'ecriture : le formateur choisit un chapitre (la vue le resout).
    chapter = serializers.PrimaryKeyRelatedField(
        queryset=Chapter.objects.all(), required=False, allow_null=True,
        write_only=True)

    class Meta(LessonListSerializer.Meta):
        fields = LessonListSerializer.Meta.fields + [
            'subject_id', 'subject', 'subject_slug', 'subject_color', 'subject_icon',
            'subject_image', 'chapter', 'chapter_title', 'chapter_title_fr',
            'content', 'content_fr',
            'resources', 'quizzes', 'author_name', 'created_at', 'status',
            'prev_lesson_id', 'next_lesson_id',
        ]
        read_only_fields = ['status']

    def _sibling(self, obj, direction):
        qs = Lesson.objects.filter(chapter=obj.chapter, status='published')
        if direction > 0:
            qs = qs.filter(order__gt=obj.order).order_by('order')
        else:
            qs = qs.filter(order__lt=obj.order).order_by('-order')
        sib = qs.first()
        # Si extrémité du chapitre, on saute au chapitre voisin
        if not sib:
            siblings_chap = obj.chapter.subject.chapters
            neigh = (siblings_chap.filter(order__gt=obj.chapter.order).order_by('order').first()
                     if direction > 0 else
                     siblings_chap.filter(order__lt=obj.chapter.order).order_by('-order').first())
            if neigh:
                sib = (neigh.lessons.filter(status='published').order_by('order').first()
                       if direction > 0 else
                       neigh.lessons.filter(status='published').order_by('-order').first())
        return sib.id if sib else None

    def get_next_lesson_id(self, obj):
        return self._sibling(obj, 1)

    def get_prev_lesson_id(self, obj):
        return self._sibling(obj, -1)


class QuizSubmissionSerializer(serializers.Serializer):
    """Réponses envoyées : {question_id: choice_id}."""
    answers = serializers.DictField(child=serializers.IntegerField())


class QuizAttemptSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    lesson_title = serializers.CharField(source='quiz.lesson.title', read_only=True)
    subject_name = serializers.CharField(source='quiz.lesson.chapter.subject.name',
                                         read_only=True)
    lesson_id = serializers.IntegerField(source='quiz.lesson_id', read_only=True)
    percentage = serializers.ReadOnlyField()
    passed = serializers.SerializerMethodField()

    class Meta:
        model = QuizAttempt
        fields = ['id', 'quiz', 'quiz_title', 'lesson_id', 'lesson_title',
                  'subject_name', 'score', 'total', 'percentage', 'passed',
                  'submitted_at']

    def get_passed(self, obj):
        return obj.percentage >= obj.quiz.pass_score
