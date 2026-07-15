import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from dashboard.models import Exercise, ExerciseCategory


CATEGORY_META = {
    "hipertrofia": {"name": "Hipertrofia", "icon": "fitness_center", "accent": "cyan"},
    "hiit": {"name": "HIIT", "icon": "timer", "accent": "red"},
    "endurance": {"name": "Endurance", "icon": "speed", "accent": "lime"},
    "mobilidade": {"name": "Mobilidade", "icon": "self_improvement", "accent": "violet"},
}

REST_BY_FOCUS = {
    "hipertrofia": 75,
    "hiit": 45,
    "endurance": 0,
    "mobilidade": 30,
}

TUTORIAL_BY_FOCUS = {
    "hipertrofia": "02:00",
    "hiit": "01:00",
    "endurance": "00:45",
    "mobilidade": "01:10",
}

GENERIC_INSTRUCTIONS = {
    "hipertrofia": [
        "Ajuste a carga para manter tecnica consistente em todas as series.",
        "Controle a fase negativa e evite compensacoes no fim da amplitude.",
        "Finalize a serie com uma ou duas repeticoes em reserva quando o treino pedir volume.",
    ],
    "hiit": [
        "Prepare o espaco e aqueça antes de iniciar o bloco intenso.",
        "Execute cada repeticao com potencia sem perder o alinhamento tecnico.",
        "Use o descanso para recuperar a respiracao e manter a qualidade do proximo bloco.",
    ],
    "endurance": [
        "Comece em ritmo controlado e preserve a respiracao estavel.",
        "Mantenha cadencia e postura constantes durante o bloco principal.",
        "Reduza gradualmente a intensidade nos minutos finais.",
    ],
    "mobilidade": [
        "Entre na posicao sem dor e mantenha respiracao nasal sempre que possivel.",
        "Avance a amplitude aos poucos, sem movimentos bruscos.",
        "Saia da posicao com controle antes de trocar de lado ou repetir.",
    ],
}

RUN_KEYWORDS = (
    "corrida",
    "esteira",
    "bicicleta",
    "ergometrica",
    "eliptico",
    "transport",
    "stairmaster",
    "escada",
    "pular corda",
    "rowing",
    "natacao",
)


class Command(BaseCommand):
    help = "Importa uma lista textual de exercicios para a biblioteca do AeroFit sem duplicar registros."

    def add_arguments(self, parser):
        parser.add_argument("source", type=str, help="Caminho do arquivo .txt com os exercicios.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra o que seria importado sem gravar no banco.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        source = Path(options["source"])
        if not source.exists():
            raise CommandError(f"Arquivo nao encontrado: {source}")

        parsed_exercises = self._parse_source(source)
        if not parsed_exercises:
            raise CommandError("Nenhum exercicio foi encontrado no arquivo informado.")

        if options["dry_run"]:
            self.stdout.write(f"{len(parsed_exercises)} exercicios encontrados. Nada foi gravado.")
            return

        categories = self._ensure_categories()
        created = 0
        updated = 0

        for item in parsed_exercises:
            category = categories[item["category"]]
            slug = self._resolve_slug(item["name"], category)
            defaults = {
                "slug": slug,
                "focus": item["focus"],
                "primary_muscle": item["primary_muscle"],
                "secondary_muscles": item["section"],
                "default_sets": item["sets"],
                "default_reps": item["reps"],
                "rest_seconds": REST_BY_FOCUS[item["focus"]],
                "tutorial_duration": TUTORIAL_BY_FOCUS[item["focus"]],
                "is_run": self._is_run(item["name"], item["focus"]),
                "instructions": GENERIC_INSTRUCTIONS[item["focus"]],
            }
            _exercise, was_created = Exercise.objects.update_or_create(
                name=item["name"],
                category=category,
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Catalogo importado: {created} criados, {updated} atualizados, {len(parsed_exercises)} processados."
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

    def _parse_source(self, source):
        text = source.read_text(encoding="utf-8-sig")
        current_category = None
        current_section = ""
        pending_name = ""
        pending_primary = ""
        parsed = []

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line.lower().startswith("sublegenda:"):
                pending_primary = self._parse_primary_muscle(line)
                continue

            if line.lower().startswith(("series:", "séries:")):
                if not current_category or not pending_name:
                    continue
                sets, reps = self._parse_sets_reps(line)
                parsed.append(
                    {
                        "name": pending_name,
                        "category": current_category,
                        "focus": current_category,
                        "section": current_section,
                        "primary_muscle": pending_primary or CATEGORY_META[current_category]["name"],
                        "sets": sets,
                        "reps": reps,
                    }
                )
                pending_name = ""
                pending_primary = ""
                continue

            detected_category = self._detect_category(line)
            if detected_category:
                current_category = detected_category
                pending_name = ""
                continue

            if self._is_section(line):
                current_section = line
                pending_name = ""
                continue

            if current_category and not self._looks_like_noise(line):
                pending_name = line

        return parsed

    def _detect_category(self, line):
        normalized = self._normalize(line)
        for key in CATEGORY_META:
            if key in normalized:
                return key
        return None

    def _is_section(self, line):
        normalized = self._normalize(line)
        return normalized.startswith("membros ") or normalized in {"core", "geral"}

    def _looks_like_noise(self, line):
        normalized = self._normalize(line)
        return normalized.startswith("aqui esta ") or normalized.startswith("eles estao ")

    def _parse_primary_muscle(self, line):
        value = re.sub(r"^sublegenda:\s*", "", line, flags=re.IGNORECASE).strip()
        return value.split("|", 1)[0].strip()

    def _parse_sets_reps(self, line):
        sets_match = re.search(r"s[ée]ries:\s*(\d+)", line, flags=re.IGNORECASE)
        reps_match = re.search(r"reps:\s*(.+)$", line, flags=re.IGNORECASE)
        sets = int(sets_match.group(1)) if sets_match else 3
        reps = reps_match.group(1).strip() if reps_match else "10"
        return sets, reps

    def _resolve_slug(self, name, category):
        base_slug = slugify(name)[:45] or "exercicio"
        same_exercise = Exercise.objects.filter(name=name, category=category).first()
        if same_exercise:
            return same_exercise.slug

        if not Exercise.objects.filter(slug=base_slug).exists():
            return base_slug

        category_slug = slugify(category.name)
        candidate = f"{base_slug}-{category_slug}"[:50]
        suffix = 2
        while Exercise.objects.filter(slug=candidate).exists():
            candidate = f"{base_slug[:44]}-{category_slug[:4]}-{suffix}"
            suffix += 1
        return candidate

    def _is_run(self, name, focus):
        normalized_name = self._normalize(name)
        return focus == "endurance" or any(keyword in normalized_name for keyword in RUN_KEYWORDS)

    def _normalize(self, value):
        replacements = str.maketrans(
            {
                "á": "a",
                "à": "a",
                "ã": "a",
                "â": "a",
                "é": "e",
                "ê": "e",
                "í": "i",
                "ó": "o",
                "õ": "o",
                "ô": "o",
                "ú": "u",
                "ç": "c",
            }
        )
        return value.lower().translate(replacements)
