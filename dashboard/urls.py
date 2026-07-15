from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views


app_name = "dashboard"

urlpatterns = [
    path("", views.SecureLoginView.as_view(), name="login"),
    path("sair/", LogoutView.as_view(next_page="dashboard:login"), name="logout"),
    path("dashboard/", views.dashboard, name="home"),
    path("treinos/", views.workouts, name="workouts"),
    path("treinos/montar/", views.workout_builder, name="workout_builder"),
    path("treinos/<int:pk>/", views.routine_detail, name="routine_detail"),
    path("treinos/<int:pk>/editar/", views.edit_routine, name="edit_routine"),
    path("treinos/<int:pk>/excluir/", views.delete_routine, name="delete_routine"),
    path("treinos/<int:pk>/exercicios/<int:item_pk>/excluir/", views.delete_workout_exercise, name="delete_workout_exercise"),
    path("progresso/", views.progress, name="progress"),
    path("elite/", views.elite, name="elite"),
    path("dev/", views.dev_profile, name="dev_profile"),
    path("dev/usuarios/", views.dev_users, name="dev_users"),
    path("dev/exercicios/", views.dev_training_catalog, name="dev_exercise_catalog"),
    path("dev/treinos/", views.dev_training_catalog, name="dev_training_catalog"),
    path("dev/teste-treinos/", views.dev_training_flow, name="dev_training_flow"),
    path("dev/treinos/<int:pk>/editar/", views.dev_edit_training, name="dev_edit_training"),
    path("dev/treinos/<int:pk>/excluir/", views.dev_delete_training, name="dev_delete_training"),
    path("dev/desenvolvimento/", views.dev_development, name="dev_development"),
    path("exercicios/<slug:slug>/", views.exercise_detail, name="exercise_detail"),
]
