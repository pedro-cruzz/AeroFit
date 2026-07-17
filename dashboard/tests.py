import io
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import (
    AthleteProfile,
    Exercise,
    ExerciseCategory,
    LoginAttempt,
    PhysicalAttribute,
    UserActivityLog,
    UserXpEvent,
    WeeklyPlan,
    WorkoutExercise,
    WorkoutRoutine,
    WorkoutSession,
    WorkoutSessionExercise,
)


User = get_user_model()
TRAINER_GROUP_NAME = "Personal"


class AuthenticationSecurityTests(TestCase):
    def setUp(self):
        self.password = "AeroFit!2026"
        self.user = User.objects.create_user(username="athlete", password=self.password)
        self.staff = User.objects.create_user(username="dev", password=self.password, is_staff=True)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard:home"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("dashboard:login"), response["Location"])

    def test_valid_login_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("dashboard:login"),
            {"username": self.user.username, "password": self.password},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("dashboard:home"))

    def test_login_page_links_to_public_signup(self):
        response = self.client.get(reverse("dashboard:login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("dashboard:signup"))
        self.assertContains(response, "Criar conta")

    def test_public_signup_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("dashboard:signup"),
            {
                "username": "new-athlete",
                "first_name": "New",
                "email": "new@example.com",
                "account_type": "student",
                "password1": "AeroFit!2026",
                "password2": "AeroFit!2026",
            },
        )

        user = User.objects.get(username="new-athlete")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("dashboard:home"))
        self.assertEqual(self.client.session.get("_auth_user_id"), str(user.pk))
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.email, "new@example.com")
        self.assertFalse(user.is_staff)

    def test_public_signup_can_create_trainer_profile(self):
        response = self.client.post(
            reverse("dashboard:signup"),
            {
                "username": "coach",
                "first_name": "Coach",
                "email": "coach@example.com",
                "account_type": "trainer",
                "password1": "AeroFit!2026",
                "password2": "AeroFit!2026",
            },
        )

        user = User.objects.get(username="coach")
        self.assertEqual(response.status_code, 302)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.groups.filter(name=TRAINER_GROUP_NAME).exists())

    def test_public_signup_rejects_invalid_data(self):
        response = self.client.post(
            reverse("dashboard:signup"),
            {
                "username": "bad-user",
                "account_type": "student",
                "password1": "short",
                "password2": "different",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="bad-user").exists())
        self.assertContains(response, "Revise os dados para criar sua conta.")

    def test_dev_area_requires_staff_user(self):
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.get(reverse("dashboard:dev_profile"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("dashboard:home"))

    def test_staff_user_can_access_dev_area(self):
        self.client.login(username=self.staff.username, password=self.password)
        response = self.client.get(reverse("dashboard:dev_profile"))

        self.assertEqual(response.status_code, 200)

    def test_staff_user_can_access_separated_dev_pages(self):
        self.client.login(username=self.staff.username, password=self.password)

        for url_name in ["dashboard:dev_users", "dashboard:dev_exercise_catalog", "dashboard:dev_training_flow", "dashboard:dev_development"]:
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 200)

    def test_authenticated_activity_is_logged(self):
        self.client.login(username=self.user.username, password=self.password)
        self.client.get(reverse("dashboard:home"))

        self.assertTrue(UserActivityLog.objects.filter(user=self.user, path=reverse("dashboard:home")).exists())

    def test_dashboard_creates_personal_athlete_profile_and_attributes(self):
        self.client.login(username=self.user.username, password=self.password)

        response = self.client.get(reverse("dashboard:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(AthleteProfile.objects.filter(user=self.user, name=self.user.username).exists())
        self.assertEqual(PhysicalAttribute.objects.filter(user=self.user).count(), 3)

        self.client.logout()
        self.client.login(username=self.staff.username, password=self.password)
        self.client.get(reverse("dashboard:home"))

        self.assertTrue(AthleteProfile.objects.filter(user=self.staff, name=self.staff.username).exists())
        self.assertEqual(PhysicalAttribute.objects.filter(user=self.staff).count(), 3)
        self.assertEqual(AthleteProfile.objects.filter(user__isnull=False).count(), 2)

    def test_repeated_failed_logins_are_locked(self):
        for _ in range(5):
            self.client.post(
                reverse("dashboard:login"),
                {"username": self.user.username, "password": "wrong-password"},
            )

        attempt = LoginAttempt.objects.get()
        self.assertEqual(attempt.attempts, 5)
        self.assertIsNotNone(attempt.locked_until)

        response = self.client.post(
            reverse("dashboard:login"),
            {"username": self.user.username, "password": self.password},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Muitas tentativas falhas")


class StudentWorkoutOwnershipTests(TestCase):
    def setUp(self):
        self.password = "AeroFit!2026"
        self.student = User.objects.create_user(username="student", password=self.password)
        self.other_student = User.objects.create_user(username="other", password=self.password)
        self.category = ExerciseCategory.objects.create(name="Forca", icon="fitness_center")
        self.exercise = Exercise.objects.create(
            name="Supino aluno",
            slug="supino-aluno",
            category=self.category,
            focus="forca",
            primary_muscle="Peitoral",
            default_sets=4,
            default_reps="10",
        )

    def test_student_created_workout_belongs_to_logged_user(self):
        self.client.login(username=self.student.username, password=self.password)
        response = self.client.post(
            reverse("dashboard:workouts"),
            {
                "name": "Planilha A",
                "goal": "forca",
                "exercises": [str(self.exercise.id)],
                f"sets_{self.exercise.id}": "5",
                f"reps_{self.exercise.id}": "8",
                "training_days": ["seg", "qua", "sex"],
            },
        )

        routine = WorkoutRoutine.objects.get(name="Planilha A")
        item = WorkoutExercise.objects.get(routine=routine)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(routine.owner, self.student)
        self.assertEqual(routine.training_days, ["seg", "qua", "sex"])
        self.assertEqual(routine.image_url, WorkoutRoutine.GOAL_COVER_IMAGES["forca"])
        self.assertEqual(item.sets, 5)
        self.assertEqual(item.reps, "8")

    def test_workout_metrics_scale_with_selected_exercises(self):
        second_exercise = Exercise.objects.create(
            name="Remada aluno",
            slug="remada-aluno",
            category=self.category,
            focus="forca",
            primary_muscle="Dorsal",
            default_sets=4,
            default_reps="10",
            rest_seconds=90,
        )
        self.client.login(username=self.student.username, password=self.password)

        self.client.post(
            reverse("dashboard:workouts"),
            {
                "name": "Curto",
                "goal": "forca",
                "exercises": [str(self.exercise.id)],
                f"sets_{self.exercise.id}": "2",
                f"reps_{self.exercise.id}": "8",
            },
        )
        self.client.post(
            reverse("dashboard:workouts"),
            {
                "name": "Longo",
                "goal": "forca",
                "exercises": [str(self.exercise.id), str(second_exercise.id)],
                f"sets_{self.exercise.id}": "5",
                f"reps_{self.exercise.id}": "8",
                f"sets_{second_exercise.id}": "5",
                f"reps_{second_exercise.id}": "10",
            },
        )

        short = WorkoutRoutine.objects.get(name="Curto")
        long = WorkoutRoutine.objects.get(name="Longo")
        self.assertGreater(long.duration_minutes, short.duration_minutes)
        self.assertGreater(long.calories, short.calories)
        self.assertNotEqual(short.duration_minutes, 60)
        self.assertNotEqual(short.calories, 430)

    def test_workout_builder_is_inside_modal(self):
        self.client.login(username=self.student.username, password=self.password)
        lower_exercise = Exercise.objects.create(
            name="Agachamento aluno",
            slug="agachamento-aluno",
            category=self.category,
            focus="forca",
            primary_muscle="Quadriceps",
            default_sets=4,
            default_reps="8",
        )

        response = self.client.get(reverse("dashboard:workouts"))

        self.assertContains(response, 'id="workoutCreateModal"')
        self.assertContains(response, "surface-modal-dialog")
        self.assertContains(response, 'data-bs-target="#workoutCreateModal"')
        self.assertContains(response, f'data-category-filter="{self.category.id}"')
        self.assertContains(response, f'data-category-open="{self.category.id}"')
        self.assertContains(response, "exercise-goal-forca")
        self.assertContains(response, "body-split-title")
        self.assertContains(response, "split-count")
        self.assertContains(response, "Superior")
        self.assertContains(response, "Inferior")
        self.assertContains(response, self.exercise.name)
        self.assertContains(response, lower_exercise.name)
        self.assertNotContains(response, "Sugerido para")

    def test_old_workout_builder_route_opens_new_modal_flow(self):
        self.client.login(username=self.student.username, password=self.password)

        response = self.client.get(reverse("dashboard:workout_builder"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "workoutCreateModal")
        self.assertContains(response, "bootstrap.Modal.getOrCreateInstance(modalElement).show();")
        self.assertContains(response, "body-split-title")
        self.assertNotContains(response, "Cada planilha fica salva apenas para o aluno logado.")

    def test_student_only_sees_own_workouts(self):
        WorkoutRoutine.objects.create(owner=self.student, name="Minha", goal="forca")
        WorkoutRoutine.objects.create(owner=self.other_student, name="Outra", goal="forca")
        self.client.login(username=self.student.username, password=self.password)

        response = self.client.get(reverse("dashboard:workouts"))

        self.assertContains(response, "Minha")
        self.assertNotContains(response, "Outra")

    def test_dashboard_ignores_global_demo_schedule_without_user_workout_days(self):
        WeeklyPlan.objects.create(day="Segunda", detail="Treino fake", is_today=True, order=1)
        WorkoutRoutine.objects.create(owner=self.student, name="Sem dias", goal="forca")
        self.client.login(username=self.student.username, password=self.password)

        response = self.client.get(reverse("dashboard:home"))

        self.assertContains(response, "Nenhuma planilha com dias definidos ainda.")
        self.assertContains(response, "Treino de hoje: Monte sua planilha")
        self.assertNotContains(response, "Treino fake")
        self.assertNotContains(response, "Treino de hoje: Sem dias")

    def test_dashboard_today_workout_accepts_load_input(self):
        all_days = [day for day, _label in WorkoutRoutine.WEEKDAY_CHOICES]
        routine = WorkoutRoutine.objects.create(owner=self.student, name="Minha hoje", goal="forca", training_days=all_days)
        item = WorkoutExercise.objects.create(routine=routine, exercise=self.exercise, sets=4, reps="8", rest_seconds=90)
        self.client.login(username=self.student.username, password=self.password)

        response = self.client.get(reverse("dashboard:home"))
        expected_action = reverse("dashboard:routine_detail", kwargs={"pk": routine.pk})

        self.assertContains(response, "Treino de hoje: Minha hoje")
        self.assertContains(response, f'name="load_{item.id}"')
        self.assertContains(response, f'action="{expected_action}"')
        self.assertContains(response, f'{self.exercise.get_absolute_url()}?return_to=/dashboard/')

    def test_exercise_detail_back_link_uses_return_to_source(self):
        self.client.login(username=self.student.username, password=self.password)
        source_path = reverse("dashboard:routine_detail", kwargs={"pk": WorkoutRoutine.objects.create(owner=self.student, name="Origem", goal="forca").pk})

        response = self.client.get(f"{self.exercise.get_absolute_url()}?return_to={source_path}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{source_path}"')

    def test_exercise_detail_back_link_defaults_to_dashboard(self):
        self.client.login(username=self.student.username, password=self.password)

        response = self.client.get(self.exercise.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{reverse("dashboard:home")}"')

    def test_exercise_detail_embeds_youtube_video_when_configured(self):
        self.exercise.image_url = "https://example.com/supino.jpg"
        self.exercise.video_url = "https://youtu.be/dQw4w9WgXcQ"
        self.exercise.video_credit = "Canal teste"
        self.exercise.save(update_fields=["image_url", "video_url", "video_credit"])
        self.client.login(username=self.student.username, password=self.password)

        response = self.client.get(self.exercise.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "https://example.com/supino.jpg")
        self.assertContains(response, "Referencia visual")
        self.assertContains(response, "Execucao em video")
        self.assertContains(response, "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ")
        self.assertContains(response, "Fonte: Canal teste")

    def test_exercise_detail_handles_missing_media_without_broken_assets(self):
        self.client.login(username=self.student.username, password=self.password)

        response = self.client.get(self.exercise.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Imagem nao cadastrada")
        self.assertContains(response, "Video nao cadastrado")
        self.assertContains(response, "Adicione um link do YouTube")
        self.assertNotContains(response, 'src=""')
        self.assertNotContains(response, "youtube-nocookie.com/embed")

    def test_student_cannot_delete_another_students_workout(self):
        routine = WorkoutRoutine.objects.create(owner=self.other_student, name="Outra", goal="forca")
        self.client.login(username=self.student.username, password=self.password)

        response = self.client.post(reverse("dashboard:delete_routine", kwargs={"pk": routine.pk}))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(WorkoutRoutine.objects.filter(pk=routine.pk).exists())

    def test_student_can_edit_own_workout_prescription(self):
        routine = WorkoutRoutine.objects.create(owner=self.student, name="Minha", goal="forca")
        item = WorkoutExercise.objects.create(routine=routine, exercise=self.exercise, sets=3, reps="10", rest_seconds=60)
        self.client.login(username=self.student.username, password=self.password)

        response = self.client.post(
            reverse("dashboard:edit_routine", kwargs={"pk": routine.pk}),
            {
                "name": "Minha editada",
                "goal": "hipertrofia",
                "training_days": ["ter", "qui"],
                f"sets_{item.id}": "4",
                f"reps_{item.id}": "12",
                f"rest_{item.id}": "75",
            },
        )

        routine.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(routine.name, "Minha editada")
        self.assertEqual(routine.training_days, ["ter", "qui"])
        self.assertEqual(item.sets, 4)
        self.assertEqual(item.reps, "12")
        self.assertEqual(item.rest_seconds, 75)

    def test_completing_workout_awards_xp_to_profile_and_attributes(self):
        run_category = ExerciseCategory.objects.create(name="Endurance", icon="speed", accent="lime")
        run_exercise = Exercise.objects.create(
            name="Corrida teste",
            slug="corrida-teste",
            category=run_category,
            focus="endurance",
            primary_muscle="Sistema cardiovascular",
            default_sets=1,
            default_reps="20 min",
            is_run=True,
        )
        routine = WorkoutRoutine.objects.create(owner=self.student, name="Hibrido", goal="forca")
        strength_item = WorkoutExercise.objects.create(routine=routine, exercise=self.exercise, sets=3, reps="10", rest_seconds=60)
        endurance_item = WorkoutExercise.objects.create(routine=routine, exercise=run_exercise, sets=1, reps="20 min", rest_seconds=0)
        self.client.login(username=self.student.username, password=self.password)

        response = self.client.post(
            reverse("dashboard:routine_detail", kwargs={"pk": routine.pk}),
            {
                f"completed_{strength_item.id}": "on",
                f"load_{strength_item.id}": "80",
                f"rpe_{strength_item.id}": "8",
                f"completed_{endurance_item.id}": "on",
                f"rpe_{endurance_item.id}": "7",
            },
            follow=True,
        )

        self.student.athlete_profile.refresh_from_db()
        strength_attribute = PhysicalAttribute.objects.get(user=self.student, name="Forca")
        endurance_attribute = PhysicalAttribute.objects.get(user=self.student, name="Resistencia")
        xp_event = UserXpEvent.objects.get(user=self.student)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"+{xp_event.total_xp} XP")
        self.assertContains(response, "RPE 8")
        self.assertEqual(WorkoutSession.objects.filter(routine=routine).count(), 1)
        self.assertEqual(WorkoutSessionExercise.objects.get(workout_exercise=strength_item).rpe, 8)
        self.assertGreater(xp_event.total_xp, 0)
        self.assertGreater(xp_event.strength_xp, 0)
        self.assertGreater(xp_event.endurance_xp, 0)
        self.assertEqual(self.student.athlete_profile.total_xp, xp_event.total_xp)
        self.assertGreater(strength_attribute.progress + (strength_attribute.level * 100), 100)
        self.assertGreater(endurance_attribute.progress + (endurance_attribute.level * 100), 100)

    def test_workout_execution_shows_previous_load_placeholder(self):
        routine = WorkoutRoutine.objects.create(owner=self.student, name="Minha", goal="forca")
        item = WorkoutExercise.objects.create(routine=routine, exercise=self.exercise, sets=3, reps="10", rest_seconds=60)
        session = WorkoutSession.objects.create(routine=routine)
        WorkoutSessionExercise.objects.create(
            session=session,
            workout_exercise=item,
            completed=True,
            load_kg="82.5",
            sets_done=3,
            reps_done="10",
            rpe=9,
        )
        self.client.login(username=self.student.username, password=self.password)

        response = self.client.get(reverse("dashboard:routine_detail", kwargs={"pk": routine.pk}))

        self.assertContains(response, "Anterior: 82.5 kg")
        self.assertContains(response, f'name="rpe_{item.id}"')
        self.assertContains(response, f'{self.exercise.get_absolute_url()}?return_to=/treinos/{routine.pk}/')

    def test_progress_page_uses_user_xp_events_instead_of_fixed_mock_metrics(self):
        routine = WorkoutRoutine.objects.create(owner=self.student, name="Minha", goal="forca", duration_minutes=22)
        session = WorkoutSession.objects.create(routine=routine)
        UserXpEvent.objects.create(
            user=self.student,
            session=session,
            total_xp=75,
            strength_xp=50,
            endurance_xp=25,
            base_xp=0,
        )
        self.client.login(username=self.student.username, password=self.password)

        response = self.client.get(reverse("dashboard:progress"))

        self.assertContains(response, "+50 XP")
        self.assertContains(response, "+25 XP")
        self.assertContains(response, "Minha")
        self.assertNotContains(response, "+14%")
        self.assertNotContains(response, "+8%")


class DevTrainingActionTests(TestCase):
    def setUp(self):
        self.password = "AeroFit!2026"
        self.staff = User.objects.create_user(username="dev-training", password=self.password, is_staff=True)
        self.trainer = User.objects.create_user(username="trainer", password=self.password)
        Group.objects.get_or_create(name=TRAINER_GROUP_NAME)[0].user_set.add(self.trainer)
        self.category = ExerciseCategory.objects.create(name="Mobilidade", icon="self_improvement", accent="violet")
        self.exercise = Exercise.objects.create(
            name="Mobilidade base",
            slug="mobilidade-base",
            category=self.category,
            focus="mobilidade",
            primary_muscle="Quadril",
            default_sets=2,
            default_reps="45 s",
        )

    def test_staff_can_edit_training_library_item(self):
        self.client.login(username=self.staff.username, password=self.password)
        response = self.client.post(
            reverse("dashboard:dev_edit_training", kwargs={"pk": self.exercise.pk}),
            {
                "name": "Mobilidade editada",
                "category": self.category.pk,
                "focus": "mobilidade",
                "primary_muscle": "Quadril",
                "secondary_muscles": "",
                "default_sets": "3",
                "default_reps": "60 s",
                "rest_seconds": "30",
                "tutorial_duration": "01:00",
                "image_url": "",
                "anatomy_image_url": "",
                "instructions_text": "Respirar\nAlongar",
            },
        )

        self.exercise.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.exercise.name, "Mobilidade editada")
        self.assertEqual(self.exercise.default_sets, 3)
        self.assertEqual(self.exercise.instructions, ["Respirar", "Alongar"])

    def test_exercise_registration_form_is_inside_modal(self):
        self.client.login(username=self.staff.username, password=self.password)

        response = self.client.get(reverse("dashboard:dev_exercise_catalog"))
        self.assertContains(response, 'id="exerciseCreateModal"')
        self.assertContains(response, "surface-modal-dialog")
        self.assertContains(response, "category-training-card accent-violet")
        self.assertContains(response, "exercise-goal-mobilidade")
        self.assertContains(response, 'class="modal fade"')
        self.assertContains(response, "Salvar exercicio")

    def test_staff_can_delete_unused_training_library_item(self):
        self.client.login(username=self.staff.username, password=self.password)
        response = self.client.post(reverse("dashboard:dev_delete_training", kwargs={"pk": self.exercise.pk}))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Exercise.objects.filter(pk=self.exercise.pk).exists())

    def test_trainer_can_access_exercise_catalog_without_dev_area(self):
        self.client.login(username=self.trainer.username, password=self.password)

        catalog_response = self.client.get(reverse("dashboard:dev_exercise_catalog"))
        dev_response = self.client.get(reverse("dashboard:dev_profile"))

        self.assertEqual(catalog_response.status_code, 200)
        self.assertContains(catalog_response, "Cadastrar exercicio")
        self.assertNotContains(catalog_response, ">Dev</a>")
        self.assertEqual(dev_response.status_code, 302)
        self.assertEqual(dev_response["Location"], reverse("dashboard:home"))

    def test_trainer_can_create_exercise_as_owner(self):
        self.client.login(username=self.trainer.username, password=self.password)
        response = self.client.post(
            reverse("dashboard:dev_exercise_catalog"),
            {
                "name": "Avanco alternado",
                "category": self.category.pk,
                "focus": "forca",
                "primary_muscle": "Quadriceps",
                "secondary_muscles": "Gluteos",
                "default_sets": "3",
                "default_reps": "12",
                "rest_seconds": "60",
                "tutorial_duration": "02:00",
                "image_url": "",
                "anatomy_image_url": "",
                "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "video_credit": "Canal tecnico",
                "instructions_text": "Descer com controle",
            },
        )

        exercise = Exercise.objects.get(name="Avanco alternado")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(exercise.created_by, self.trainer)
        self.assertEqual(exercise.youtube_video_id, "dQw4w9WgXcQ")
        self.assertEqual(exercise.video_credit, "Canal tecnico")

    def test_trainer_cannot_edit_or_delete_another_trainers_exercise(self):
        other_trainer = User.objects.create_user(username="other-trainer", password=self.password)
        Group.objects.get(name=TRAINER_GROUP_NAME).user_set.add(other_trainer)
        owned_exercise = Exercise.objects.create(
            name="Exercicio de outro",
            slug="exercicio-de-outro",
            category=self.category,
            focus="forca",
            primary_muscle="Core",
            created_by=other_trainer,
        )
        self.client.login(username=self.trainer.username, password=self.password)

        edit_response = self.client.get(reverse("dashboard:dev_edit_training", kwargs={"pk": owned_exercise.pk}))
        delete_response = self.client.post(reverse("dashboard:dev_delete_training", kwargs={"pk": owned_exercise.pk}))

        self.assertEqual(edit_response.status_code, 302)
        self.assertEqual(delete_response.status_code, 302)
        self.assertTrue(Exercise.objects.filter(pk=owned_exercise.pk).exists())


class ExerciseCatalogImportCommandTests(TestCase):
    def test_imports_text_catalog_without_creating_duplicates(self):
        source_text = """
1. Hipertrofia
Membros Superiores
Supino Teste com Barra
Sublegenda: Peitoral Maior | Hipertrofia
Series: 4 | Reps: 10

2. HIIT
Membros Inferiores / Geral
Burpee Teste
Sublegenda: Corpo Inteiro | HIIT
Series: 5 | Reps: 30 (em segundos)
"""
        with TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "catalog.txt"
            source.write_text(source_text, encoding="utf-8")
            first_output = io.StringIO()
            second_output = io.StringIO()

            call_command("import_exercise_catalog", str(source), stdout=first_output)
            call_command("import_exercise_catalog", str(source), stdout=second_output)

        self.assertEqual(Exercise.objects.count(), 2)
        self.assertIn("2 criados", first_output.getvalue())
        self.assertIn("0 criados, 2 atualizados", second_output.getvalue())

        supino = Exercise.objects.get(name="Supino Teste com Barra")
        burpee = Exercise.objects.get(name="Burpee Teste")
        self.assertEqual(supino.category.name, "Hipertrofia")
        self.assertEqual(supino.primary_muscle, "Peitoral Maior")
        self.assertEqual(supino.default_sets, 4)
        self.assertEqual(supino.default_reps, "10")
        self.assertEqual(burpee.focus, "hiit")
        self.assertEqual(burpee.secondary_muscles, "Membros Inferiores / Geral")

    def test_structured_catalog_uses_training_goal_categories(self):
        source_text = """
1. Supino Reto
Nome: Supino Reto
Categoria: Forca (Membros Superiores)
Foco: Peito
Musculo Principal: Peitoral Maior
Musculos Secundarios: Triceps, Deltoide Anterior
Series Padrao: 4
Reps Padrao: 8 a 10
Descanso: 90
Exercicio de Corrida: [ ] Nao marcado

2. Agachamento Livre
Nome: Agachamento Livre
Categoria: Base (Membros Inferiores & Core)
Foco: Pernas
Musculo Principal: Quadriceps
Musculos Secundarios: Gluteos, Posteriores, Core
Series Padrao: 4
Reps Padrao: 10
Descanso: 90
Exercicio de Corrida: [ ] Nao marcado

3. Corrida de Tiros (HIIT)
Nome: Corrida de Tiros (HIIT)
Categoria: Resistencia (Cardio / Corrida)
Foco: Cardio
Musculo Principal: Sistema Cardiovascular
Musculos Secundarios: Quadriceps, Isquiotibiais, Panturrilhas
Series Padrao: 1
Reps Padrao: 1
Descanso: 0
Exercicio de Corrida: [X] Marcado
"""
        with TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "catalog.txt"
            source.write_text(source_text, encoding="utf-8")

            call_command("import_exercise_catalog", str(source))

        supino = Exercise.objects.get(name="Supino Reto")
        agachamento = Exercise.objects.get(name="Agachamento Livre")
        tiros = Exercise.objects.get(name="Corrida de Tiros (HIIT)")

        self.assertEqual(supino.category.name, "Hipertrofia")
        self.assertEqual(agachamento.category.name, "Hipertrofia")
        self.assertEqual(tiros.category.name, "HIIT")
        self.assertEqual(supino.focus, "forca")
        self.assertEqual(tiros.focus, "hiit")
        self.assertTrue(tiros.is_run)
        self.assertFalse(ExerciseCategory.objects.filter(name__in=["Superior", "Inferior", "Cardio"]).exists())

    def test_extended_catalog_imports_curated_exercises_without_placeholder_assets(self):
        output = io.StringIO()

        call_command("seed_extended_exercise_catalog", stdout=output)

        supino = Exercise.objects.get(slug="supino-reto")
        corrida = Exercise.objects.get(slug="corrida-leve")

        self.assertEqual(Exercise.objects.count(), 150)
        self.assertIn("150 processados", output.getvalue())
        self.assertEqual(supino.category.name, "Hipertrofia")
        self.assertEqual(corrida.category.name, "Endurance")
        self.assertEqual(supino.image_url, "")
        self.assertEqual(supino.anatomy_image_url, "")
        self.assertTrue(Exercise.objects.filter(name="Barra fixa supinada").exists())
        self.assertTrue(Exercise.objects.filter(name="Voador peitoral").exists())
        self.assertFalse(Exercise.objects.filter(name="Chin-up").exists())

    def test_extended_catalog_renames_legacy_english_exercises_without_duplicates(self):
        category = ExerciseCategory.objects.create(name="Hipertrofia", icon="fitness_center", accent="cyan")
        Exercise.objects.create(
            name="Chin-up",
            slug="chin-up",
            category=category,
            focus="forca",
            primary_muscle="Dorsal",
        )

        call_command("seed_extended_exercise_catalog")

        self.assertEqual(Exercise.objects.count(), 150)
        self.assertFalse(Exercise.objects.filter(slug="chin-up").exists())
        self.assertTrue(Exercise.objects.filter(slug="barra-fixa-supinada", name="Barra fixa supinada").exists())
