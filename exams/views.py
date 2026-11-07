from django.http import FileResponse
from django.db.models import Q
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework import status

from .models import ExamPaper, PaperCorrection
from .serializers import (ExamPaperCreateSerializer, ExamPaperListSerializer,
                          PaperCorrectionCreateSerializer, PaperCorrectionSerializer,
                          parse_questions_payload)


class CanManageExamPaper(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS or (
            request.user.is_authenticated and (
                request.user.is_staff or request.user.role == 'admin'
            )
        )


class ExamPaperViewSet(viewsets.ReadOnlyModelViewSet):
    """Public annals catalogue and published correction retrieval."""
    permission_classes = [permissions.AllowAny]
    serializer_class = ExamPaperListSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'subject__name', 'route', 'year']
    ordering_fields = ['year', 'paper_number', 'subject__name']
    ordering = ['subject__level', 'subject__name', '-year', 'paper_number']

    def get_queryset(self):
        qs = ExamPaper.objects.select_related('subject').prefetch_related(
            'questions', 'correction_versions')
        level = self.request.query_params.get('level')
        subject = self.request.query_params.get('subject')
        year = self.request.query_params.get('year')

        if level:
            lvl = level.lower().replace('/', '')
            if lvl in ('ol', 'al'):
                qs = qs.filter(subject__level=lvl)

        if subject:
            sub = subject.lower().strip()
            if sub.endswith('-ol'):
                sub = sub[:-3]
            elif sub.endswith('-al'):
                sub = sub[:-3]
            if sub.startswith('math'):
                prefixes = ['math', 'mathematique', 'mathematiques']
            elif sub.startswith('phys'):
                prefixes = ['phys', 'physics', 'physique']
            elif sub.startswith('chem') or sub.startswith('chim'):
                prefixes = ['chem', 'chemistry', 'chim', 'chimie']
            elif sub.startswith('bio'):
                prefixes = ['bio', 'biology', 'biologie']
            else:
                prefixes = [sub]

            sub_filter = Q()
            for pfx in prefixes:
                sub_filter |= Q(subject__slug__istartswith=pfx)
                sub_filter |= Q(subject__name__icontains=pfx)
            qs = qs.filter(sub_filter)

        if year and year.isdigit():
            qs = qs.filter(year=int(year))
        return qs

    @action(detail=False, methods=['post'], url_path='create',
            permission_classes=[CanManageExamPaper])
    def create_paper(self, request):
        serializer = ExamPaperCreateSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        paper = serializer.save()
        return Response(
            ExamPaperListSerializer(paper, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'], url_path='pdf')
    def pdf(self, request, pk=None):
        paper = self.get_object()
        if not paper.source_pdf:
            raise NotFound('PDF file not found.')

        try:
            pdf_file = paper.source_pdf.open('rb')
        except FileNotFoundError as error:
            raise NotFound('PDF file not found.') from error

        return FileResponse(
            pdf_file,
            content_type='application/pdf',
            as_attachment=False,
            filename=paper.source_name or paper.source_pdf.name.rsplit('/', 1)[-1],
        )

    @action(detail=True, methods=['get', 'post'], url_path='correction',
            permission_classes=[CanManageExamPaper])
    def correction(self, request, pk=None):
        paper = self.get_object()
        if request.method == 'POST':
            payload = {key: value for key, value in request.data.items()}
            payload['questions'] = parse_questions_payload(request.data)
            serializer = PaperCorrectionCreateSerializer(
                data=payload,
                context={'request': request, 'paper': paper},
            )
            serializer.is_valid(raise_exception=True)
            correction = serializer.save()
            return Response(
                PaperCorrectionSerializer(
                    correction, context={'request': request}
                ).data,
                status=status.HTTP_201_CREATED,
            )

        correction = paper.correction_versions.filter(
            status=PaperCorrection.Status.PUBLISHED,
        ).filter(
            Q(question_corrections__isnull=False) | ~Q(correction_pdf=''),
        ).distinct().order_by('-version').first()
        if not correction:
            return Response({'detail': 'Correction not published.'}, status=404)
        return Response(PaperCorrectionSerializer(
            correction, context={'request': request}).data)

    @action(detail=True, methods=['get'], url_path='correction-pdf',
            permission_classes=[permissions.AllowAny])
    def correction_pdf(self, request, pk=None):
        paper = self.get_object()
        correction = paper.correction_versions.filter(
            status=PaperCorrection.Status.PUBLISHED,
        ).exclude(correction_pdf='').order_by('-version').first()
        if not correction or not correction.correction_pdf:
            raise NotFound('Published correction PDF not found.')

        try:
            pdf_file = correction.correction_pdf.open('rb')
        except FileNotFoundError as error:
            raise NotFound('Published correction PDF not found.') from error

        return FileResponse(
            pdf_file,
            content_type='application/pdf',
            as_attachment=False,
            filename=correction.correction_pdf.name.rsplit('/', 1)[-1],
        )
