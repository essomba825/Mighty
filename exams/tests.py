import json
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from education.models import Subject
from .models import ExamPaper, PaperCorrection, QuestionCorrection


class ExamPaperAdminAPITests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_dir.cleanup)
        self.settings(MEDIA_ROOT=self.media_dir.name)

        self.subject = Subject.objects.create(
            name='Mathematics', slug='mathematics-al', level='al'
        )
        self.admin = get_user_model().objects.create_user(
            username='exam-admin',
            email='exam-admin@example.test',
            password='test-password',
            role='admin',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.paper_data = {
            'subject': self.subject.pk,
            'year': 2025,
            'session': 'june',
            'paper_number': 1,
            'paper_type': 'official',
            'title': 'Mathematics Paper 1',
        }

    @staticmethod
    def pdf(name='document.pdf'):
        return SimpleUploadedFile(
            name, b'%PDF-1.4\nTest PDF content\n%%EOF', content_type='application/pdf'
        )

    def create_paper(self):
        response = self.client.post(
            '/api/exams/papers/create/',
            {**self.paper_data, 'source_pdf': self.pdf('paper.pdf')},
            format='multipart',
        )
        self.assertEqual(response.status_code, 201, response.data)
        return ExamPaper.objects.get(pk=response.data['id'])

    def test_admin_can_add_pdf_exam_and_duplicate_pdf_is_rejected(self):
        response = self.client.post(
            '/api/exams/papers/create/',
            {**self.paper_data, 'source_pdf': self.pdf('paper.pdf')},
            format='multipart',
        )

        self.assertEqual(response.status_code, 201, response.data)
        paper = ExamPaper.objects.get(pk=response.data['id'])
        self.assertTrue(paper.source_pdf.storage.exists(paper.source_pdf.name))

        duplicate = self.client.post(
            '/api/exams/papers/create/',
            {**self.paper_data, 'source_pdf': self.pdf('duplicate.pdf')},
            format='multipart',
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn('source_pdf', duplicate.data)
        self.assertEqual(ExamPaper.objects.count(), 1)

    def test_non_admin_cannot_add_exam(self):
        student = get_user_model().objects.create_user(
            username='exam-student',
            email='exam-student@example.test',
            password='test-password',
            role='student',
        )
        self.client.force_authenticate(student)

        response = self.client.post(
            '/api/exams/papers/create/',
            {**self.paper_data, 'source_pdf': self.pdf()},
            format='multipart',
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(ExamPaper.objects.count(), 0)

    def test_admin_can_publish_structured_and_pdf_correction(self):
        paper = self.create_paper()
        questions = [{
            'number': '1',
            'statement': 'Solve the equation.',
            'answer': 'x = 2',
            'explanation_fr': 'On isole x.',
            'kind': 'structured',
        }]

        response = self.client.post(
            f'/api/exams/papers/{paper.pk}/correction/',
            {
                'correction_pdf': self.pdf('correction.pdf'),
                'questions': json.dumps(questions),
                'publish': 'true',
                'coverage_complete': 'true',
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 201, response.data)
        correction = PaperCorrection.objects.get(paper=paper)
        self.assertEqual(correction.status, PaperCorrection.Status.PUBLISHED)
        self.assertTrue(
            correction.correction_pdf.storage.exists(correction.correction_pdf.name)
        )
        self.assertEqual(QuestionCorrection.objects.filter(version=correction).count(), 1)

        self.client.force_authenticate(None)
        public_correction = self.client.get(
            f'/api/exams/papers/{paper.pk}/correction/'
        )
        self.assertEqual(public_correction.status_code, 200)
        self.assertEqual(public_correction.data['questions'][0]['question']['number'], '1')
        self.assertTrue(public_correction.data['paper']['correction_available'])

        correction_pdf = self.client.get(
            f'/api/exams/papers/{paper.pk}/correction-pdf/'
        )
        self.assertEqual(correction_pdf.status_code, 200)
        self.assertEqual(correction_pdf['Content-Type'], 'application/pdf')
        self.assertTrue(
            b''.join(correction_pdf.streaming_content).startswith(b'%PDF-')
        )

    def test_draft_correction_is_not_public(self):
        paper = self.create_paper()
        response = self.client.post(
            f'/api/exams/papers/{paper.pk}/correction/',
            {
                'questions': json.dumps([{
                    'number': '1',
                    'statement': 'Solve the equation.',
                    'answer': 'x = 2',
                }]),
                'publish': 'false',
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, 201, response.data)

        self.client.force_authenticate(None)
        correction = self.client.get(
            f'/api/exams/papers/{paper.pk}/correction/'
        )
        paper_list = self.client.get('/api/exams/papers/')

        self.assertEqual(correction.status_code, 404)
        self.assertFalse(paper_list.data[0]['correction_available'])

    def test_invalid_pdf_is_rejected(self):
        response = self.client.post(
            '/api/exams/papers/create/',
            {
                **self.paper_data,
                'source_pdf': SimpleUploadedFile(
                    'not-a-pdf.txt', b'not a PDF', content_type='text/plain'
                ),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('source_pdf', response.data)
