from django.contrib import admin

from .models import File, Folder, PubLink, SharedFile, Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('email', 'nombre', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('email', 'nombre')
    fields = ('email', 'nombre', 'is_active', 'is_staff', 'is_superuser')


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'parent', 'is_trash', 'created_at')
    list_filter = ('is_trash',)
    search_fields = ('name', 'owner__email')


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'folder', 'size', 'is_trash', 'upl_at')
    list_filter = ('is_trash',)
    search_fields = ('name', 'owner__email')


@admin.register(SharedFile)
class SharedFileAdmin(admin.ModelAdmin):
    list_display = ('file', 'shr_by', 'shr_with', 'perm', 'created_at')


@admin.register(PubLink)
class PubLinkAdmin(admin.ModelAdmin):
    list_display = ('file', 'token', 'active', 'created_at', 'revoked_at')
    list_filter = ('active',)
