import re

from django.core.management.base import BaseCommand, CommandError

from dashboard.models import Exercise


BAD_TITLE_TERMS = (
    "playlist",
    "compilado",
    "treino completo",
    "aula completa",
    "podcast",
    "shorts",
)
GOOD_TITLE_TERMS = (
    "execucao",
    "execução",
    "correta",
    "como fazer",
    "tecnica",
    "técnica",
    "exercicio",
    "exercício",
)


def normalize_text(value):
    value = value.lower()
    replacements = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    return re.sub(r"[^a-z0-9 ]+", " ", value)


def build_search_query(exercise):
    name = exercise.name
    if exercise.focus == "mobilidade":
        return f"{name} como fazer mobilidade alongamento"
    if exercise.is_run or exercise.focus == "endurance":
        return f"{name} tecnica correta corrida exercicio"
    if exercise.focus == "hiit":
        return f"{name} como fazer exercicio execucao correta"
    return f"{name} execucao correta exercicio musculacao"


def score_video(exercise, entry):
    title = entry.get("title") or ""
    normalized_title = normalize_text(title)
    normalized_name = normalize_text(exercise.name)
    duration = entry.get("duration") or 0
    score = 0

    for word in normalized_name.split():
        if len(word) > 2 and word in normalized_title:
            score += 4

    for term in GOOD_TITLE_TERMS:
        if normalize_text(term) in normalized_title:
            score += 3

    for term in BAD_TITLE_TERMS:
        if normalize_text(term) in normalized_title:
            score -= 8

    if 20 <= duration <= 720:
        score += 5
    elif duration > 1800:
        score -= 8

    if "shorts" in (entry.get("url") or ""):
        score -= 10

    return score


class Command(BaseCommand):
    help = "Pesquisa e cadastra videos do YouTube para exercicios sem video."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Sobrescreve videos ja cadastrados.")
        parser.add_argument("--dry-run", action="store_true", help="Mostra os videos encontrados sem salvar.")
        parser.add_argument("--limit", type=int, default=0, help="Limita a quantidade de exercicios processados.")
        parser.add_argument("--max-results", type=int, default=3, help="Resultados avaliados por exercicio.")

    def handle(self, *args, **options):
        try:
            import yt_dlp
        except ImportError as exc:
            raise CommandError("Instale yt-dlp no ambiente antes de rodar este comando.") from exc

        queryset = Exercise.objects.order_by("category__name", "name")
        if not options["force"]:
            queryset = queryset.filter(video_url="")
        if options["limit"]:
            queryset = queryset[: options["limit"]]

        updated = 0
        skipped = 0
        searched = 0
        max_results = max(1, options["max_results"])
        ydl_options = {
            "extract_flat": "in_playlist",
            "quiet": True,
            "skip_download": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            for exercise in queryset:
                searched += 1
                query = build_search_query(exercise)
                try:
                    info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
                except Exception as exc:
                    skipped += 1
                    self.stderr.write(f"Falha ao pesquisar {exercise.slug}: {exc}")
                    continue

                entries = [entry for entry in info.get("entries", []) if entry and entry.get("id")]
                if not entries:
                    skipped += 1
                    self.stdout.write(f"Sem video: {exercise.name}")
                    continue

                selected = max(entries, key=lambda entry: score_video(exercise, entry))
                video_url = f"https://www.youtube.com/watch?v={selected['id']}"
                credit = selected.get("uploader") or selected.get("channel") or "YouTube"

                self.stdout.write(
                    f"{exercise.slug}: {selected.get('title')} | {credit} | {video_url}"
                )
                if options["dry_run"]:
                    continue

                exercise.video_url = video_url
                exercise.video_credit = credit[:160]
                exercise.save(update_fields=["video_url", "video_credit"])
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Pesquisados: {searched}. Videos atualizados: {updated}. Ignorados: {skipped}."
            )
        )
