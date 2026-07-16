from hashlib import sha256

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import Group
from django.utils import timezone
from django.utils.text import slugify

from .models import Exercise, LoginAttempt, WorkoutRoutine


User = get_user_model()
TRAINER_GROUP_NAME = "Personal"


def get_trainer_group():
    group, _created = Group.objects.get_or_create(name=TRAINER_GROUP_NAME)
    return group


def is_trainer(user):
    return bool(
        user
        and user.is_authenticated
        and user.groups.filter(name=TRAINER_GROUP_NAME).exists()
    )


def can_manage_exercises(user):
    return bool(user and user.is_authenticated and (user.is_staff or is_trainer(user)))


class SecureAuthenticationForm(AuthenticationForm):
    MAX_ATTEMPTS = 5
    LOCKOUT_SECONDS = 15 * 60

    error_messages = {
        "invalid_login": "Credenciais invalidas. Verifique usuario e senha.",
        "inactive": "Esta conta esta inativa.",
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {
                "class": "form-control",
                "autocomplete": "username",
                "autocapitalize": "none",
                "spellcheck": "false",
                "placeholder": "seu usuario",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "class": "form-control",
                "autocomplete": "current-password",
                "placeholder": "sua senha",
            }
        )

    def clean(self):
        username = self.cleaned_data.get("username", "").strip().lower()

        if username and self._is_locked(username):
            raise forms.ValidationError(
                "Muitas tentativas falhas. Aguarde alguns minutos e tente novamente.",
                code="locked",
            )

        try:
            cleaned_data = super().clean()
        except forms.ValidationError as error:
            if username:
                self._register_failure(username)
            raise error

        if username:
            self._clear_failures(username)
        return cleaned_data

    def _client_ip(self):
        if not self.request:
            return "unknown"
        return self.request.META.get("REMOTE_ADDR", "unknown")

    def _identity_hash(self, username):
        identity = f"{self._client_ip()}:{username}".encode()
        return sha256(identity).hexdigest()

    def _is_locked(self, username):
        attempt = LoginAttempt.objects.filter(identity_hash=self._identity_hash(username)).first()
        return bool(attempt and attempt.locked_until and attempt.locked_until > timezone.now())

    def _register_failure(self, username):
        attempt, _ = LoginAttempt.objects.get_or_create(identity_hash=self._identity_hash(username))
        attempt.attempts += 1

        if attempt.attempts >= self.MAX_ATTEMPTS:
            attempt.locked_until = timezone.now() + timezone.timedelta(seconds=self.LOCKOUT_SECONDS)
        attempt.save(update_fields=["attempts", "locked_until", "last_attempt_at"])

    def _clear_failures(self, username):
        LoginAttempt.objects.filter(identity_hash=self._identity_hash(username)).delete()


class DevUserCreationForm(UserCreationForm):
    first_name = forms.CharField(label="Nome", max_length=150, required=False)
    last_name = forms.CharField(label="Sobrenome", max_length=150, required=False)
    email = forms.EmailField(label="Email", required=False)
    is_trainer = forms.BooleanField(label="Perfil Personal", required=False)
    is_staff = forms.BooleanField(label="Conceder acesso Dev", required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "is_trainer", "is_staff")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "form-check-input precision-check"})
            else:
                field.widget.attrs.update({"class": "form-control"})
            if name in {"password1", "password2"}:
                field.help_text = ""

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and self.cleaned_data.get("is_trainer"):
            user.groups.add(get_trainer_group())
        return user


class PublicUserCreationForm(UserCreationForm):
    ACCOUNT_TYPE_CHOICES = [
        ("student", "Aluno"),
        ("trainer", "Personal"),
    ]

    first_name = forms.CharField(label="Nome", max_length=150, required=False)
    email = forms.EmailField(label="Email", required=False)
    account_type = forms.ChoiceField(
        label="Perfil",
        choices=ACCOUNT_TYPE_CHOICES,
        initial="student",
        widget=forms.RadioSelect,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "email", "account_type")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Usuario"
        self.fields["password1"].label = "Senha"
        self.fields["password2"].label = "Confirmar senha"
        self.fields["account_type"].widget.attrs.update({"class": "auth-radio-list"})
        self.fields["username"].widget.attrs.update(
            {
                "class": "form-control",
                "autocomplete": "username",
                "autocapitalize": "none",
                "spellcheck": "false",
                "placeholder": "seu usuario",
            }
        )
        self.fields["first_name"].widget.attrs.update(
            {
                "class": "form-control",
                "autocomplete": "given-name",
                "placeholder": "seu nome",
            }
        )
        self.fields["email"].widget.attrs.update(
            {
                "class": "form-control",
                "autocomplete": "email",
                "placeholder": "voce@email.com",
            }
        )
        for name in ("password1", "password2"):
            self.fields[name].help_text = ""
            self.fields[name].widget.attrs.update(
                {
                    "class": "form-control",
                    "autocomplete": "new-password",
                    "placeholder": "minimo 8 caracteres",
                }
            )

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and self.cleaned_data.get("account_type") == "trainer":
            user.groups.add(get_trainer_group())
        return user


class RoutineEditForm(forms.ModelForm):
    training_days = forms.MultipleChoiceField(
        label="Dias do treino",
        choices=WorkoutRoutine.WEEKDAY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = WorkoutRoutine
        fields = ("name", "goal", "training_days")
        labels = {
            "name": "Nome da planilha",
            "goal": "Objetivo",
        }

    def __init__(self, *args, **kwargs):
        self.routine = kwargs.get("instance")
        super().__init__(*args, **kwargs)
        self.fields["name"].widget.attrs.update({"class": "form-control"})
        self.fields["goal"].widget.attrs.update({"class": "form-select"})
        self.fields["training_days"].initial = self.routine.training_days if self.routine else []
        self.fields["training_days"].widget.attrs.update({"class": "form-check-input precision-check"})

        if not self.routine:
            return

        for item in self.routine.items.select_related("exercise"):
            self.fields[f"sets_{item.id}"] = forms.IntegerField(
                label=f"Series - {item.exercise.name}",
                min_value=1,
                max_value=20,
                initial=item.sets,
                widget=forms.NumberInput(attrs={"class": "form-control"}),
            )
            self.fields[f"reps_{item.id}"] = forms.CharField(
                label=f"Reps - {item.exercise.name}",
                max_length=40,
                initial=item.reps,
                widget=forms.TextInput(attrs={"class": "form-control"}),
            )
            self.fields[f"rest_{item.id}"] = forms.IntegerField(
                label=f"Descanso - {item.exercise.name}",
                min_value=0,
                max_value=600,
                initial=item.rest_seconds,
                widget=forms.NumberInput(attrs={"class": "form-control"}),
            )

    def save(self, commit=True):
        routine = super().save(commit=commit)
        for item in routine.items.all():
            item.sets = self.cleaned_data[f"sets_{item.id}"]
            item.reps = self.cleaned_data[f"reps_{item.id}"].strip()
            item.rest_seconds = self.cleaned_data[f"rest_{item.id}"]
            item.save(update_fields=["sets", "reps", "rest_seconds"])
        return routine


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
            "video_url",
            "video_credit",
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
            "video_url": "Video do YouTube",
            "video_credit": "Credito do video",
            "is_run": "Exercicio de corrida",
        }
        widgets = {
            "instructions_text": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["instructions_text"].initial = "\n".join(self.instance.instructions or [])

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
        existing = Exercise.objects.exclude(pk=exercise.pk) if exercise.pk else Exercise.objects.all()
        while existing.filter(slug=candidate_slug).exists():
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
