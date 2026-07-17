import re
from decimal import Decimal

from django.db import transaction

from .models import AthleteProfile, Exercise, PhysicalAttribute, UserXpEvent, WorkoutExercise, WorkoutRoutine


GOAL_PRESETS = {
    "forca": {"duration": 60, "calories": 430, "level": "Intermediario", "description": "Treino estruturado para forca maxima e controle tecnico."},
    "hipertrofia": {"duration": 55, "calories": 390, "level": "Intermediario", "description": "Volume moderado com foco em tensao mecanica e consistencia."},
    "endurance": {"duration": 35, "calories": 330, "level": "Base aerobica", "description": "Sessao para eficiencia cardiovascular e ritmo sustentavel."},
    "mobilidade": {"duration": 30, "calories": 140, "level": "Recuperacao", "description": "Fluxo de mobilidade para amplitude, respiracao e regeneracao."},
    "hiit": {"duration": 28, "calories": 360, "level": "Avancado", "description": "Blocos curtos de alta intensidade com recuperacao controlada."},
}
DEFAULT_PHYSICAL_ATTRIBUTES = [
    {"name": "Forca", "level": 1, "progress": 0, "accent": "cyan", "order": 1},
    {"name": "Resistencia", "level": 1, "progress": 0, "accent": "lime", "order": 2},
    {"name": "Base", "level": 1, "progress": 0, "accent": "indigo", "order": 3},
]
BASE_ATTRIBUTE_TERMS = (
    "quadriceps",
    "quadril",
    "glute",
    "posterior",
    "panturr",
    "adutor",
    "abdutor",
    "coxa",
    "perna",
    "joelho",
    "tornoz",
    "isquio",
    "core",
)


def montar_treino(name, goal, exercise_ids=None, exercise_configs=None, owner=None, training_days=None):
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

    planned_items = [
        {
            "exercise": exercise,
            "sets": exercise_configs.get(exercise.id, {}).get("sets") or exercise.default_sets,
            "reps": exercise_configs.get(exercise.id, {}).get("reps") or exercise.default_reps,
        }
        for exercise in exercises
    ]
    duration_minutes = estimate_workout_duration(goal, planned_items, preset["duration"])
    calories = estimate_workout_calories(goal, duration_minutes, planned_items, preset["calories"])

    with transaction.atomic():
        routine = WorkoutRoutine.objects.create(
            owner=owner,
            name=name.strip() or f"Treino de {dict(WorkoutRoutine.GOAL_CHOICES).get(goal, goal)}",
            goal=goal,
            description=preset["description"],
            duration_minutes=duration_minutes,
            calories=calories,
            level=preset["level"],
            progress=0,
            is_template=False,
            training_days=training_days or [],
            image_url=WorkoutRoutine.GOAL_COVER_IMAGES.get(goal, exercises[0].image_url),
        )

        WorkoutExercise.objects.bulk_create(
            [
                WorkoutExercise(
                    routine=routine,
                    exercise=item["exercise"],
                    order=index,
                    sets=item["sets"],
                    reps=item["reps"],
                    rest_seconds=item["exercise"].rest_seconds,
                )
                for index, item in enumerate(planned_items, start=1)
            ]
        )

    return routine


def parse_minutes_from_reps(reps):
    match = re.search(r"(\d+)\s*min", str(reps).lower())
    if match:
        return int(match.group(1))

    distance_match = re.search(r"(\d+)\s*km", str(reps).lower())
    if distance_match:
        return int(distance_match.group(1)) * 6

    return None


def estimate_exercise_minutes(exercise, sets, reps):
    if exercise.is_run or exercise.focus in {"endurance", "hiit"}:
        minutes = parse_minutes_from_reps(reps)
        if minutes:
            return minutes
        return max(8, min(30, sets * 3))

    active_minutes = max(1, round(sets * 0.75))
    rest_minutes = max(0, round((max(sets - 1, 0) * exercise.rest_seconds) / 60))
    return max(4, active_minutes + rest_minutes + 2)


def estimate_workout_duration(goal, planned_items, fallback):
    if not planned_items:
        return fallback

    total = sum(
        estimate_exercise_minutes(item["exercise"], item["sets"], item["reps"])
        for item in planned_items
    )
    setup_buffer = 5 if goal in {"forca", "hipertrofia"} else 3
    return max(12, min(120, total + setup_buffer))


def estimate_workout_calories(goal, duration_minutes, planned_items, fallback):
    if not planned_items:
        return fallback

    factor_by_goal = {
        "forca": 6.6,
        "hipertrofia": 6.2,
        "endurance": 8.4,
        "hiit": 10.5,
        "mobilidade": 3.6,
    }
    factor = factor_by_goal.get(goal, 6.0)
    exercise_bonus = len(planned_items) * (8 if goal in {"forca", "hipertrofia"} else 5)
    return max(40, round((duration_minutes * factor) + exercise_bonus))


def get_or_create_athlete_profile(user):
    display_name = user.get_full_name() or user.username
    profile, _ = AthleteProfile.objects.get_or_create(
        user=user,
        defaults={"name": display_name},
    )
    if not profile.name:
        profile.name = display_name
        profile.save(update_fields=["name"])
    return profile


def ensure_physical_attributes(user):
    existing = set(PhysicalAttribute.objects.filter(user=user).values_list("name", flat=True))
    missing = [
        PhysicalAttribute(user=user, **attribute)
        for attribute in DEFAULT_PHYSICAL_ATTRIBUTES
        if attribute["name"] not in existing
    ]
    if missing:
        PhysicalAttribute.objects.bulk_create(missing)
    return PhysicalAttribute.objects.filter(user=user).order_by("order", "name")


def attribute_name_for_exercise(exercise):
    target = f"{exercise.name} {exercise.primary_muscle} {exercise.secondary_muscles}".lower()
    if exercise.is_run or exercise.focus in {"endurance", "hiit"}:
        return "Resistencia"
    if exercise.focus == "mobilidade" or any(term in target for term in BASE_ATTRIBUTE_TERMS):
        return "Base"
    return "Forca"


def calculate_log_xp(log):
    if not log.completed:
        return 0

    exercise = log.workout_exercise.exercise
    sets_done = log.sets_done or log.workout_exercise.sets
    base_xp = 24 if exercise.is_run else 18
    set_xp = sets_done * (10 if exercise.is_run else 8)
    load_bonus = 0
    if log.load_kg:
        load_bonus = min(int(Decimal(log.load_kg) * Decimal("0.35")), 45)
    return base_xp + set_xp + load_bonus


def add_xp_to_profile(profile, xp_amount):
    profile.total_xp += xp_amount
    profile.elite_points += xp_amount
    if not profile.next_level_xp:
        profile.next_level_xp = 1000
    while profile.total_xp >= profile.next_level_xp:
        profile.level += 1
        profile.next_level_xp += max(1000, profile.level * 250)
    profile.save(update_fields=["total_xp", "elite_points", "level", "next_level_xp"])


def add_xp_to_attribute(attribute, xp_amount):
    total_progress = attribute.progress + xp_amount
    if total_progress >= 100:
        attribute.level += total_progress // 100
        attribute.progress = total_progress % 100
    else:
        attribute.progress = total_progress
    attribute.save(update_fields=["level", "progress"])


def award_workout_xp(user, session):
    profile = get_or_create_athlete_profile(user)
    attributes = {attribute.name: attribute for attribute in ensure_physical_attributes(user)}
    totals = {"Forca": 0, "Resistencia": 0, "Base": 0}
    exercise_details = []

    for log in session.exercise_logs.select_related("workout_exercise__exercise"):
        xp_amount = calculate_log_xp(log)
        if not xp_amount:
            continue
        attribute_name = attribute_name_for_exercise(log.workout_exercise.exercise)
        totals[attribute_name] += xp_amount
        exercise_details.append(
            {
                "exercise": log.workout_exercise.exercise.name,
                "attribute": attribute_name,
                "xp": xp_amount,
            }
        )

    total_xp = sum(totals.values())
    if not total_xp:
        return None

    with transaction.atomic():
        add_xp_to_profile(profile, total_xp)
        for attribute_name, xp_amount in totals.items():
            if xp_amount and attribute_name in attributes:
                add_xp_to_attribute(attributes[attribute_name], xp_amount)

        return UserXpEvent.objects.create(
            user=user,
            session=session,
            total_xp=total_xp,
            strength_xp=totals["Forca"],
            endurance_xp=totals["Resistencia"],
            base_xp=totals["Base"],
            detail={"exercises": exercise_details},
        )
