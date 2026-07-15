from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.contrib.sessions.models import Session
from django.db.models import Count, Max, Prefetch, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import DevUserCreationForm, ExerciseCreationForm, RoutineEditForm, SecureAuthenticationForm
from .models import (
    Achievement,
    AthleteProfile,
    Challenge,
    Exercise,
    ExerciseCategory,
    LeaderboardEntry,
    PhysicalAttribute,
    ProgressEntry,
    UserActivityLog,
    WeeklyPlan,
    WorkoutRoutine,
    WorkoutSession,
    WorkoutSessionExercise,
)
from .services import award_workout_xp, ensure_physical_attributes, get_or_create_athlete_profile, montar_treino


User = get_user_model()
PROFILE_IMAGE = "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=240&q=80"
LOWER_BODY_TERMS = (
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
)

class SecureLoginView(LoginView):
    authentication_form = SecureAuthenticationForm
    redirect_authenticated_user = True
    template_name = "dashboard/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(base_context("login"))
        return context


def get_athlete_profile(user=None):
    if user and user.is_authenticated:
        return get_or_create_athlete_profile(user)
    return AthleteProfile.objects.filter(user__isnull=True).first() or AthleteProfile.objects.first()


def get_physical_attributes(user):
    if user and user.is_authenticated:
        return ensure_physical_attributes(user)
    return PhysicalAttribute.objects.filter(user__isnull=True).order_by("order", "name")


def base_context(active, user=None):
    profile = get_athlete_profile(user)
    nav_items = [
        {"label": "Dashboard", "icon": "dashboard", "url_name": "dashboard:home", "key": "home"},
        {"label": "Treinos", "icon": "fitness_center", "url_name": "dashboard:workouts", "key": "workouts"},
        {"label": "Progresso", "icon": "query_stats", "url_name": "dashboard:progress", "key": "progress"},
        {"label": "Elite", "icon": "workspace_premium", "url_name": "dashboard:elite", "key": "elite"},
    ]
    if user and user.is_staff:
        nav_items.append({"label": "Dev", "icon": "admin_panel_settings", "url_name": "dashboard:dev_profile", "key": "dev"})
        nav_items.append({"label": "Exercicios", "icon": "library_add", "url_name": "dashboard:dev_exercise_catalog", "key": "dev_exercises"})

    return {
        "active": active,
        "profile": profile,
        "profile_image": profile.image_url if profile and profile.image_url else PROFILE_IMAGE,
        "nav_items": nav_items,
    }


def get_online_users():
    online_user_ids = set()
    active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
    for session in active_sessions:
        user_id = session.get_decoded().get("_auth_user_id")
        if user_id:
            online_user_ids.add(user_id)

    return User.objects.filter(id__in=online_user_ids).order_by("username")


def get_recently_active_user_ids(minutes=5):
    since = timezone.now() - timezone.timedelta(minutes=minutes)
    return set(
        UserActivityLog.objects.filter(created_at__gte=since)
        .values_list("user_id", flat=True)
        .distinct()
    )


def current_weekday_key():
    keys = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
    return keys[timezone.localdate().weekday()]


def build_user_week_plan(user_routines, today_key):
    week_plan = []
    for day_key, day_label in WorkoutRoutine.WEEKDAY_CHOICES:
        day_routines = [routine for routine in user_routines if day_key in routine.training_days]
        if day_routines:
            week_plan.append(
                {
                    "key": day_key,
                    "day": day_label,
                    "routines": day_routines,
                    "is_today": day_key == today_key,
                }
            )
    return week_plan


def build_workout_category_groups():
    categories = ExerciseCategory.objects.prefetch_related(
        Prefetch("exercises", queryset=Exercise.objects.order_by("name"))
    ).all()
    groups = []
    for category in categories:
        upper_exercises = []
        lower_exercises = []
        for exercise in category.exercises.all():
            target = f"{exercise.name} {exercise.primary_muscle} {exercise.secondary_muscles}".lower()
            if exercise.is_run or any(term in target for term in LOWER_BODY_TERMS):
                lower_exercises.append(exercise)
            else:
                upper_exercises.append(exercise)
        groups.append(
            {
                "category": category,
                "upper_exercises": upper_exercises,
                "lower_exercises": lower_exercises,
            }
        )
    return groups


@login_required
def dashboard(request):
    context = base_context("home", request.user)
    user_routines = list(
        WorkoutRoutine.objects.filter(owner=request.user, is_template=False)
        .prefetch_related("items__exercise")
    )
    today_key = current_weekday_key()
    today_routine = next((routine for routine in user_routines if today_key in routine.training_days), None)
    today_items = []
    if today_routine:
        today_items = today_routine.items.select_related("exercise")
    today_rows = [
        {
            "item": item,
            "previous_load": previous_load_label(item),
        }
        for item in today_items
    ]

    context.update(
        {
            "attributes": get_physical_attributes(request.user),
            "week_plan": build_user_week_plan(user_routines, today_key),
            "today_routine": today_routine,
            "today_key": today_key,
            "today_workout": today_items,
            "today_workout_rows": today_rows,
        }
    )
    return render(request, "dashboard/home.html", context)


@login_required
def workouts(request):
    context = base_context("workouts", request.user)
    show_workout_modal = request.GET.get("modal") == "1"
    if request.method == "POST":
        show_workout_modal = True
        routine = create_workout_from_request(request)
        if routine:
            messages.success(request, f"Treino {routine.name} montado e salvo para o aluno.")
            return redirect("dashboard:routine_detail", pk=routine.pk)

    workout_categories = build_workout_category_groups()
    categories = [entry["category"] for entry in workout_categories]
    context.update(
        {
            "routines": WorkoutRoutine.objects.filter(owner=request.user, is_template=False).prefetch_related("items"),
            "categories": categories,
            "workout_categories": workout_categories,
            "goals": WorkoutRoutine.GOAL_CHOICES,
            "weekday_choices": WorkoutRoutine.WEEKDAY_CHOICES,
            "show_workout_modal": show_workout_modal,
        }
    )
    return render(request, "dashboard/workouts.html", context)


@login_required
def workout_builder(request):
    if request.method == "POST":
        routine = create_workout_from_request(request)
        if routine:
            messages.success(request, f"Treino {routine.name} montado e salvo para o aluno.")
            return redirect("dashboard:routine_detail", pk=routine.pk)
    return redirect(f"{reverse('dashboard:workouts')}?modal=1")


def create_workout_from_request(request):
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
        return montar_treino(
            name=request.POST.get("name", ""),
            goal=request.POST.get("goal", "hipertrofia"),
            exercise_ids=exercise_ids,
            exercise_configs=exercise_configs,
            owner=request.user,
            training_days=request.POST.getlist("training_days"),
        )
    except ValueError as error:
        messages.error(request, str(error))
        return None


def parse_rpe(value):
    if not str(value).isdigit():
        return None
    rpe = int(value)
    if 1 <= rpe <= 10:
        return rpe
    return None


def previous_load_label(item):
    previous_log = (
        item.session_logs.filter(completed=True, load_kg__isnull=False)
        .select_related("session")
        .order_by("-session__completed_at", "-id")
        .first()
    )
    if not previous_log:
        return ""
    load_text = format(previous_log.load_kg.normalize(), "f").rstrip("0").rstrip(".")
    return f"Anterior: {load_text} kg"


@login_required
def routine_detail(request, pk):
    routine = get_object_or_404(
        WorkoutRoutine.objects.filter(Q(owner=request.user) | Q(owner__isnull=True, is_template=True)).prefetch_related("items__exercise"),
        pk=pk,
    )
    can_manage = routine.owner_id == request.user.id and not routine.is_template
    if request.method == "POST":
        if not can_manage:
            messages.error(request, "Este modelo e apenas sugestao. Monte sua propria planilha antes de executar.")
            return redirect("dashboard:workout_builder")

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
            rpe = parse_rpe(request.POST.get(f"rpe_{item.id}", ""))
            logs.append(
                WorkoutSessionExercise(
                    session=session,
                    workout_exercise=item,
                    completed=completed,
                    load_kg=load_kg,
                    sets_done=item.sets if completed else 0,
                    reps_done=item.reps if completed else "",
                    rpe=rpe,
                )
            )
        WorkoutSessionExercise.objects.bulk_create(logs)
        xp_event = award_workout_xp(request.user, session)
        if xp_event:
            messages.success(
                request,
                (
                    f"Treino concluido: +{xp_event.total_xp} XP "
                    f"(Forca +{xp_event.strength_xp}, Resistencia +{xp_event.endurance_xp}, Base +{xp_event.base_xp})."
                ),
            )
        else:
            messages.success(request, "Treino concluido e cargas salvas.")
        return redirect("dashboard:routine_detail", pk=routine.pk)

    context = base_context("workouts", request.user)
    context["routine"] = routine
    context["can_manage"] = can_manage
    context["execution_rows"] = [
        {
            "item": item,
            "previous_load": previous_load_label(item),
        }
        for item in routine.items.select_related("exercise")
    ]
    context["sessions"] = routine.sessions.prefetch_related("exercise_logs__workout_exercise__exercise")[:5]
    return render(request, "dashboard/routine_detail.html", context)


@login_required
def edit_routine(request, pk):
    routine = get_object_or_404(
        WorkoutRoutine.objects.prefetch_related("items__exercise"),
        pk=pk,
        owner=request.user,
        is_template=False,
    )
    form = RoutineEditForm(instance=routine)

    if request.method == "POST":
        form = RoutineEditForm(request.POST, instance=routine)
        if form.is_valid():
            form.save()
            messages.success(request, f"Treino {routine.name} atualizado.")
            return redirect("dashboard:routine_detail", pk=routine.pk)
        messages.error(request, "Revise os dados do treino antes de salvar.")

    context = base_context("workouts", request.user)
    context.update(
        {
            "routine": routine,
            "form": form,
            "item_rows": [
                {
                    "item": item,
                    "sets_field": form[f"sets_{item.id}"],
                    "reps_field": form[f"reps_{item.id}"],
                    "rest_field": form[f"rest_{item.id}"],
                }
                for item in routine.items.select_related("exercise")
            ],
        }
    )
    return render(request, "dashboard/routine_edit.html", context)


@login_required
@require_POST
def delete_routine(request, pk):
    routine = get_object_or_404(WorkoutRoutine, pk=pk, owner=request.user, is_template=False)
    routine_name = routine.name
    routine.delete()
    messages.success(request, f"Treino {routine_name} excluido.")
    return redirect("dashboard:workouts")


@login_required
@require_POST
def delete_workout_exercise(request, pk, item_pk):
    routine = get_object_or_404(WorkoutRoutine, pk=pk, owner=request.user, is_template=False)
    item = get_object_or_404(routine.items.select_related("exercise"), pk=item_pk)
    exercise_name = item.exercise.name
    item.delete()

    for order, remaining_item in enumerate(routine.items.all(), start=1):
        if remaining_item.order != order:
            remaining_item.order = order
            remaining_item.save(update_fields=["order"])

    messages.success(request, f"Exercicio {exercise_name} removido do treino.")
    return redirect("dashboard:routine_detail", pk=routine.pk)


@login_required
@user_passes_test(lambda user: user.is_staff, login_url="dashboard:home", redirect_field_name=None)
def dev_profile(request):
    online_users = get_online_users()
    active_user_ids = get_recently_active_user_ids()
    context = base_context("dev", request.user)
    context.update(
        {
            "total_users": User.objects.count(),
            "online_count": online_users.count(),
            "active_now_count": len(active_user_ids),
            "total_exercises": Exercise.objects.count(),
            "total_categories": ExerciseCategory.objects.count(),
            "recent_logs": UserActivityLog.objects.select_related("user")[:6],
        }
    )
    return render(request, "dashboard/dev_profile.html", context)


@login_required
@user_passes_test(lambda user: user.is_staff, login_url="dashboard:home", redirect_field_name=None)
def dev_users(request):
    user_form = DevUserCreationForm()
    show_user_modal = False

    if request.method == "POST":
        show_user_modal = True
        user_form = DevUserCreationForm(request.POST)
        if user_form.is_valid():
            user = user_form.save()
            messages.success(request, f"Aluno {user.username} criado.")
            return redirect("dashboard:dev_users")
        messages.error(request, "Revise os dados do aluno antes de salvar.")

    online_users = get_online_users()
    active_user_ids = get_recently_active_user_ids()
    users = User.objects.order_by("-date_joined", "username")

    context = base_context("dev", request.user)
    context.update(
        {
            "user_form": user_form,
            "users": users,
            "online_users": online_users,
            "online_user_ids": {user.id for user in online_users},
            "active_user_ids": active_user_ids,
            "total_users": users.count(),
            "show_user_modal": show_user_modal,
        }
    )
    return render(request, "dashboard/dev_users.html", context)


@login_required
@user_passes_test(lambda user: user.is_staff, login_url="dashboard:home", redirect_field_name=None)
def dev_training_catalog(request):
    exercise_form = ExerciseCreationForm()
    show_form = False

    if request.method == "POST":
        show_form = True
        exercise_form = ExerciseCreationForm(request.POST)
        if exercise_form.is_valid():
            exercise = exercise_form.save()
            messages.success(request, f"Treino {exercise.name} cadastrado.")
            return redirect("dashboard:dev_exercise_catalog")
        messages.error(request, "Revise os dados do treino antes de salvar.")

    categories = ExerciseCategory.objects.prefetch_related("exercises").annotate(total_exercises=Count("exercises"))
    context = base_context("dev_exercises", request.user)
    context.update(
        {
            "exercise_form": exercise_form,
            "categories": categories,
            "total_exercises": Exercise.objects.count(),
            "show_form": show_form,
        }
    )
    return render(request, "dashboard/dev_training_catalog.html", context)


@login_required
@user_passes_test(lambda user: user.is_staff, login_url="dashboard:home", redirect_field_name=None)
def dev_training_flow(request):
    context = base_context("dev", request.user)
    context.update(
        {
            "routines": WorkoutRoutine.objects.filter(owner=request.user, is_template=False).prefetch_related("items__exercise"),
            "total_routines": WorkoutRoutine.objects.filter(owner=request.user, is_template=False).count(),
            "total_sessions": WorkoutSession.objects.filter(routine__owner=request.user).count(),
            "sample_exercises": Exercise.objects.select_related("category")[:6],
        }
    )
    return render(request, "dashboard/dev_training_flow.html", context)


@login_required
@user_passes_test(lambda user: user.is_staff, login_url="dashboard:home", redirect_field_name=None)
def dev_edit_training(request, pk):
    exercise = get_object_or_404(Exercise.objects.select_related("category"), pk=pk)
    form = ExerciseCreationForm(instance=exercise)

    if request.method == "POST":
        form = ExerciseCreationForm(request.POST, instance=exercise)
        if form.is_valid():
            exercise = form.save()
            messages.success(request, f"Treino {exercise.name} atualizado.")
            return redirect("dashboard:dev_exercise_catalog")
        messages.error(request, "Revise os dados do treino antes de salvar.")

    context = base_context("dev_exercises", request.user)
    context.update({"exercise": exercise, "exercise_form": form})
    return render(request, "dashboard/dev_training_edit.html", context)


@login_required
@user_passes_test(lambda user: user.is_staff, login_url="dashboard:home", redirect_field_name=None)
@require_POST
def dev_delete_training(request, pk):
    exercise = get_object_or_404(Exercise, pk=pk)
    exercise_name = exercise.name
    try:
        exercise.delete()
    except ProtectedError:
        messages.error(request, f"Treino {exercise_name} esta em uso em planilhas e nao pode ser excluido.")
    else:
        messages.success(request, f"Treino {exercise_name} excluido da biblioteca.")
    return redirect("dashboard:dev_exercise_catalog")


@login_required
@user_passes_test(lambda user: user.is_staff, login_url="dashboard:home", redirect_field_name=None)
def dev_development(request):
    online_users = get_online_users()
    active_user_ids = get_recently_active_user_ids()
    users = User.objects.annotate(
        last_seen=Max("activity_logs__created_at"),
        activity_count=Count("activity_logs"),
    ).order_by("username")
    logs = UserActivityLog.objects.select_related("user")[:80]

    context = base_context("dev", request.user)
    context.update(
        {
            "users": users,
            "logs": logs,
            "online_user_ids": {user.id for user in online_users},
            "active_user_ids": active_user_ids,
            "online_count": online_users.count(),
            "active_now_count": len(active_user_ids),
            "total_logs": UserActivityLog.objects.count(),
        }
    )
    return render(request, "dashboard/dev_development.html", context)


@login_required
def progress(request):
    context = base_context("progress", request.user)
    context.update(
        {
            "history": ProgressEntry.objects.all(),
            "achievements": Achievement.objects.all(),
        }
    )
    return render(request, "dashboard/progress.html", context)


@login_required
def elite(request):
    context = base_context("elite", request.user)
    context.update(
        {
            "ranking": LeaderboardEntry.objects.all(),
            "challenges": Challenge.objects.all(),
        }
    )
    return render(request, "dashboard/elite.html", context)


@login_required
def exercise_detail(request, slug):
    exercise = get_object_or_404(Exercise.objects.select_related("category"), slug=slug)
    context = base_context("exercise", request.user)
    context["exercise"] = exercise
    return render(request, "dashboard/exercise_detail.html", context)
