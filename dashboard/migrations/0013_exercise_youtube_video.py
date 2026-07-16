from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0012_exercise_static_image_paths"),
    ]

    operations = [
        migrations.AddField(
            model_name="exercise",
            name="video_credit",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="exercise",
            name="video_url",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
