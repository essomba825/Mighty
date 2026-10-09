# Nettoyage final : colonnes legacy supprimées après conversion (0003), champs durcis.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0003_convert_courses'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subject',
            name='slug',
            field=models.SlugField(max_length=120, unique=True),
        ),
        migrations.AlterField(
            model_name='quiz',
            name='lesson',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                    related_name='quizzes', to='education.lesson'),
        ),
        migrations.RemoveField(
            model_name='quiz',
            name='course',
        ),
        migrations.DeleteModel(
            name='Course',
        ),
    ]
