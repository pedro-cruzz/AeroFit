from django.urls import path

from . import views


app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard, name="home"),
    path("treinos/", views.workouts, name="workouts"),
    path("treinos/montar/", views.workout_builder, name="workout_builder"),
    path("treinos/<int:pk>/", views.routine_detail, name="routine_detail"),
    path("treinos/<int:pk>/excluir/", views.delete_routine, name="delete_routine"),
    path("treinos/<int:pk>/exercicios/<int:item_pk>/excluir/", views.delete_workout_exercise, name="delete_workout_exercise"),
    path("progresso/", views.progress, name="progress"),
    path("elite/", views.elite, name="elite"),
    path("dev/", views.dev_profile, name="dev_profile"),
    path("exercicios/<slug:slug>/", views.exercise_detail, name="exercise_detail"),
]
