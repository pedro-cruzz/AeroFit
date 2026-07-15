from django.contrib import admin

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
    readonly_fields = ("workout_exercise", "completed", "load_kg", "sets_done", "reps_done")
    can_delete = False


@admin.register(WorkoutRoutine)
class WorkoutRoutineAdmin(admin.ModelAdmin):
    list_display = ("name", "goal", "duration_minutes", "calories", "is_template")
    list_filter = ("goal", "is_template")
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


@admin.register(WorkoutSession)
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = ("routine", "completed_at", "notes")
    list_filter = ("routine", "completed_at")
    inlines = [WorkoutSessionExerciseInline]
