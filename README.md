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

## Páginas

- `/` Dashboard
- `/treinos/` Biblioteca de treinos
- `/treinos/montar/` Montar treino e salvar no SQLite
- `/treinos/<id>/` Detalhe de uma rotina salva
- `/progresso/` Progresso
- `/elite/` Elite e comunidade
- `/exercicios/supino-reto/` Detalhes do exercício

## Dados

Os dados ficam em `db.sqlite3`. O comando `python manage.py seed_aerofit` recria perfil, atributos, exercícios, rotinas, plano semanal, progresso, ranking e desafios. A função de montagem está em `dashboard/services.py` como `montar_treino(...)`.
