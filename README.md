# NOMAS HIZE ESTA MADRE PARA RECORDAR COMANDOS

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

jasso es un pendejo

| DONDE SE ENCUENTRA CADA MADRE |
|---|---|
| Registro / login / logout, contraseñas con hash BCrypt | `files/forms.py`, `settings.py` (`PASSWORD_HASHERS`) |
| Carpetas y subcarpetas, listar, renombrar, eliminar (cascada lógica) | `files/models.py` (`Folder`), `views.py` |
| Subir varios archivos, descargar, mover (extra), editar | `views.py` (`up_fl`, `dl_file`, `edit_fl`) |
| Papelera: ver, restaurar, eliminar definitivo (borra en S3 + BD) | `views.py` (`trash_vw`, `rest_*`, `del_*_perm`) |
| Compartir con usuarios y "Compartido conmigo" | `SharedFile`, `shr_file`, `shrd_w_me` |
| Enlace público sin sesión + revocación | `PubLink`, `pub_on/off`, `pub_fl/pub_dl` |
| RDS MySQL / S3 / IAM Role | `settings.py` (variables del `.env`) |
| ERD, script SQL, decisiones de diseño, guía AWS | carpeta `docs/` |

Sin variables de AWS el proyecto usa **SQLite + carpeta `media/`**, para que puedas
desarrollar sin instalar nada. Con las variables del `.env` pasa a **MySQL (RDS) + S3**
sin tocar código.

## SOLO PONER ESTO EN CASO DE EMERGENCIA

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser      # ACA PONES CUALQUIER MAMADA COMO CORREO Y CONTRASEÑA
python manage.py runserver
```
http://127.0.0.1:8000/ 


`venv\Scripts\activate`  `python manage.py runserver`