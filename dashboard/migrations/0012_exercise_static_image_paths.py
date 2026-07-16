from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0011_exercise_created_by"),
    ]

    operations = [
        migrations.AlterField(
            model_name="exercise",
            name="anatomy_image_url",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AlterField(
            model_name="exercise",
            name="image_url",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
