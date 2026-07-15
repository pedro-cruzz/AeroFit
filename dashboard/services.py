from django.db import transaction

from .models import Exercise, WorkoutExercise, WorkoutRoutine


GOAL_PRESETS = {
    "forca": {"duration": 60, "calories": 430, "level": "Intermediario", "description": "Treino estruturado para forca maxima e controle tecnico."},
    "hipertrofia": {"duration": 55, "calories": 390, "level": "Intermediario", "description": "Volume moderado com foco em tensao mecanica e consistencia."},
    "endurance": {"duration": 35, "calories": 330, "level": "Base aerobica", "description": "Sessao para eficiencia cardiovascular e ritmo sustentavel."},
    "mobilidade": {"duration": 30, "calories": 140, "level": "Recuperacao", "description": "Fluxo de mobilidade para amplitude, respiracao e regeneracao."},
    "hiit": {"duration": 28, "calories": 360, "level": "Avancado", "description": "Blocos curtos de alta intensidade com recuperacao controlada."},
}


def montar_treino(name, goal, exercise_ids=None, exercise_configs=None):
    exercise_ids = [int(item) for item in exercise_ids or [] if str(item).isdigit()]
    exercise_configs = exercise_configs or {}
    preset = GOAL_PRESETS.get(goal, GOAL_PRESETS["hipertrofia"])

    if exercise_ids:
        exercises = list(Exercise.objects.filter(id__in=exercise_ids))
        exercises.sort(key=lambda exercise: exercise_ids.index(exercise.id))
    else:
        exercises = list(Exercise.objects.filter(focus=goal)[:5])
        if len(exercises) < 4:
            extra = Exercise.objects.exclude(id__in=[exercise.id for exercise in exercises])[: 4 - len(exercises)]
            exercises.extend(extra)

    if not exercises:
        raise ValueError("Cadastre pelo menos um exercicio antes de montar um treino.")

    with transaction.atomic():
        routine = WorkoutRoutine.objects.create(
            name=name.strip() or f"Treino de {dict(WorkoutRoutine.GOAL_CHOICES).get(goal, goal)}",
            goal=goal,
            description=preset["description"],
            duration_minutes=preset["duration"],
            calories=preset["calories"],
            level=preset["level"],
            progress=0,
            is_template=False,
            image_url=exercises[0].image_url,
        )

        WorkoutExercise.objects.bulk_create(
            [
                WorkoutExercise(
                    routine=routine,
                    exercise=exercise,
                    order=index,
                    sets=exercise_configs.get(exercise.id, {}).get("sets") or exercise.default_sets,
                    reps=exercise_configs.get(exercise.id, {}).get("reps") or exercise.default_reps,
                    rest_seconds=exercise.rest_seconds,
                )
                for index, exercise in enumerate(exercises, start=1)
            ]
        )

    return routine
