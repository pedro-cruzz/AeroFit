from django.conf import settings
from django.db import models
from django.urls import reverse


class AthleteProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="athlete_profile",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120)
    level = models.PositiveIntegerField(default=1)
    streak_days = models.PositiveIntegerField(default=0)
    total_xp = models.PositiveIntegerField(default=0)
    next_level_xp = models.PositiveIntegerField(default=1000)
    elite_points = models.PositiveIntegerField(default=0)
    global_rank = models.PositiveIntegerField(default=0)
    image_url = models.URLField(blank=True)

    def __str__(self):
        return self.name

    @property
    def xp_progress(self):
        if not self.next_level_xp:
            return 0
        return min(round((self.total_xp / self.next_level_xp) * 100), 100)


class PhysicalAttribute(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="physical_attributes",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=80)
    level = models.PositiveIntegerField(default=1)
    progress = models.PositiveIntegerField(default=0)
    accent = models.CharField(max_length=20, default="indigo")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class ExerciseCategory(models.Model):
    name = models.CharField(max_length=80, unique=True)
    icon = models.CharField(max_length=60, default="fitness_center")
    accent = models.CharField(max_length=20, default="cyan")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Exercise(models.Model):
    FOCUS_CHOICES = [
        ("forca", "Forca"),
        ("hipertrofia", "Hipertrofia"),
        ("endurance", "Endurance"),
        ("mobilidade", "Mobilidade"),
        ("hiit", "HIIT"),
    ]

    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(ExerciseCategory, on_delete=models.PROTECT, related_name="exercises")
    focus = models.CharField(max_length=20, choices=FOCUS_CHOICES)
    primary_muscle = models.CharField(max_length=120)
    secondary_muscles = models.CharField(max_length=180, blank=True)
    default_sets = models.PositiveIntegerField(default=3)
    default_reps = models.CharField(max_length=40, default="10")
    rest_seconds = models.PositiveIntegerField(default=60)
    tutorial_duration = models.CharField(max_length=10, default="02:00")
    image_url = models.URLField(blank=True)
    anatomy_image_url = models.URLField(blank=True)
    instructions = models.JSONField(default=list, blank=True)
    is_run = models.BooleanField(default=False)

    class Meta:
        ordering = ["category__name", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("dashboard:exercise_detail", kwargs={"slug": self.slug})


class WorkoutRoutine(models.Model):
    GOAL_CHOICES = Exercise.FOCUS_CHOICES
    WEEKDAY_CHOICES = [
        ("seg", "Segunda"),
        ("ter", "Terca"),
        ("qua", "Quarta"),
        ("qui", "Quinta"),
        ("sex", "Sexta"),
        ("sab", "Sabado"),
        ("dom", "Domingo"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workout_routines",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120)
    goal = models.CharField(max_length=20, choices=GOAL_CHOICES)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=45)
    calories = models.PositiveIntegerField(default=300)
    image_url = models.URLField(blank=True)
    level = models.CharField(max_length=60, default="Intermediario")
    progress = models.PositiveIntegerField(default=0)
    is_template = models.BooleanField(default=False)
    training_days = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "name"]

    def __str__(self):
        return self.name

    @property
    def type(self):
        return self.get_goal_display()

    @property
    def day_labels(self):
        labels = dict(self.WEEKDAY_CHOICES)
        return [labels.get(day, day) for day in self.training_days]

    @property
    def days_summary(self):
        labels = self.day_labels
        if not labels:
            return "Sem dias definidos"
        return ", ".join(labels)


class WorkoutExercise(models.Model):
    routine = models.ForeignKey(WorkoutRoutine, on_delete=models.CASCADE, related_name="items")
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT, related_name="routine_items")
    order = models.PositiveIntegerField(default=1)
    sets = models.PositiveIntegerField(default=3)
    reps = models.CharField(max_length=40, default="10")
    rest_seconds = models.PositiveIntegerField(default=60)
    notes = models.CharField(max_length=180, blank=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.routine} - {self.exercise}"

    @property
    def meta(self):
        if self.exercise.is_run:
            return self.reps
        return f"{self.sets}x{self.reps}"


class WorkoutSession(models.Model):
    routine = models.ForeignKey(WorkoutRoutine, on_delete=models.CASCADE, related_name="sessions")
    completed_at = models.DateTimeField(auto_now_add=True)
    notes = models.CharField(max_length=220, blank=True)

    class Meta:
        ordering = ["-completed_at"]

    def __str__(self):
        return f"{self.routine} em {self.completed_at:%d/%m/%Y %H:%M}"


class WorkoutSessionExercise(models.Model):
    session = models.ForeignKey(WorkoutSession, on_delete=models.CASCADE, related_name="exercise_logs")
    workout_exercise = models.ForeignKey(WorkoutExercise, on_delete=models.CASCADE, related_name="session_logs")
    completed = models.BooleanField(default=True)
    load_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    sets_done = models.PositiveIntegerField(default=0)
    reps_done = models.CharField(max_length=40, blank=True)
    rpe = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["workout_exercise__order", "id"]

    def __str__(self):
        return f"{self.session} - {self.workout_exercise.exercise}"


class UserXpEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="xp_events")
    session = models.OneToOneField(
        WorkoutSession,
        on_delete=models.CASCADE,
        related_name="xp_event",
        null=True,
        blank=True,
    )
    total_xp = models.PositiveIntegerField(default=0)
    strength_xp = models.PositiveIntegerField(default=0)
    endurance_xp = models.PositiveIntegerField(default=0)
    base_xp = models.PositiveIntegerField(default=0)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} +{self.total_xp} XP"


class WeeklyPlan(models.Model):
    day = models.CharField(max_length=20)
    routine = models.ForeignKey(WorkoutRoutine, on_delete=models.SET_NULL, null=True, blank=True)
    detail = models.CharField(max_length=120, blank=True)
    is_today = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.day


class ProgressEntry(models.Model):
    name = models.CharField(max_length=120)
    date_label = models.CharField(max_length=30)
    duration_minutes = models.PositiveIntegerField(default=30)
    xp = models.PositiveIntegerField(default=0)
    tag = models.CharField(max_length=40)
    icon = models.CharField(max_length=60, default="fitness_center")

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return self.name


class Achievement(models.Model):
    label = models.CharField(max_length=80)
    icon = models.CharField(max_length=60)
    accent = models.CharField(max_length=20, default="primary")
    unlocked = models.BooleanField(default=True)

    def __str__(self):
        return self.label


class LeaderboardEntry(models.Model):
    rank = models.PositiveIntegerField()
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=80)
    city = models.CharField(max_length=80)
    points = models.PositiveIntegerField()
    medal = models.CharField(max_length=20, blank=True)
    is_current_user = models.BooleanField(default=False)

    class Meta:
        ordering = ["rank"]

    def __str__(self):
        return f"#{self.rank} {self.name}"


class LoginAttempt(models.Model):
    identity_hash = models.CharField(max_length=64, unique=True)
    attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_attempt_at"]

    def __str__(self):
        return f"{self.identity_hash[:12]} ({self.attempts})"


class UserActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activity_logs")
    path = models.CharField(max_length=220)
    method = models.CharField(max_length=10)
    status_code = models.PositiveIntegerField()
    ip_hash = models.CharField(max_length=64, blank=True)
    user_agent = models.CharField(max_length=220, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.user} {self.method} {self.path}"


class Challenge(models.Model):
    name = models.CharField(max_length=120)
    detail = models.CharField(max_length=160)
    progress = models.PositiveIntegerField(default=0)
    icon = models.CharField(max_length=60, default="fitness_center")
    days_left = models.PositiveIntegerField(default=7)

    def __str__(self):
        return self.name
