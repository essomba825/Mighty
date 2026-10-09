# Conversion des anciens Course -> Chapter / Lesson / Resource, sans perte de données.
import unicodedata

from django.db import migrations


def slugify_ascii(value):
    base = unicodedata.normalize('NFKD', value.lower())
    cleaned = ''.join(c for c in base if not unicodedata.combining(c))
    return '-'.join(''.join(c if c.isalnum() else ' ' for c in cleaned).split())


def convert(apps, schema_editor):
    Subject = apps.get_model('education', 'Subject')
    Chapter = apps.get_model('education', 'Chapter')
    Lesson = apps.get_model('education', 'Lesson')
    Resource = apps.get_model('education', 'Resource')
    Quiz = apps.get_model('education', 'Quiz')
    Course = apps.get_model('education', 'Course')

    # Slugs pour les matières existantes
    for subject in Subject.objects.all():
        if not subject.slug:
            subject.slug = slugify_ascii(f'{subject.name} {subject.level}')
            subject.save()

    # Ancien modèle Course -> nouvelle structure
    chapters = {}
    for course in Course.objects.select_related('subject').order_by(
            'subject_id', 'chapter', 'id'):
        key = (course.subject_id, course.chapter)
        if key not in chapters:
            chapters[key] = Chapter.objects.create(
                subject_id=course.subject_id,
                order=course.chapter or 1,
                title=f'Chapter {course.chapter or 1}',
                description='',
            )
        chapter = chapters[key]
        lesson = Lesson.objects.create(
            chapter=chapter,
            order=chapter.lessons.count() + 1,
            kind='exam_paper' if course.is_exam_paper else 'lesson',
            title=course.title,
            content=course.content or '',
            video_url=course.video_url or '',
            status=course.status if course.status in ('draft', 'pending', 'published')
            else 'published',
            teacher=course.teacher,
        )
        if course.pdf:
            Resource.objects.create(lesson=lesson, order=1, kind='pdf',
                                    title='Support PDF', file=course.pdf)
        if course.video_url:
            Resource.objects.create(lesson=lesson, order=2, kind='video',
                                    title='Video', url=course.video_url)
        Quiz.objects.filter(course_id=course.id).update(lesson=lesson)


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0002_remove_quiz_course_quiz_title_fr_subject_color_and_more'),
    ]

    operations = [
        migrations.RunPython(convert, migrations.RunPython.noop),
    ]
