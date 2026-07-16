from html import escape
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from dashboard.management.commands.seed_extended_exercise_catalog import EXERCISE_CATALOG


BASE_DIR = Path(__file__).resolve().parents[3] / "static" / "dashboard" / "exercises"

ACCENT_BY_FOCUS = {
    "forca": "#38bdf8",
    "hipertrofia": "#38bdf8",
    "endurance": "#a3e635",
    "hiit": "#ef4444",
    "mobilidade": "#a78bfa",
}

LABEL_BY_FOCUS = {
    "forca": "STRENGTH",
    "hipertrofia": "HYPERTROPHY",
    "endurance": "ENDURANCE",
    "hiit": "HIIT",
    "mobilidade": "MOBILITY",
}


class Command(BaseCommand):
    help = "Gera SVGs estaticos para os exercicios do catalogo amplo."

    def handle(self, *args, **options):
        tutorial_dir = BASE_DIR / "tutorial"
        anatomy_dir = BASE_DIR / "anatomy"
        tutorial_dir.mkdir(parents=True, exist_ok=True)
        anatomy_dir.mkdir(parents=True, exist_ok=True)

        generated = 0
        for item in EXERCISE_CATALOG:
            slug = slugify(item["name"])[:70] or "exercicio"
            accent = ACCENT_BY_FOCUS[item["focus"]]
            label = LABEL_BY_FOCUS[item["focus"]]
            tutorial_svg = self._tutorial_svg(item, accent, label)
            anatomy_svg = self._anatomy_svg(item, accent, label)

            (tutorial_dir / f"{slug}.svg").write_text(tutorial_svg, encoding="utf-8")
            (anatomy_dir / f"{slug}.svg").write_text(anatomy_svg, encoding="utf-8")
            generated += 2

        self.stdout.write(self.style.SUCCESS(f"{generated} assets SVG gerados em {BASE_DIR}."))

    def _tutorial_svg(self, item, accent, label):
        name = escape(item["name"])
        primary = escape(item["primary_muscle"])
        secondary = escape(item["secondary_muscles"] or "Controle tecnico")
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720" role="img" aria-label="{name}">
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#0e0e0e"/>
      <stop offset="1" stop-color="#201f1f"/>
    </linearGradient>
    <radialGradient id="signal" cx="70%" cy="38%" r="55%">
      <stop offset="0" stop-color="{accent}" stop-opacity="0.28"/>
      <stop offset="1" stop-color="{accent}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1280" height="720" fill="url(#bg)"/>
  <rect width="1280" height="720" fill="url(#signal)"/>
  <g opacity="0.22" stroke="#e5e2e1" stroke-width="1">
    <path d="M92 118H1188M92 242H1188M92 366H1188M92 490H1188M92 614H1188"/>
    <path d="M160 72V648M320 72V648M480 72V648M640 72V648M800 72V648M960 72V648M1120 72V648"/>
  </g>
  <g transform="translate(780 112)" stroke="{accent}" stroke-linecap="round" stroke-linejoin="round" fill="none">
    <circle cx="178" cy="72" r="42" stroke-width="12" opacity="0.95"/>
    <path d="M178 118v156M96 172c54 36 110 36 164 0M128 324l50-50 52 50M128 474l50-150 52 150" stroke-width="16"/>
    <path d="M56 288h244M48 474h260" stroke-width="20" opacity="0.42"/>
    <rect x="16" y="474" width="332" height="30" rx="6" stroke-width="8" opacity="0.72"/>
  </g>
  <g transform="translate(72 78)">
    <rect x="0" y="0" width="152" height="34" rx="4" fill="{accent}" fill-opacity="0.16" stroke="{accent}" stroke-opacity="0.55"/>
    <text x="18" y="23" fill="{accent}" font-family="JetBrains Mono, Consolas, monospace" font-size="14" font-weight="700" letter-spacing="2">{label}</text>
    <text x="0" y="148" fill="#f4f4f5" font-family="Inter, Arial, sans-serif" font-size="62" font-weight="800">{name}</text>
    <text x="0" y="206" fill="#c8c6ca" font-family="Inter, Arial, sans-serif" font-size="28" font-weight="500">{primary}</text>
    <text x="0" y="252" fill="#919095" font-family="Inter, Arial, sans-serif" font-size="20">{secondary}</text>
  </g>
  <g transform="translate(72 590)">
    <text fill="#919095" font-family="JetBrains Mono, Consolas, monospace" font-size="15" letter-spacing="2">AEROFIT PRECISION / EXERCISE GUIDE</text>
    <rect x="0" y="28" width="480" height="4" fill="#ffffff" opacity="0.08"/>
    <rect x="0" y="28" width="220" height="4" fill="{accent}"/>
  </g>
</svg>
"""

    def _anatomy_svg(self, item, accent, label):
        name = escape(item["name"])
        primary = escape(item["primary_muscle"])
        secondary = escape(item["secondary_muscles"] or "Estabilizadores")
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="900" viewBox="0 0 900 900" role="img" aria-label="Diagrama muscular {name}">
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#0e0e0e"/>
      <stop offset="1" stop-color="#201f1f"/>
    </linearGradient>
  </defs>
  <rect width="900" height="900" fill="url(#bg)"/>
  <g opacity="0.16" stroke="#e5e2e1" stroke-width="1">
    <path d="M90 150H810M90 300H810M90 450H810M90 600H810M90 750H810"/>
    <path d="M150 90V810M300 90V810M450 90V810M600 90V810M750 90V810"/>
  </g>
  <g transform="translate(316 116)" fill="none" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="134" cy="66" r="50" stroke="#e5e2e1" stroke-width="10" opacity="0.86"/>
    <path d="M134 122v124" stroke="#e5e2e1" stroke-width="18" opacity="0.76"/>
    <path d="M58 170c42 32 110 32 152 0" stroke="{accent}" stroke-width="18"/>
    <path d="M82 252c32 54 72 54 104 0" stroke="{accent}" stroke-width="18" opacity="0.72"/>
    <path d="M44 320l90-74 90 74" stroke="#e5e2e1" stroke-width="15" opacity="0.58"/>
    <path d="M84 500l50-180 50 180" stroke="#e5e2e1" stroke-width="18" opacity="0.72"/>
    <path d="M82 690l52-190 52 190" stroke="{accent}" stroke-width="18" opacity="0.78"/>
  </g>
  <g transform="translate(64 64)">
    <rect x="0" y="0" width="164" height="36" rx="4" fill="{accent}" fill-opacity="0.16" stroke="{accent}" stroke-opacity="0.55"/>
    <text x="18" y="24" fill="{accent}" font-family="JetBrains Mono, Consolas, monospace" font-size="14" font-weight="700" letter-spacing="2">{label}</text>
    <text x="0" y="110" fill="#f4f4f5" font-family="Inter, Arial, sans-serif" font-size="42" font-weight="800">{primary}</text>
    <text x="0" y="152" fill="#919095" font-family="Inter, Arial, sans-serif" font-size="20">{secondary}</text>
  </g>
  <g transform="translate(64 796)">
    <text fill="#c8c6ca" font-family="Inter, Arial, sans-serif" font-size="24" font-weight="700">{name}</text>
    <text y="38" fill="#919095" font-family="JetBrains Mono, Consolas, monospace" font-size="14" letter-spacing="2">ACTIVE MUSCLE MAP</text>
  </g>
</svg>
"""
