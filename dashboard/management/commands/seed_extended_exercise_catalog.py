from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from dashboard.management.commands.import_exercise_catalog import (
    CATEGORY_META,
    GENERIC_INSTRUCTIONS,
    REST_BY_FOCUS,
    TUTORIAL_BY_FOCUS,
)
from dashboard.models import Exercise, ExerciseCategory


def gym(name, primary, secondary="", sets=3, reps="10", focus="hipertrofia", rest=None):
    return {
        "name": name,
        "category": "hipertrofia",
        "focus": focus,
        "primary_muscle": primary,
        "secondary_muscles": secondary,
        "sets": sets,
        "reps": reps,
        "rest_seconds": rest or REST_BY_FOCUS[focus],
        "is_run": False,
    }


def run(name, reps="30 min", focus="endurance", rest=0):
    return {
        "name": name,
        "category": "hiit" if focus == "hiit" else "endurance",
        "focus": focus,
        "primary_muscle": "Sistema cardiovascular",
        "secondary_muscles": "Quadriceps, Isquiotibiais, Gluteos, Panturrilhas",
        "sets": 1,
        "reps": reps,
        "rest_seconds": rest,
        "is_run": True,
    }


def cardio(name, primary="Sistema cardiovascular", reps="25 min", focus="endurance"):
    return {
        "name": name,
        "category": "endurance",
        "focus": focus,
        "primary_muscle": primary,
        "secondary_muscles": "Membros inferiores, Core",
        "sets": 1,
        "reps": reps,
        "rest_seconds": 0,
        "is_run": False,
    }


def hiit(name, primary="Corpo inteiro", secondary="Sistema cardiovascular", sets=6, reps="30 s", rest=30):
    return {
        "name": name,
        "category": "hiit",
        "focus": "hiit",
        "primary_muscle": primary,
        "secondary_muscles": secondary,
        "sets": sets,
        "reps": reps,
        "rest_seconds": rest,
        "is_run": False,
    }


def mobility(name, primary, secondary="", sets=2, reps="45 s"):
    return {
        "name": name,
        "category": "mobilidade",
        "focus": "mobilidade",
        "primary_muscle": primary,
        "secondary_muscles": secondary,
        "sets": sets,
        "reps": reps,
        "rest_seconds": REST_BY_FOCUS["mobilidade"],
        "is_run": False,
    }


EXERCISE_CATALOG = [
    gym("Supino Reto", "Peitoral maior", "Triceps, Deltoide anterior", 4, "8", "forca", 90),
    gym("Supino inclinado com barra", "Peitoral superior", "Triceps, Deltoide anterior", 4, "8"),
    gym("Supino Inclinado com Halteres", "Peitoral superior", "Triceps, Deltoide anterior", 4, "10"),
    gym("Supino declinado", "Peitoral inferior", "Triceps, Deltoide anterior", 3, "10"),
    gym("Crucifixo reto com halteres", "Peitoral maior", "Deltoide anterior", 3, "12"),
    gym("Crucifixo inclinado", "Peitoral superior", "Deltoide anterior", 3, "12"),
    gym("Crossover polia alta", "Peitoral inferior", "Peitoral maior", 3, "12"),
    gym("Crossover polia baixa", "Peitoral superior", "Peitoral maior", 3, "12"),
    gym("Peck deck", "Peitoral maior", "Deltoide anterior", 3, "12"),
    gym("Flexao de bracos", "Peitoral maior", "Triceps, Core", 3, "12"),
    gym("Pullover com halter", "Dorsal", "Peitoral, Serratil", 3, "12"),
    gym("Puxada Alta Aberta (Pronada)", "Dorsal", "Biceps, Romboides", 4, "10", "forca", 90),
    gym("Puxada alta fechada", "Dorsal", "Biceps, Romboides", 3, "10"),
    gym("Puxada supinada", "Dorsal", "Biceps", 3, "10"),
    gym("Barra fixa pronada", "Dorsal", "Biceps, Core", 4, "8", "forca", 90),
    gym("Chin-up", "Dorsal", "Biceps", 4, "8", "forca", 90),
    gym("Remada curvada com barra", "Dorsal", "Romboides, Biceps, Lombar", 4, "8", "forca", 90),
    gym("Remada Curvada com Halteres", "Dorsal", "Romboides, Biceps", 4, "10"),
    gym("Remada Baixa Neutra (Triangulo)", "Dorsal", "Romboides, Biceps", 4, "10"),
    gym("Remada unilateral com halter", "Dorsal", "Romboides, Biceps", 3, "10"),
    gym("Remada cavalinho", "Dorsal", "Romboides, Trapezio", 4, "10"),
    gym("Remada maquina articulada", "Dorsal", "Romboides, Biceps", 3, "10"),
    gym("Pulldown braco reto", "Dorsal", "Core", 3, "12"),
    gym("Face pull", "Deltoide posterior", "Trapezio, Manguito rotador", 3, "15"),
    gym("Encolhimento com halteres", "Trapezio", "Antebracos", 3, "12"),
    gym("Hiperextensao lombar", "Lombar", "Gluteos, Posteriores", 3, "12"),
    gym("Desenvolvimento militar", "Deltoides", "Triceps, Core", 4, "8", "forca", 90),
    gym("Desenvolvimento com Halteres", "Deltoides", "Triceps", 4, "10"),
    gym("Desenvolvimento Arnold", "Deltoides", "Triceps", 3, "10"),
    gym("Elevacao Lateral", "Deltoide medial", "Trapezio", 3, "12"),
    gym("Elevacao frontal", "Deltoide anterior", "Peitoral superior", 3, "12"),
    gym("Crucifixo Invertido na Maquina (Voador Invertido)", "Deltoide posterior", "Romboides, Trapezio", 3, "12"),
    gym("Crucifixo invertido com halteres", "Deltoide posterior", "Romboides", 3, "12"),
    gym("Remada alta", "Deltoides", "Trapezio", 3, "10"),
    gym("Rotacao externa com elastico", "Manguito rotador", "Deltoide posterior", 2, "15"),
    gym("Pike push-up", "Deltoides", "Triceps, Core", 3, "10"),
    gym("Rosca Direta", "Biceps", "Antebracos", 3, "10"),
    gym("Rosca alternada", "Biceps", "Braquial, Antebracos", 3, "10"),
    gym("Rosca martelo", "Braquial", "Biceps, Antebracos", 3, "10"),
    gym("Rosca concentrada", "Biceps", "Antebracos", 3, "12"),
    gym("Rosca Scott", "Biceps", "Braquial", 3, "10"),
    gym("Rosca inversa", "Antebracos", "Biceps", 3, "12"),
    gym("Triceps Pulley", "Triceps", "Core", 3, "12"),
    gym("Triceps corda", "Triceps", "Core", 3, "12"),
    gym("Triceps Testa (ou Frances)", "Triceps", "Ombros", 3, "10"),
    gym("Triceps frances unilateral", "Triceps", "Ombros", 3, "10"),
    gym("Mergulho no banco", "Triceps", "Peitoral, Ombros", 3, "12"),
    gym("Paralelas", "Triceps", "Peitoral, Deltoide anterior", 4, "8", "forca", 90),
    gym("Agachamento Livre", "Quadriceps", "Gluteos, Posteriores, Core", 4, "8", "forca", 120),
    gym("Agachamento frontal", "Quadriceps", "Gluteos, Core", 4, "8", "forca", 120),
    gym("Agachamento goblet", "Quadriceps", "Gluteos, Core", 3, "12"),
    gym("Leg press 45", "Quadriceps", "Gluteos, Posteriores", 4, "10", "forca", 90),
    gym("Hack squat", "Quadriceps", "Gluteos", 4, "10"),
    gym("Cadeira Extensora", "Quadriceps", "", 3, "12"),
    gym("Afundo", "Quadriceps", "Gluteos, Posteriores", 3, "10"),
    gym("Avanco caminhando", "Quadriceps", "Gluteos, Posteriores", 3, "12"),
    gym("Passada bulgara", "Quadriceps", "Gluteos, Posteriores", 3, "10"),
    gym("Step-up", "Quadriceps", "Gluteos, Panturrilhas", 3, "10"),
    gym("Levantamento terra", "Posteriores", "Gluteos, Lombar, Dorsal", 4, "6", "forca", 150),
    gym("Levantamento terra romeno", "Posteriores", "Gluteos, Lombar", 4, "8", "forca", 120),
    gym("Stiff com Halteres ou Barra", "Posteriores", "Gluteos, Lombar", 4, "10"),
    gym("Mesa flexora", "Posteriores", "Panturrilhas", 3, "12"),
    gym("Cadeira flexora", "Posteriores", "", 3, "12"),
    gym("Hip thrust", "Gluteos", "Posteriores, Core", 4, "10", "forca", 90),
    gym("Glute bridge", "Gluteos", "Posteriores, Core", 3, "12"),
    gym("Cadeira abdutora", "Gluteo medio", "Quadril", 3, "15"),
    gym("Cadeira adutora", "Adutores", "Quadril", 3, "15"),
    gym("Gemeos em Pe (Panturrilhas)", "Panturrilhas", "", 4, "12"),
    gym("Gemeos sentado", "Panturrilhas", "", 4, "12"),
    gym("Prancha Abdominal", "Core", "Ombros, Gluteos", 3, "60 s"),
    gym("Prancha lateral", "Obliquos", "Core, Ombros", 3, "45 s"),
    gym("Abdominal crunch", "Reto abdominal", "Obliquos", 3, "15"),
    gym("Abdominal infra", "Reto abdominal", "Flexores do quadril", 3, "12"),
    gym("Elevacao de pernas", "Reto abdominal", "Flexores do quadril", 3, "12"),
    gym("Dead bug", "Core", "Flexores do quadril", 3, "10"),
    gym("Bird dog", "Core", "Gluteos, Lombar", 3, "10"),
    gym("Russian twist", "Obliquos", "Core", 3, "20"),
    gym("Mountain climber", "Core", "Ombros, Quadriceps", 3, "30 s"),
    gym("Pallof press", "Core anti-rotacao", "Ombros", 3, "12"),
    gym("Ab wheel rollout", "Core", "Dorsal, Ombros", 3, "10"),
    run("Corrida leve", "30 min"),
    run("Corrida de Rodagem Estabilizadora", "40 min"),
    run("Corrida longa", "60 min"),
    run("Corrida tempo", "20 min"),
    run("Corrida progressiva", "35 min"),
    run("Corrida regenerativa", "25 min"),
    run("Corrida em zona 2", "45 min"),
    run("Fartlek", "35 min", "hiit", 60),
    run("Intervalado 400m", "8 x 400 m", "hiit", 90),
    run("Intervalado 800m", "6 x 800 m", "hiit", 120),
    run("Tiros curtos 100m", "10 x 100 m", "hiit", 60),
    run("Tiros 200m", "8 x 200 m", "hiit", 75),
    run("Repeticoes em subida", "8 x 45 s", "hiit", 90),
    run("Ladeira longa", "6 x 2 min", "hiit", 120),
    run("Strides", "8 x 20 s", "hiit", 60),
    run("Corrida em ritmo de prova 5K", "20 min"),
    run("Corrida em ritmo de prova 10K", "25 min"),
    run("Caminhada corrida iniciante", "30 min"),
    run("Corrida de trilha", "45 min"),
    run("Corrida de escada", "12 min", "hiit", 60),
    cardio("Caminhada acelerada", "Sistema cardiovascular", "30 min"),
    cardio("Caminhada inclinada", "Sistema cardiovascular", "25 min"),
    cardio("Esteira inclinada", "Sistema cardiovascular", "25 min"),
    cardio("Bicicleta ergometrica", "Sistema cardiovascular", "30 min"),
    cardio("Bike spinning endurance", "Sistema cardiovascular", "40 min"),
    cardio("Eliptico", "Sistema cardiovascular", "30 min"),
    cardio("Remo indoor continuo", "Sistema cardiovascular", "20 min"),
    cardio("Escada StairMaster", "Sistema cardiovascular", "20 min"),
    cardio("Natacao livre", "Sistema cardiovascular", "30 min"),
    cardio("Pular corda continuo", "Sistema cardiovascular", "12 min"),
    hiit("Corrida de Tiros (HIIT)", "Sistema cardiovascular", "Quadriceps, Isquiotibiais, Panturrilhas", 10, "30 s", 60),
    hiit("Sprint 30/30", "Sistema cardiovascular", "Membros inferiores", 10, "30 s", 30),
    hiit("Tabata corrida", "Sistema cardiovascular", "Membros inferiores", 8, "20 s", 10),
    hiit("EMOM corrida", "Sistema cardiovascular", "Membros inferiores", 10, "1 min", 0),
    hiit("HIIT bike", "Sistema cardiovascular", "Quadriceps, Gluteos", 10, "40 s", 20),
    hiit("HIIT remo", "Sistema cardiovascular", "Dorsal, Pernas, Core", 8, "45 s", 45),
    hiit("HIIT corda", "Sistema cardiovascular", "Panturrilhas, Ombros", 8, "45 s", 30),
    hiit("Burpee", "Corpo inteiro", "Peitoral, Core, Quadriceps", 5, "10"),
    hiit("Thruster", "Corpo inteiro", "Quadriceps, Ombros, Core", 5, "12"),
    hiit("Kettlebell swing", "Posteriores", "Gluteos, Core, Dorsal", 5, "15"),
    hiit("Clean and press", "Corpo inteiro", "Ombros, Pernas, Core", 5, "8"),
    hiit("Snatch com kettlebell", "Corpo inteiro", "Ombros, Gluteos, Core", 5, "8"),
    hiit("Farmer walk", "Core", "Antebracos, Trapezio, Gluteos", 4, "30 m"),
    hiit("Battle rope waves", "Ombros", "Core, Bracos", 6, "30 s"),
    hiit("Wall ball", "Corpo inteiro", "Quadriceps, Ombros, Core", 5, "15"),
    hiit("Box jump", "Quadriceps", "Gluteos, Panturrilhas", 5, "8"),
    hiit("Jump squat", "Quadriceps", "Gluteos, Panturrilhas", 5, "12"),
    hiit("Skater jump", "Gluteo medio", "Quadriceps, Core", 5, "30 s"),
    hiit("Medicine ball slam", "Core", "Ombros, Dorsal", 5, "12"),
    hiit("Bear crawl", "Core", "Ombros, Quadriceps", 4, "20 m"),
    mobility("Alongamento flexor do quadril ajoelhado", "Flexores do quadril", "Quadriceps"),
    mobility("Alongamento 90 graus de dorsal", "Dorsal", "Ombros"),
    mobility("Alongamento peitoral na porta", "Peitoral", "Deltoide anterior"),
    mobility("Rotacao toracica em quatro apoios", "Coluna toracica", "Ombros"),
    mobility("Cat cow", "Coluna", "Core"),
    mobility("Child pose com alcance lateral", "Dorsal", "Coluna toracica"),
    mobility("World's greatest stretch", "Quadril", "Coluna toracica, Posteriores"),
    mobility("Mobilidade de tornozelo na parede", "Tornozelo", "Panturrilhas"),
    mobility("Alongamento de panturrilha", "Panturrilhas", "Tornozelo"),
    mobility("Alongamento posterior de coxa", "Posteriores", "Gluteos"),
    mobility("Alongamento de quadriceps", "Quadriceps", "Flexores do quadril"),
    mobility("Pigeon stretch", "Gluteos", "Quadril"),
    mobility("Figure four stretch", "Gluteos", "Piriforme"),
    mobility("Cossack squat mobility", "Adutores", "Quadril, Tornozelos"),
    mobility("Agachamento profundo sustentado", "Quadril", "Tornozelos, Adutores"),
    mobility("Shoulder dislocates com bastao", "Ombros", "Peitoral"),
    mobility("Wall angels", "Ombros", "Coluna toracica"),
    mobility("Mobilidade de punho", "Punhos", "Antebracos"),
    mobility("Mobilidade cervical controlada", "Cervical", "Trapezio"),
    mobility("Downward dog", "Posteriores", "Panturrilhas, Ombros"),
]


class Command(BaseCommand):
    help = "Cadastra uma biblioteca ampla de exercicios pesquisados e organizados para o AeroFit."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra quantos exercicios seriam processados sem gravar no banco.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        categories = self._ensure_categories()

        if options["dry_run"]:
            self.stdout.write(f"{len(EXERCISE_CATALOG)} exercicios encontrados. Nada foi gravado.")
            return

        created = 0
        updated = 0

        for item in EXERCISE_CATALOG:
            slug = self._resolve_slug(item["name"])
            exercise = Exercise.objects.filter(slug=slug).first()
            defaults = {
                "name": exercise.name if exercise else item["name"],
                "category": categories[item["category"]],
                "focus": item["focus"],
                "primary_muscle": item["primary_muscle"],
                "secondary_muscles": item["secondary_muscles"],
                "default_sets": item["sets"],
                "default_reps": item["reps"],
                "rest_seconds": item["rest_seconds"],
                "tutorial_duration": TUTORIAL_BY_FOCUS[item["focus"]],
                "instructions": GENERIC_INSTRUCTIONS[item["focus"]],
                "is_run": item["is_run"],
            }

            if exercise:
                for field, value in defaults.items():
                    setattr(exercise, field, value)
                exercise.save()
                updated += 1
                continue

            Exercise.objects.create(slug=slug, **defaults)
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Catalogo estendido importado: {created} criados, {updated} atualizados, "
                f"{len(EXERCISE_CATALOG)} processados."
            )
        )

    def _ensure_categories(self):
        categories = {}
        for key, data in CATEGORY_META.items():
            category, _created = ExerciseCategory.objects.get_or_create(
                name=data["name"],
                defaults={"icon": data["icon"], "accent": data["accent"]},
            )
            categories[key] = category
        return categories

    def _resolve_slug(self, name):
        base_slug = slugify(name)[:45] or "exercicio"
        same_exercise = Exercise.objects.filter(slug=base_slug).first()
        if same_exercise:
            return same_exercise.slug

        candidate = base_slug
        suffix = 2
        while Exercise.objects.filter(slug=candidate).exists():
            candidate = f"{base_slug[:45]}-{suffix}"
            suffix += 1
        return candidate
