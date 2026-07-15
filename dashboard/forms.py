from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils.text import slugify

from .models import Exercise


User = get_user_model()


class DevUserCreationForm(UserCreationForm):
    first_name = forms.CharField(label="Nome", max_length=150, required=False)
    last_name = forms.CharField(label="Sobrenome", max_length=150, required=False)
    email = forms.EmailField(label="Email", required=False)
    is_staff = forms.BooleanField(label="Perfil dev", required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "is_staff")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "form-check-input precision-check"})
            else:
                field.widget.attrs.update({"class": "form-control"})
            if name in {"password1", "password2"}:
                field.help_text = ""


class ExerciseCreationForm(forms.ModelForm):
    instructions_text = forms.CharField(
        label="Instrucoes",
        required=False,
        widget=forms.Textarea,
        help_text="Uma instrucao por linha.",
    )

    class Meta:
        model = Exercise
        fields = (
            "name",
            "category",
            "focus",
            "primary_muscle",
            "secondary_muscles",
            "default_sets",
            "default_reps",
            "rest_seconds",
            "tutorial_duration",
            "image_url",
            "anatomy_image_url",
            "is_run",
        )
        labels = {
            "name": "Nome",
            "category": "Categoria",
            "focus": "Foco",
            "primary_muscle": "Musculo principal",
            "secondary_muscles": "Musculos secundarios",
            "default_sets": "Series padrao",
            "default_reps": "Reps padrao",
            "rest_seconds": "Descanso em segundos",
            "tutorial_duration": "Duracao do tutorial",
            "image_url": "Imagem",
            "anatomy_image_url": "Imagem anatomica",
            "is_run": "Exercicio de corrida",
        }
        widgets = {
            "instructions_text": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "form-check-input precision-check"})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({"class": "form-select"})
            else:
                field.widget.attrs.update({"class": "form-control"})

    def save(self, commit=True):
        exercise = super().save(commit=False)
        base_slug = slugify(exercise.name)
        candidate_slug = base_slug
        suffix = 2
        while Exercise.objects.filter(slug=candidate_slug).exists():
            candidate_slug = f"{base_slug}-{suffix}"
            suffix += 1

        exercise.slug = candidate_slug
        exercise.instructions = [
            line.strip()
            for line in self.cleaned_data.get("instructions_text", "").splitlines()
            if line.strip()
        ]

        if commit:
            exercise.save()
            self.save_m2m()

        return exercise
