from django.core.management.base import BaseCommand

from dashboard.models import Exercise


FREE_EXERCISE_DB_BASE_URL = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises"

FREE_EXERCISE_DB_IMAGES = {
    "supino-reto": "Barbell_Bench_Press_-_Medium_Grip",
    "supino-inclinado-com-barra": "Barbell_Incline_Bench_Press_-_Medium_Grip",
    "supino-inclinado-com-halteres": "Incline_Dumbbell_Press",
    "supino-declinado": "Decline_Barbell_Bench_Press",
    "crucifixo-reto-com-halteres": "Dumbbell_Flyes",
    "crucifixo-inclinado": "Incline_Dumbbell_Flyes",
    "crossover-polia-alta": "Cable_Crossover",
    "crossover-polia-baixa": "Low_Cable_Crossover",
    "voador-peitoral": "Butterfly",
    "flexao-de-bracos": "Pushups",
    "pullover-com-halter": "Bent-Arm_Dumbbell_Pullover",
    "puxada-alta-aberta-pronada": "Wide-Grip_Lat_Pulldown",
    "puxada-alta-fechada": "Close-Grip_Front_Lat_Pulldown",
    "puxada-supinada": "Underhand_Cable_Pulldowns",
    "barra-fixa-pronada": "Pullups",
    "barra-fixa-supinada": "Chin-Up",
    "remada-curvada-com-barra": "Bent_Over_Barbell_Row",
    "remada-curvada-com-halteres": "Bent_Over_Two-Dumbbell_Row",
    "remada-baixa-neutra-triangulo": "Seated_Cable_Rows",
    "remada-unilateral-com-halter": "One-Arm_Dumbbell_Row",
    "remada-cavalinho": "Bent_Over_One-Arm_Long_Bar_Row",
    "remada-maquina-articulada": "Leverage_High_Row",
    "pulldown-na-polia-alta": "Straight-Arm_Pulldown",
    "face-pull": "Face_Pull",
    "encolhimento-com-halteres": "Dumbbell_Shrug",
    "hiperextensao-lombar": "Hyperextensions_Back_Extensions",
    "desenvolvimento-militar": "Barbell_Shoulder_Press",
    "desenvolvimento-com-halteres": "Dumbbell_Shoulder_Press",
    "desenvolvimento-arnold": "Arnold_Dumbbell_Press",
    "elevacao-lateral": "Side_Lateral_Raise",
    "elevacao-frontal": "Front_Dumbbell_Raise",
    "crucifixo-invertido-na-maquina-voador-invertido": "Reverse_Machine_Flyes",
    "crucifixo-invertido-com-halteres": "Seated_Bent-Over_Rear_Delt_Raise",
    "remada-alta": "Standing_Dumbbell_Upright_Row",
    "rotacao-externa-com-elastico": "External_Rotation_with_Band",
    "flexao-pike": "Anti-Gravity_Press",
    "rosca-direta": "Barbell_Curl",
    "rosca-alternada": "Seated_Dumbbell_Curl",
    "rosca-martelo": "Hammer_Curls",
    "rosca-concentrada": "Concentration_Curls",
    "rosca-scott": "Preacher_Curl",
    "rosca-inversa": "Reverse_Barbell_Curl",
    "triceps-pulley": "Triceps_Pushdown",
    "triceps-corda": "Triceps_Pushdown_-_Rope_Attachment",
    "triceps-testa-ou-frances": "Lying_Triceps_Press",
    "triceps-frances-unilateral": "Standing_Dumbbell_Triceps_Extension",
    "mergulho-no-banco": "Bench_Dips",
    "paralelas": "Dips_-_Triceps_Version",
    "agachamento-livre": "Barbell_Full_Squat",
    "agachamento-frontal": "Front_Squat_Clean_Grip",
    "agachamento-goblet": "Goblet_Squat",
    "leg-press-45": "Leg_Press",
    "agachamento-hack": "Barbell_Hack_Squat",
    "cadeira-extensora": "Leg_Extensions",
    "afundo": "Dumbbell_Lunges",
    "avanco-caminhando": "Bodyweight_Walking_Lunge",
    "passada-bulgara": "Split_Squat_with_Dumbbells",
    "subida-no-banco": "Dumbbell_Step_Ups",
    "levantamento-terra": "Barbell_Deadlift",
    "levantamento-terra-romeno": "Romanian_Deadlift",
    "stiff-com-halteres-ou-barra": "Stiff-Legged_Barbell_Deadlift",
    "mesa-flexora": "Lying_Leg_Curls",
    "cadeira-flexora": "Seated_Leg_Curl",
    "elevacao-pelvica-no-banco-hip-thrust": "Barbell_Hip_Thrust",
    "ponte-de-gluteos": "Barbell_Glute_Bridge",
    "cadeira-abdutora": "Thigh_Abductor",
    "cadeira-adutora": "Adductor",
    "gemeos-em-pe-panturrilhas": "Standing_Calf_Raises",
    "gemeos-sentado": "Seated_Calf_Raise",
    "prancha-abdominal": "Plank",
    "abdominal-curto": "Crunches",
    "abdominal-infra": "Flat_Bench_Lying_Leg_Raise",
    "elevacao-de-pernas": "Hanging_Leg_Raise",
    "abdominal-dead-bug": "Dead_Bug",
    "abdominal-russo": "Russian_Twist",
    "escalador": "Mountain_Climbers",
    "abdominal-com-roda": "Ab_Roller",
    "salto-na-caixa": "Front_Box_Jump",
    "agachamento-com-salto": "Freehand_Jump_Squat",
    "swing-com-kettlebell": "One-Arm_Kettlebell_Swings",
    "slam-com-medicine-ball": "One-Arm_Medicine_Ball_Slam",
}


class Command(BaseCommand):
    help = "Preenche imagens dos exercicios usando URLs publicas da Free Exercise DB."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Sobrescreve imagens ja cadastradas.")

    def handle(self, *args, **options):
        force = options["force"]
        updated = 0
        skipped = 0

        for slug, asset_id in FREE_EXERCISE_DB_IMAGES.items():
            exercise = Exercise.objects.filter(slug=slug).first()
            if not exercise:
                skipped += 1
                continue

            if not force and (exercise.image_url or exercise.anatomy_image_url):
                skipped += 1
                continue

            exercise.image_url = f"{FREE_EXERCISE_DB_BASE_URL}/{asset_id}/0.jpg"
            exercise.anatomy_image_url = f"{FREE_EXERCISE_DB_BASE_URL}/{asset_id}/1.jpg"
            exercise.save(update_fields=["image_url", "anatomy_image_url"])
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Midias de imagem atualizadas: {updated}. Ignoradas/sem correspondencia: {skipped}."
            )
        )
