from django.core.management.base import BaseCommand

from dashboard.models import WorkoutRoutine
from dashboard.services import GOAL_PRESETS, estimate_workout_calories, estimate_workout_duration


class Command(BaseCommand):
    help = "Recalcula duracao e calorias das planilhas existentes com base nos exercicios."

    def add_arguments(self, parser):
        parser.add_argument(
            "--templates",
            action="store_true",
            help="Inclui planilhas modelo do sistema.",
        )

    def handle(self, *args, **options):
        queryset = WorkoutRoutine.objects.prefetch_related("items__exercise")
        if not options["templates"]:
            queryset = queryset.filter(is_template=False)

        updated = 0
        skipped = 0

        for routine in queryset:
            items = [
                {
                    "exercise": item.exercise,
                    "sets": item.sets,
                    "reps": item.reps,
                }
                for item in routine.items.all()
            ]
            if not items:
                skipped += 1
                continue

            preset = GOAL_PRESETS.get(routine.goal, GOAL_PRESETS["hipertrofia"])
            duration = estimate_workout_duration(routine.goal, items, preset["duration"])
            calories = estimate_workout_calories(routine.goal, duration, items, preset["calories"])
            first_image = next((item["exercise"].image_url for item in items if item["exercise"].image_url), "")

            routine.duration_minutes = duration
            routine.calories = calories
            if first_image:
                routine.image_url = first_image
            routine.save(update_fields=["duration_minutes", "calories", "image_url"])
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Planilhas recalculadas: {updated}. Ignoradas sem exercicios: {skipped}."
            )
        )
