import hashlib
import json
from pathlib import PurePath

from django.db import transaction
from django.db.models import Max
from django.db.models import Q
from rest_framework import serializers

from education.models import Subject
from .models import (ExamPaper, ExamQuestion, ExamSubmission, MarkCriterion,
                     PaperCorrection, QuestionCorrection)


class ExamPaperListSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_slug = serializers.CharField(source='subject.slug', read_only=True)
    level = serializers.CharField(source='subject.level', read_only=True)
    question_count = serializers.IntegerField(source='questions.count', read_only=True)
    correction_available = serializers.SerializerMethodField()
    correction_complete = serializers.SerializerMethodField()

    class Meta:
        model = ExamPaper
        fields = ['id', 'subject', 'subject_name', 'subject_slug', 'level',
                  'subject_code', 'route', 'year', 'session', 'paper_number',
                  'paper_type', 'title', 'source_name', 'source_pdf', 'source_url',
                  'duration_minutes', 'total_marks', 'question_count',
                  'correction_available', 'correction_complete']

    def get_correction_available(self, obj):
        return obj.correction_versions.filter(
            status=PaperCorrection.Status.PUBLISHED,
        ).filter(
            Q(question_corrections__isnull=False) | ~Q(correction_pdf=''),
        ).exists()

    def get_correction_complete(self, obj):
        correction = obj.correction_versions.filter(
            status=PaperCorrection.Status.PUBLISHED,
        ).filter(
            Q(question_corrections__isnull=False) | ~Q(correction_pdf=''),
        ).order_by('-version').first()
        if not correction:
            return False
        if correction.correction_pdf and not correction.question_corrections.exists():
            return True
        return correction.generation_metadata.get('coverage_complete', True)


class ExamQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamQuestion
        fields = ['id', 'parent', 'number', 'order', 'kind', 'statement',
                  'statement_fr', 'choices', 'source_pages', 'source_region',
                  'marks', 'extraction_confidence', 'needs_human_review',
                  'review_flags']


class MarkCriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarkCriterion
        fields = ['order', 'key', 'criterion_type', 'description_en',
                  'description_fr', 'marks', 'accepted_answers',
                  'follow_through', 'depends_on']


class QuestionCorrectionSerializer(serializers.ModelSerializer):
    question = ExamQuestionSerializer(read_only=True)
    criteria = MarkCriterionSerializer(many=True, read_only=True)

    class Meta:
        model = QuestionCorrection
        fields = ['question', 'answer', 'explanation_en', 'explanation_fr',
                  'solution_steps', 'confidence', 'needs_human_review',
                  'review_flags', 'criteria']


class PaperCorrectionSerializer(serializers.ModelSerializer):
    paper = ExamPaperListSerializer(read_only=True)
    questions = serializers.SerializerMethodField()
    correction_pdf = serializers.FileField(read_only=True)

    class Meta:
        model = PaperCorrection
        fields = ['id', 'version', 'status', 'is_machine_generated',
                  'generation_model', 'published_at', 'generation_metadata',
                  'correction_pdf', 'paper', 'questions']

    def get_questions(self, obj):
        qs = obj.question_corrections.select_related('question').prefetch_related('criteria')
        return QuestionCorrectionSerializer(qs, many=True, context=self.context).data


class ExamPaperCreateSerializer(serializers.ModelSerializer):
    source_pdf = serializers.FileField(write_only=True)

    class Meta:
        model = ExamPaper
        fields = ['subject', 'subject_code', 'route', 'year', 'session',
                  'paper_number', 'paper_type', 'title', 'source_pdf',
                  'duration_minutes', 'total_marks']

    def validate_source_pdf(self, value):
        position = value.tell()
        if value.read(5) != b'%PDF-':
            raise serializers.ValidationError('Le fichier doit Ãªtre un PDF valide.')
        value.seek(position)
        return value

    def create(self, validated_data):
        pdf = validated_data['source_pdf']
        digest = hashlib.sha256()
        for chunk in pdf.chunks():
            digest.update(chunk)
        pdf.seek(0)
        sha256 = digest.hexdigest()
        if ExamPaper.objects.filter(source_sha256=sha256).exists():
            raise serializers.ValidationError({
                'source_pdf': 'Cette Ã©preuve PDF est dÃ©jÃ  enregistrÃ©e.'
            })

        validated_data['source_name'] = PurePath(pdf.name).name
        validated_data['source_sha256'] = sha256
        return ExamPaper.objects.create(**validated_data)


class PaperCorrectionCreateSerializer(serializers.Serializer):
    correction_pdf = serializers.FileField(required=False)
    questions = serializers.JSONField(required=False, default=list)
    publish = serializers.BooleanField(required=False, default=False)
    coverage_complete = serializers.BooleanField(required=False, default=False)

    def validate_correction_pdf(self, value):
        position = value.tell()
        if value.read(5) != b'%PDF-':
            raise serializers.ValidationError('Le fichier doit Ãªtre un PDF valide.')
        value.seek(position)
        return value

    def validate(self, attrs):
        pdf = attrs.get('correction_pdf')
        questions = attrs.get('questions') or []
        if not pdf and not questions:
            raise serializers.ValidationError(
                'Ajoutez un PDF de corrigÃ© ou au moins une correction de question.'
            )
        if not isinstance(questions, list):
            raise serializers.ValidationError({'questions': 'Une liste de questions est attendue.'})

        seen_numbers = set()
        for index, question in enumerate(questions, start=1):
            if not isinstance(question, dict):
                raise serializers.ValidationError({
                    'questions': f"La correction {index} doit Ãªtre un objet."
                })
            if not str(question.get('number', '')).strip():
                raise serializers.ValidationError({
                    'questions': f"Le numÃ©ro de la question {index} est obligatoire."
                })
            number = str(question['number']).strip()
            if number in seen_numbers:
                raise serializers.ValidationError({
                    'questions': f"La question {number} apparaÃ®t plusieurs fois."
                })
            seen_numbers.add(number)
            if not str(question.get('statement', '')).strip():
                raise serializers.ValidationError({
                    'questions': f"L'Ã©noncÃ© de la question {index} est obligatoire."
                })
            if not str(question.get('answer', '')).strip() and not str(
                question.get('explanation_fr', '') or question.get('explanation_en', '')
            ).strip():
                raise serializers.ValidationError({
                    'questions': f"Ajoutez une rÃ©ponse ou une explication Ã  la question {index}."
                })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        paper = self.context['paper']
        request = self.context['request']
        publish = validated_data.get('publish', False)
        status_value = (
            PaperCorrection.Status.PUBLISHED if publish
            else PaperCorrection.Status.DRAFT
        )
        latest_version = paper.correction_versions.aggregate(
            latest=Max('version')
        )['latest'] or 0

        if publish:
            paper.correction_versions.filter(
                status=PaperCorrection.Status.PUBLISHED
            ).update(status=PaperCorrection.Status.ARCHIVED)

        correction = PaperCorrection.objects.create(
            paper=paper,
            version=latest_version + 1,
            status=status_value,
            correction_pdf=validated_data.get('correction_pdf'),
            created_by=request.user,
            reviewed_by=request.user if publish else None,
            generation_metadata={
                'coverage_complete': validated_data.get('coverage_complete', False),
            },
        )

        for index, item in enumerate(validated_data.get('questions', []), start=1):
            number = str(item['number']).strip()
            question, _ = ExamQuestion.objects.get_or_create(
                paper=paper,
                number=number,
                defaults={
                    'order': index,
                    'statement': item['statement'].strip(),
                    'statement_fr': item.get('statement_fr', '').strip(),
                    'marks': item.get('marks') or None,
                    'kind': item.get('kind') or ExamQuestion.Kind.UNKNOWN,
                    'needs_human_review': not publish,
                },
            )
            question_correction = QuestionCorrection.objects.create(
                version=correction,
                question=question,
                answer={'final': item.get('answer', '').strip()} if item.get('answer', '').strip() else {},
                explanation_en=item.get('explanation_en', '').strip(),
                explanation_fr=item.get('explanation_fr', '').strip(),
                needs_human_review=not publish,
            )
            if item.get('solution_steps'):
                question_correction.solution_steps = [
                    step.strip() for step in item['solution_steps'].splitlines()
                    if step.strip()
                ]
                question_correction.save(update_fields=['solution_steps'])

        return correction


def parse_questions_payload(data):
    """Decode the JSON question list sent alongside multipart PDF uploads."""
    questions = data.get('questions', [])
    if isinstance(questions, str):
        try:
            return json.loads(questions)
        except json.JSONDecodeError as error:
            raise serializers.ValidationError({
                'questions': 'Le contenu des questions doit Ãªtre un JSON valide.'
            }) from error
    return questions


class ExamSubmissionSerializer(serializers.ModelSerializer):
    submitted_by_name = serializers.SerializerMethodField()
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_id = serializers.PrimaryKeyRelatedField(
        source='subject', queryset=Subject.objects.all(),
        required=False, allow_null=True, write_only=True,
    )

    class Meta:
        model = ExamSubmission
        fields = [
            'id', 'resource_type', 'level', 'year', 'title', 'description',
            'pdf_file', 'status', 'reviewer_note',
            'submitted_at', 'reviewed_at',
            'submitted_by_name', 'subject_name', 'subject_id',
        ]
        read_only_fields = ['id', 'status', 'reviewer_note', 'submitted_at', 'reviewed_at',
                            'submitted_by_name', 'subject_name']

    def get_submitted_by_name(self, obj):
        if obj.submitted_by:
            return f'{obj.submitted_by.first_name} {obj.submitted_by.last_name}'.strip() or obj.submitted_by.username
        return None

    def validate_pdf_file(self, value):
        pos = value.tell()
        if value.read(5) != b'%PDF-':
            raise serializers.ValidationError('The file must be a valid PDF.')
        value.seek(pos)
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError('PDF file size must not exceed 50 MB.')
        return value

    def create(self, validated_data):
        request = self.context['request']
        validated_data['submitted_by'] = request.user
        return super().create(validated_data)
