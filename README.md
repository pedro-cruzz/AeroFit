# AeroFit

Projeto Django com templates e Bootstrap baseado no prototipo premium do AeroFit.

## Como rodar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_aerofit
python manage.py runserver
```

Depois acesse `http://127.0.0.1:8000/`.

Se o `pip` falhar por causa do caminho com acento/OneDrive, use um venv temporario fora da pasta:

```powershell
python -m venv "$env:TEMP\aerofit-venv"
& "$env:TEMP\aerofit-venv\Scripts\python.exe" -m pip install -r requirements.txt
& "$env:TEMP\aerofit-venv\Scripts\python.exe" manage.py migrate
& "$env:TEMP\aerofit-venv\Scripts\python.exe" manage.py seed_aerofit
& "$env:TEMP\aerofit-venv\Scripts\python.exe" manage.py runserver
```

## Banco Postgres no Neon

O projeto carrega variaveis de ambiente a partir de `.env`. Para usar o banco do Neon:

```powershell
Copy-Item .env.example .env
```

Abra o `.env` e cole a connection string do Neon em `DATABASE_URL`.
Use a URL no formato `postgresql://...` com `sslmode=require`.

Depois rode:

```powershell
python manage.py migrate
python manage.py seed_aerofit
python manage.py runserver
```

Sem `DATABASE_URL`, o projeto continua usando `db.sqlite3` para desenvolvimento local.

## Beta no Render

O projeto ja inclui `render.yaml` para criar o Web Service Python no Render usando o Postgres externo do Neon.

1. Suba este repositorio para GitHub/GitLab/Bitbucket.
2. No Render, crie um **Blueprint** apontando para o repositorio.
3. O Render vai usar `bash build.sh` para instalar dependencias, coletar arquivos estaticos e rodar migrations.
4. O start command configurado e:

```bash
python -m gunicorn aerofit_project.asgi:application -k uvicorn.workers.UvicornWorker
```

Variaveis configuradas pelo blueprint:

- `DATABASE_URL` deve receber a connection string do Neon no painel do Render.
- `DJANGO_SECRET_KEY` gerada automaticamente.
- `DJANGO_DEBUG=0`.
- `WEB_CONCURRENCY=4`.

Depois do primeiro deploy, rode no Shell do Render se quiser popular o beta com dados iniciais:

```bash
python manage.py seed_aerofit
python manage.py seed_extended_exercise_catalog
```

Para criar um admin:

```bash
python manage.py createsuperuser
```

## Paginas

- `/` Dashboard
- `/treinos/` Biblioteca de treinos
- `/treinos/montar/` Montar treino e salvar no banco configurado
- `/treinos/<id>/` Detalhe de uma rotina salva
- `/progresso/` Progresso
- `/elite/` Elite e comunidade
- `/exercicios/supino-reto/` Detalhes do exercicio

## Dados

Por padrao, os dados ficam em `db.sqlite3`. Quando `DATABASE_URL` estiver configurado, o Django usa o Postgres do Neon. O comando `python manage.py seed_aerofit` recria perfil, atributos, exercicios, rotinas, plano semanal, progresso, ranking e desafios. Para popular uma biblioteca maior de musculacao, corrida, cardio, HIIT e mobilidade, rode `python manage.py seed_extended_exercise_catalog`.

As imagens dos exercicios podem ficar versionadas em `dashboard/static/dashboard/exercises/`, mas devem ser fotos/ilustracoes reais do movimento ou assets gerados e revisados. A funcao de montagem esta em `dashboard/services.py` como `montar_treino(...)`.
