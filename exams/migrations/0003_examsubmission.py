# Generated migration for ExamSubmission model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0001_initial'),
        ('exams', '0002_papercorrection_correction_pdf'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ExamSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resource_type', models.CharField(
                    choices=[
                        ('past_paper', 'Past Paper / Épreuve'),
                        ('correction', 'Correction / Corrigé'),
                        ('notes', 'Notes de cours'),
                        ('textbook', 'Livre / Manuel'),
                        ('other', 'Autre ressource'),
                    ],
                    default='past_paper',
                    max_length=20,
                )),
                ('level', models.CharField(
                    choices=[('ol', 'GCE O/L'), ('al', 'GCE A/L')],
                    max_length=2,
                )),
                ('year', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('pdf_file', models.FileField(upload_to='submissions/')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'En attente'),
                        ('approved', 'Approuvé'),
                        ('rejected', 'Refusé'),
                    ],
                    default='pending',
                    max_length=12,
                )),
                ('reviewer_note', models.TextField(blank=True)),
                ('submitted_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('submitted_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='exam_submissions',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('subject', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='exam_submissions',
                    to='education.subject',
                )),
                ('reviewed_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='exam_submissions_reviewed',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-submitted_at'],
            },
        ),
    ]

