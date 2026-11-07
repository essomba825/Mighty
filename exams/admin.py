from django.contrib import admin

from .models import (ExamPaper, ExamQuestion, MarkCriterion, PaperCorrection,
                     QuestionCorrection)


class ExamQuestionInline(admin.TabularInline):
    model = ExamQuestion
    extra = 0
    fields = ('order', 'number', 'kind', 'marks', 'extraction_confidence',
              'needs_human_review')
    show_change_link = True


class CorrectionInline(admin.TabularInline):
    model = PaperCorrection
    extra = 0
    fields = ('version', 'status', 'is_machine_generated', 'generation_model',
              'created_at', 'reviewed_by')
    readonly_fields = ('created_at',)
    show_change_link = True


@admin.register(ExamPaper)
class ExamPaperAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'year', 'session', 'paper_number',
                    'route', 'paper_type', 'source_sha256')
    list_filter = ('subject__level', 'subject', 'year', 'paper_type', 'session')
    search_fields = ('title', 'source_name', 'source_sha256')
    readonly_fields = ('source_sha256', 'imported_at')
    inlines = [ExamQuestionInline, CorrectionInline]


class MarkCriterionInline(admin.TabularInline):
    model = MarkCriterion
    extra = 0
    fields = ('order', 'key', 'criterion_type', 'marks', 'description_en',
              'description_fr', 'follow_through', 'depends_on')


class QuestionCorrectionInline(admin.StackedInline):
    model = QuestionCorrection
    extra = 0
    show_change_link = True


@admin.register(ExamQuestion)
class ExamQuestionAdmin(admin.ModelAdmin):
    list_display = ('paper', 'number', 'kind', 'marks', 'extraction_confidence',
                    'needs_human_review')
    list_filter = ('paper__subject', 'paper__year', 'kind', 'needs_human_review')
    search_fields = ('statement', 'raw_ocr', 'number')
    inlines = [QuestionCorrectionInline]


@admin.register(PaperCorrection)
class PaperCorrectionAdmin(admin.ModelAdmin):
    list_display = ('paper', 'version', 'status', 'correction_pdf', 'is_machine_generated',
                    'generation_model', 'reviewed_by', 'published_at')
    list_filter = ('status', 'is_machine_generated', 'paper__subject', 'paper__year')
    search_fields = ('paper__title', 'reviewer_notes')
    inlines = []


@admin.register(QuestionCorrection)
class QuestionCorrectionAdmin(admin.ModelAdmin):
    list_display = ('question', 'version', 'confidence', 'needs_human_review')
    list_filter = ('needs_human_review', 'version__paper__subject')
    search_fields = ('question__statement', 'explanation_en', 'explanation_fr')
    inlines = [MarkCriterionInline]
