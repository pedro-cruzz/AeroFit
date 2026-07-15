from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import DevUserCreationForm, ExerciseCreationForm
from .models import (
    Achievement,
    AthleteProfile,
    Challenge,
    Exercise,
    ExerciseCategory,
    LeaderboardEntry,
    PhysicalAttribute,
    ProgressEntry,
    WeeklyPlan,
    WorkoutRoutine,
    WorkoutSession,
    WorkoutSessionExercise,
)
from .services import montar_treino


User = get_user_model()
PROFILE_IMAGE = "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=240&q=80"


def base_context(active):
    profile = AthleteProfile.objects.first()
    return {
        "active": active,
        "profile": profile,
        "profile_image": profile.image_url if profile and profile.image_url else PROFILE_IMAGE,
        "nav_items": [
            {"label": "Dashboard", "icon": "dashboard", "url_name": "dashboard:home", "key": "home"},
            {"label": "Treinos", "icon": "fitness_center", "url_name": "dashboard:workouts", "key": "workouts"},
            {"label": "Progresso", "icon": "query_stats", "url_name": "dashboard:progress", "key": "progress"},
            {"label": "Elite", "icon": "workspace_premium", "url_name": "dashboard:elite", "key": "elite"},
            {"label": "Dev", "icon": "admin_panel_settings", "url_name": "dashboard:dev_profile", "key": "dev"},
        ],
    }


def get_online_users():
    online_user_ids = set()
    active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
    for session in active_sessions:
        user_id = session.get_decoded().get("_auth_user_id")
        if user_id:
            online_user_ids.add(user_id)

    return User.objects.filter(id__in=online_user_ids).order_by("username")


def dashboard(request):
    context = base_context("home")
    today_plan = WeeklyPlan.objects.filter(is_today=True).select_related("routine").first()
    today_items = []
    if today_plan and today_plan.routine:
        today_items = today_plan.routine.items.select_related("exercise")

    context.update(
        {
            "attributes": PhysicalAttribute.objects.all(),
            "week_plan": WeeklyPlan.objects.select_related("routine"),
            "today_plan": today_plan,
            "today_workout": today_items,
        }
    )
    return render(request, "dashboard/home.html", context)


def workouts(request):
    context = base_context("workouts")
    context.update(
        {
            "routines": WorkoutRoutine.objects.prefetch_related("items").all(),
            "categories": ExerciseCategory.objects.all(),
            "suggestions": WorkoutRoutine.objects.filter(is_template=True).order_by("progress")[:2],
        }
    )
    return render(request, "dashboard/workouts.html", context)


def workout_builder(request):
    context = base_context("workouts")

    if request.method == "POST":
        exercise_ids = request.POST.getlist("exercises")
        exercise_configs = {}
        for exercise_id in exercise_ids:
            if not str(exercise_id).isdigit():
                continue
            sets_value = request.POST.get(f"sets_{exercise_id}", "")
            reps_value = request.POST.get(f"reps_{exercise_id}", "").strip()
            exercise_configs[int(exercise_id)] = {
                "sets": int(sets_value) if sets_value.isdigit() else None,
                "reps": reps_value,
            }

        try:
            routine = montar_treino(
                name=request.POST.get("name", ""),
                goal=request.POST.get("goal", "hipertrofia"),
                exercise_ids=exercise_ids,
                exercise_configs=exercise_configs,
            )
        except ValueError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f"Treino {routine.name} montado e salvo no SQLite.")
            return redirect("dashboard:routine_detail", pk=routine.pk)

    context.update(
        {
            "goals": WorkoutRoutine.GOAL_CHOICES,
            "exercises": Exercise.objects.select_related("category"),
        }
    )
    return render(request, "dashboard/workout_builder.html", context)


def routine_detail(request, pk):
    routine = get_object_or_404(WorkoutRoutine.objects.prefetch_related("items__exercise"), pk=pk)
    if request.method == "POST":
        session = WorkoutSession.objects.create(
            routine=routine,
            notes=request.POST.get("notes", "").strip(),
        )
        logs = []
        for item in routine.items.all():
            completed = request.POST.get(f"completed_{item.id}") == "on"
            load_value = request.POST.get(f"load_{item.id}", "").replace(",", ".").strip()
            load_kg = None
            if load_value:
                try:
                    load_kg = Decimal(load_value)
                except InvalidOperation:
                    load_kg = None
            logs.append(
                WorkoutSessionExercise(
                    session=session,
                    workout_exercise=item,
                    completed=completed,
                    load_kg=load_kg,
                    sets_done=item.sets if completed else 0,
                    reps_done=item.reps if completed else "",
                )
            )
        WorkoutSessionExercise.objects.bulk_create(logs)
        messages.success(request, "Treino concluido e cargas salvas no SQLite.")
        return redirect("dashboard:routine_detail", pk=routine.pk)

    context = base_context("workouts")
    context["routine"] = routine
    context["sessions"] = routine.sessions.prefetch_related("exercise_logs__workout_exercise__exercise")[:5]
    return render(request, "dashboard/routine_detail.html", context)


@require_POST
def delete_routine(request, pk):
    routine = get_object_or_404(WorkoutRoutine, pk=pk)
    routine_name = routine.name
    routine.delete()
    messages.success(request, f"Treino {routine_name} excluido.")
    return redirect("dashboard:workouts")


@require_POST
def delete_workout_exercise(request, pk, item_pk):
    routine = get_object_or_404(WorkoutRoutine, pk=pk)
    item = get_object_or_404(routine.items.select_related("exercise"), pk=item_pk)
    exercise_name = item.exercise.name
    item.delete()

    for order, remaining_item in enumerate(routine.items.all(), start=1):
        if remaining_item.order != order:
            remaining_item.order = order
            remaining_item.save(update_fields=["order"])

    messages.success(request, f"Exercicio {exercise_name} removido do treino.")
    return redirect("dashboard:routine_detail", pk=routine.pk)


def dev_profile(request):
    user_form = DevUserCreationForm()
    exercise_form = ExerciseCreationForm()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create_user":
            user_form = DevUserCreationForm(request.POST)
            if user_form.is_valid():
                user = user_form.save()
                messages.success(request, f"Usuario {user.username} criado.")
                return redirect("dashboard:dev_profile")
            messages.error(request, "Revise os dados do usuario antes de salvar.")

        if action == "create_exercise":
            exercise_form = ExerciseCreationForm(request.POST)
            if exercise_form.is_valid():
                exercise = exercise_form.save()
                messages.success(request, f"Exercicio {exercise.name} cadastrado.")
                return redirect("dashboard:dev_profile")
            messages.error(request, "Revise os dados do exercicio antes de salvar.")

    online_users = get_online_users()
    users = User.objects.order_by("-date_joined", "username")

    context = base_context("dev")
    context.update(
        {
            "user_form": user_form,
            "exercise_form": exercise_form,
            "users": users,
            "online_users": online_users,
            "online_user_ids": {user.id for user in online_users},
            "total_users": users.count(),
            "total_exercises": Exercise.objects.count(),
            "recent_exercises": Exercise.objects.select_related("category").order_by("-id")[:8],
        }
    )
    return render(request, "dashboard/dev_profile.html", context)


def progress(request):
    context = base_context("progress")
    context.update(
        {
            "history": ProgressEntry.objects.all(),
            "achievements": Achievement.objects.all(),
        }
    )
    return render(request, "dashboard/progress.html", context)


def elite(request):
    context = base_context("elite")
    context.update(
        {
            "ranking": LeaderboardEntry.objects.all(),
            "challenges": Challenge.objects.all(),
        }
    )
    return render(request, "dashboard/elite.html", context)


def exercise_detail(request, slug):
    exercise = get_object_or_404(Exercise.objects.select_related("category"), slug=slug)
    context = base_context("exercise")
    context["exercise"] = exercise
    return render(request, "dashboard/exercise_detail.html", context)
