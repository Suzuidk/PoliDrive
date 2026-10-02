import os
import secrets
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.urls import reverse
from django.utils import timezone

def usr_key(inst, fname):
    """Key del objeto en S3: usuario_<id>/<uuid>_<nombre>.

    El uuid evita colisiones si dos archivos tienen el mismo nombre.
    """
    return f'usuario_{inst.owner_id}/{uuid.uuid4().hex}_{os.path.basename(fname)}'


def new_token():
    """Token aleatorio (no adivinable) para los enlaces públicos."""
    return secrets.token_urlsafe(24)


def fmt_size(num_bytes):
    """Convierte bytes a un texto legible (KB/MB/GB)."""
    size = num_bytes
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f'{size:.0f} {unit}' if unit == 'B' else f'{size:.1f} {unit}'
        size /= 1024
    return f'{size:.1f} TB'

class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email)

    def _create(self, email, nombre, password, **extra):
        if not email:
            raise ValueError('El correo es obligatorio.')
        email = self.normalize_email(email).lower()
        usr = self.model(email=email, nombre=nombre, **extra)
        usr.set_password(password)
        usr.save(using=self._db)
        return usr

    def create_user(self, email, nombre='', password=None, **extra):
        extra.setdefault('is_staff', False)
        extra.setdefault('is_superuser', False)
        return self._create(email, nombre, password, **extra)

    def create_superuser(self, email, nombre='', password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self._create(email, nombre, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField('correo electrónico', max_length=190, unique=True)
    nombre = models.CharField('nombre', max_length=150)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre']

    class Meta:
        db_table = 'usuarios'

    def __str__(self):
        return self.email

class Folder(models.Model):
    name = models.CharField('nombre', max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='folders')
    parent = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE, related_name='subfolders'
    )
    created_at = models.DateTimeField('creado', auto_now_add=True)

    is_trash = models.BooleanField('en papelera', default=False, db_column='eliminado')
    trash_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'carpetas'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('fold_det', args=[self.pk])

    def desc(self):
        """Todas las subcarpetas (a cualquier nivel), recorriendo por niveles."""
        res, level = [], [self.id]
        while level:
            kids = list(Folder.objects.filter(parent_id__in=level))
            res.extend(kids)
            level = [k.id for k in kids]
        return res

    def ids_tree(self):
        return [self.id] + [f.id for f in self.desc()]

    def path_lbl(self):
        parts, node = [], self
        while node is not None:
            parts.insert(0, node.name)
            node = node.parent
        return ' / '.join(parts)

    def mv_trash(self):
        """Eliminación lógica EN CASCADA: la carpeta, todas sus subcarpetas y
        todos sus archivos pasan a la papelera con la MISMA marca de tiempo.
        Lo que ya estaba en la papelera (con otra fecha) no se toca.
        """
        now = timezone.now()
        ids = self.ids_tree()
        Folder.objects.filter(id__in=ids, is_trash=False).update(is_trash=True, trash_at=now)
        File.objects.filter(folder_id__in=ids, is_trash=False).update(is_trash=True, trash_at=now)
        self.is_trash = True
        self.trash_at = now

    def restore(self):
        """Restaura la carpeta y solo lo que se fue a la papelera junto con ella
        (misma marca de tiempo). Lo eliminado antes por separado sigue en la papelera.
        """
        if self.parent_id and self.parent.is_trash:
            self.parent = None  # su carpeta original ya no está disponible: vuelve a la raíz
            self.save(update_fields=['parent'])
        t = self.trash_at
        ids = self.ids_tree()
        Folder.objects.filter(id__in=ids, is_trash=True, trash_at=t).update(is_trash=False, trash_at=None)
        File.objects.filter(folder_id__in=ids, is_trash=True, trash_at=t).update(is_trash=False, trash_at=None)
        self.is_trash = False
        self.trash_at = None

    def purge(self):
        """Eliminación DEFINITIVA: borra de S3 los objetos de todos los archivos
        del árbol y luego los registros de la BD (el resto cae por CASCADE).
        """
        for fl in File.objects.filter(folder_id__in=self.ids_tree()):
            if fl.upload:
                fl.upload.delete(save=False)
        self.delete()

class File(models.Model):
    name = models.CharField('nombre', max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='files')
    folder = models.ForeignKey(
        Folder, null=True, blank=True, on_delete=models.CASCADE, related_name='files'
    )
    upload = models.FileField('archivo (key en S3)', upload_to=usr_key, max_length=500)
    size = models.PositiveBigIntegerField('tamaño (bytes)', default=0)
    upl_at = models.DateTimeField('subido', auto_now_add=True)

    is_trash = models.BooleanField('en papelera', default=False, db_column='eliminado')
    trash_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'archivos'
        ordering = ['-upl_at']

    def __str__(self):
        return self.name

    def size_disp(self):
        return fmt_size(self.size)

    def mv_trash(self):
        self.is_trash = True
        self.trash_at = timezone.now()
        self.save(update_fields=['is_trash', 'trash_at'])

    def restore(self):
        if self.folder_id and self.folder.is_trash:
            self.folder = None
        self.is_trash = False
        self.trash_at = None
        self.save(update_fields=['is_trash', 'trash_at', 'folder'])

    def purge(self):
        """Borra el objeto real de S3 y el registro de la BD."""
        if self.upload:
            self.upload.delete(save=False)
        self.delete()

    def can_view(self, usr):
        """¿Puede este usuario ver el archivo? Dueño O compartido con él."""
        if self.owner_id == usr.id:
            return True
        return self.shares.filter(shr_with=usr).exists()

    def can_edit(self, usr):
        """¿Puede editarlo? Dueño O compartido con permiso de escritura."""
        if self.owner_id == usr.id:
            return True
        return self.shares.filter(shr_with=usr, perm='edit').exists()

class SharedFile(models.Model):
    PERM_CHOICES = [
        ('view', 'Solo lectura'),
        ('edit', 'Lectura y escritura'),
    ]

    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='shares')
    shr_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shr_by_me')
    shr_with = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shr_with_me')
    perm = models.CharField(max_length=10, choices=PERM_CHOICES, default='view')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'archivos_compartidos'
        unique_together = [('file', 'shr_with')]

    def __str__(self):
        return f'{self.file} -> {self.shr_with}'

class PubLink(models.Model):
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='links')
    token = models.CharField(max_length=64, unique=True, default=new_token)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pub_links')
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'enlaces_publicos'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.file} ({"activo" if self.active else "revocado"})'
