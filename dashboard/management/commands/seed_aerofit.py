from django.core.management.base import BaseCommand
from django.db import transaction

from dashboard.models import (
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


class Command(BaseCommand):
    help = "Cria dados iniciais reais no banco configurado para o AeroFit."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Limpando dados antigos do AeroFit...")
        for model in [
            WeeklyPlan,
            WorkoutSessionExercise,
            WorkoutSession,
            WorkoutExercise,
            WorkoutRoutine,
            Exercise,
            ExerciseCategory,
            PhysicalAttribute,
            ProgressEntry,
            Achievement,
            LeaderboardEntry,
            Challenge,
            AthleteProfile,
        ]:
            model.objects.all().delete()

        profile = AthleteProfile.objects.create(
            name="Alex Rivera",
            level=18,
            streak_days=12,
            total_xp=45820,
            next_level_xp=50000,
            elite_points=12450,
            global_rank=1284,
            image_url="https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=240&q=80",
        )

        PhysicalAttribute.objects.bulk_create(
            [
                PhysicalAttribute(name="Forca", level=8, progress=65, accent="cyan", order=1),
                PhysicalAttribute(name="Resistencia", level=11, progress=85, accent="lime", order=2),
                PhysicalAttribute(name="Base", level=6, progress=45, accent="indigo", order=3),
            ]
        )

        categories = {
            "Hipertrofia": ExerciseCategory.objects.create(name="Hipertrofia", icon="fitness_center", accent="cyan"),
            "Endurance": ExerciseCategory.objects.create(name="Endurance", icon="speed", accent="lime"),
            "Mobilidade": ExerciseCategory.objects.create(name="Mobilidade", icon="self_improvement", accent="violet"),
            "HIIT": ExerciseCategory.objects.create(name="HIIT", icon="timer", accent="red"),
        }

        exercise_data = [
            ("Supino reto", "supino-reto", "Hipertrofia", "forca", "Peitoral maior", "Triceps, deltoide anterior", 4, "10", 90, "02:14", False),
            ("Desenvolvimento militar", "desenvolvimento-militar", "Hipertrofia", "forca", "Deltoide anterior", "Triceps, trapezio", 3, "12", 75, "01:48", False),
            ("Triceps corda", "triceps-corda", "Hipertrofia", "hipertrofia", "Triceps braquial", "Core estabilizador", 3, "15", 60, "01:20", False),
            ("Remada curvada", "remada-curvada", "Hipertrofia", "forca", "Dorsal", "Biceps, romboides", 4, "8", 90, "02:05", False),
            ("Agachamento livre", "agachamento-livre", "Hipertrofia", "forca", "Quadriceps", "Gluteos, posterior", 4, "8", 120, "02:30", False),
            ("Corrida leve", "corrida-leve", "Endurance", "endurance", "Sistema cardiovascular", "Panturrilhas, posterior", 1, "20 min | Pace 5'40\"", 0, "00:45", True),
            ("Corrida 5 km", "corrida-5km", "Endurance", "endurance", "Sistema cardiovascular", "Core, panturrilhas", 1, "5 km progressivo", 0, "00:45", True),
            ("Tiros 10x200m", "tiros-10x200m", "HIIT", "hiit", "Potencia anaerobica", "Gluteos, panturrilhas", 10, "200 m", 45, "00:50", True),
            ("Mobilidade toracica", "mobilidade-toracica", "Mobilidade", "mobilidade", "Coluna toracica", "Ombros, respiracao", 3, "45 s", 30, "01:10", False),
            ("Alongamento de flexores", "alongamento-flexores", "Mobilidade", "mobilidade", "Flexores do quadril", "Gluteos, core", 3, "60 s", 30, "01:05", False),
        ]
        exercises = {}
        default_image = "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?auto=format&fit=crop&w=1200&q=80"
        anatomy_image = "https://images.unsplash.com/photo-1571019613914-85f342c6a11e?auto=format&fit=crop&w=700&q=80"
        for name, slug, category, focus, primary, secondary, sets, reps, rest, duration, is_run in exercise_data:
            exercises[slug] = Exercise.objects.create(
                name=name,
                slug=slug,
                category=categories[category],
                focus=focus,
                primary_muscle=primary,
                secondary_muscles=secondary,
                default_sets=sets,
                default_reps=reps,
                rest_seconds=rest,
                tutorial_duration=duration,
                image_url=default_image,
                anatomy_image_url=anatomy_image,
                is_run=is_run,
                instructions=[
                    "Prepare a postura e estabilize a respiracao antes de iniciar.",
                    "Execute a fase principal com controle e amplitude consistente.",
                    "Finalize mantendo alinhamento tecnico e sem compensacoes.",
                ],
            )

        supino = exercises["supino-reto"]
        supino.instructions = [
            "Mantenha os pes firmes no chao, garantindo estabilidade.",
            "Escapulas retraidas contra o banco durante todo o movimento.",
            "Desca a barra de forma controlada ate a linha media do peito.",
        ]
        supino.save(update_fields=["instructions"])

        routines = [
            WorkoutRoutine.objects.create(
                name="Superior A",
                goal="forca",
                description="Empurrar com foco em forca tecnica.",
                duration_minutes=55,
                calories=420,
                image_url="https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=900&q=80",
                level="Intermediario",
                progress=60,
                is_template=True,
            ),
            WorkoutRoutine.objects.create(
                name="Corrida 5 km",
                goal="endurance",
                description="Rodagem controlada para base aerobica.",
                duration_minutes=28,
                calories=310,
                image_url="https://images.unsplash.com/photo-1502904550040-7534597429ae?auto=format&fit=crop&w=900&q=80",
                level="Base aerobica",
                progress=35,
                is_template=True,
            ),
            WorkoutRoutine.objects.create(
                name="Mobilidade total",
                goal="mobilidade",
                description="Rotina de mobilidade e recuperacao.",
                duration_minutes=35,
                calories=140,
                image_url="https://images.unsplash.com/photo-1506126613408-eca07ce68773?auto=format&fit=crop&w=900&q=80",
                level="Recuperacao",
                progress=100,
                is_template=True,
            ),
        ]

        routine_items = [
            (routines[0], "supino-reto", 1),
            (routines[0], "desenvolvimento-militar", 2),
            (routines[0], "triceps-corda", 3),
            (routines[0], "corrida-leve", 4),
            (routines[1], "corrida-5km", 1),
            (routines[1], "mobilidade-toracica", 2),
            (routines[2], "mobilidade-toracica", 1),
            (routines[2], "alongamento-flexores", 2),
        ]
        WorkoutExercise.objects.bulk_create(
            [
                WorkoutExercise(
                    routine=routine,
                    exercise=exercises[slug],
                    order=order,
                    sets=exercises[slug].default_sets,
                    reps=exercises[slug].default_reps,
                    rest_seconds=exercises[slug].rest_seconds,
                )
                for routine, slug, order in routine_items
            ]
        )

        WeeklyPlan.objects.bulk_create(
            [
                WeeklyPlan(day="Segunda", routine=routines[0], detail="+ Corrida leve", is_today=True, order=1),
                WeeklyPlan(day="Terca", routine=routines[1], detail="5 km", order=2),
                WeeklyPlan(day="Quarta", detail="Pernas completo", order=3),
                WeeklyPlan(day="Quinta", detail="Superior (Puxar)", order=4),
                WeeklyPlan(day="Sexta", detail="Corrida tiros", order=5),
            ]
        )

        ProgressEntry.objects.bulk_create(
            [
                ProgressEntry(name="HIIT Explosivo", date_label="22 OUT", duration_minutes=45, xp=450, tag="Hard core", icon="sprint"),
                ProgressEntry(name="Superior A (Forca)", date_label="21 OUT", duration_minutes=60, xp=320, tag="Strength", icon="fitness_center"),
                ProgressEntry(name="Corrida regenerativa", date_label="19 OUT", duration_minutes=30, xp=180, tag="Light", icon="directions_run"),
            ]
        )
        Achievement.objects.bulk_create(
            [
                Achievement(label="10K Finisher", icon="timer", accent="primary"),
                Achievement(label="Strength Master", icon="fitness_center", accent="cyan"),
                Achievement(label="Early Bird", icon="eco", accent="lime"),
                Achievement(label="Ultra Man", icon="lock", accent="muted", unlocked=False),
            ]
        )
        LeaderboardEntry.objects.bulk_create(
            [
                LeaderboardEntry(rank=1, name="Marcus Thorne", role="Pro Athlete", city="London, UK", points=18290, medal="gold"),
                LeaderboardEntry(rank=2, name="Elena Rodriguez", role="Elite Runner", city="Madrid, ES", points=17440, medal="silver"),
                LeaderboardEntry(rank=3, name="Kenji Sato", role="Powerlifter", city="Tokyo, JP", points=16910, medal="bronze"),
                LeaderboardEntry(rank=64, name=f"Voce ({profile.name})", role="Subindo", city="Top 5%", points=profile.elite_points, is_current_user=True),
            ]
        )
        Challenge.objects.bulk_create(
            [
                Challenge(name="Sprint de 30 km", detail="24,6 km de 30 km completados", progress=82, icon="sprint", days_left=7),
                Challenge(name="Mestre do Volume", detail="450.000 kg movidos de 1M kg", progress=45, icon="fitness_center", days_left=12),
            ]
        )

        self.stdout.write(self.style.SUCCESS("Dados reais criados no banco configurado com sucesso."))
