from django.contrib import admin

from .models import (
    Achievement,
    AthleteProfile,
    Challenge,
    Exercise,
    ExerciseCategory,
    LeaderboardEntry,
    LoginAttempt,
    PhysicalAttribute,
    ProgressEntry,
    UserActivityLog,
    UserXpEvent,
    WeeklyPlan,
    WorkoutExercise,
    WorkoutRoutine,
    WorkoutSession,
    WorkoutSessionExercise,
)


class WorkoutExerciseInline(admin.TabularInline):
    model = WorkoutExercise
    extra = 1


class WorkoutSessionExerciseInline(admin.TabularInline):
    model = WorkoutSessionExercise
    extra = 0
    readonly_fields = ("workout_exercise", "completed", "load_kg", "sets_done", "reps_done", "rpe")
    can_delete = False


@admin.register(WorkoutRoutine)
class WorkoutRoutineAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "goal", "duration_minutes", "calories", "is_template")
    list_filter = ("goal", "is_template", "owner")
    search_fields = ("name", "description")
    inlines = [WorkoutExerciseInline]


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "focus", "primary_muscle", "default_sets", "default_reps")
    list_filter = ("category", "focus", "is_run")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "primary_muscle", "secondary_muscles")


admin.site.register(AthleteProfile)
admin.site.register(PhysicalAttribute)
admin.site.register(ExerciseCategory)
admin.site.register(WeeklyPlan)
admin.site.register(ProgressEntry)
admin.site.register(Achievement)
admin.site.register(LeaderboardEntry)
admin.site.register(Challenge)


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("identity_hash", "attempts", "locked_until", "last_attempt_at")
    readonly_fields = ("identity_hash", "attempts", "locked_until", "last_attempt_at")
    search_fields = ("identity_hash",)


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ("user", "method", "path", "status_code", "created_at")
    list_filter = ("method", "status_code", "created_at")
    readonly_fields = ("user", "path", "method", "status_code", "ip_hash", "user_agent", "created_at")
    search_fields = ("user__username", "path", "user_agent")


@admin.register(UserXpEvent)
class UserXpEventAdmin(admin.ModelAdmin):
    list_display = ("user", "total_xp", "strength_xp", "endurance_xp", "base_xp", "created_at")
    list_filter = ("created_at",)
    readonly_fields = ("user", "session", "total_xp", "strength_xp", "endurance_xp", "base_xp", "detail", "created_at")
    search_fields = ("user__username", "session__routine__name")


@admin.register(WorkoutSession)
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = ("routine", "completed_at", "notes")
    list_filter = ("routine", "completed_at")
    inlines = [WorkoutSessionExerciseInline]
