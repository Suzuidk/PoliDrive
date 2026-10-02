from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import FoldForm, RegForm, ShrForm
from .models import File, Folder, PubLink, SharedFile

MAX_UPL = 100 * 1024 * 1024  # ACA TMB SE AJUSTA SI DA ERROR

def _own_fold(request, fid):
    """Devuelve la carpeta propia (no eliminada) con ese id, o None (raíz)."""
    if not fid or not str(fid).isdigit():
        return None
    return get_object_or_404(Folder, pk=int(fid), owner=request.user, is_trash=False)


def _go(fold):
    """Redirige a la carpeta indicada (o a la raíz si es None)."""
    if fold:
        return redirect('fold_det', fold_id=fold.id)
    return redirect('dash')


def _stream(fl):
    """Entrega el archivo leyéndolo del storage (S3 o disco local).
    El bucket puede ser 100% privado: los permisos se validan aquí, en Django.
    """
    try:
        return FileResponse(fl.upload.open('rb'), as_attachment=True, filename=fl.name)
    except (FileNotFoundError, OSError):
        raise Http404('El archivo ya no existe en el almacenamiento.')

def reg_view(request):
    if request.user.is_authenticated:
        return redirect('dash')
    if request.method == 'POST':
        form = RegForm(request.POST)
        if form.is_valid():
            usr = form.save()
            login(request, usr)
            messages.success(request, '¡Cuenta creada! Bienvenido/a.')
            return redirect('dash')
    else:
        form = RegForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def dash(request, fold_id=None):
    curr_fold = None
    if fold_id:
        curr_fold = get_object_or_404(Folder, pk=fold_id, owner=request.user, is_trash=False)

    q = request.GET.get('q', '').strip()
    if q:
        curr_fold = None
        folds = Folder.objects.filter(owner=request.user, is_trash=False, name__icontains=q)
        fls = File.objects.filter(owner=request.user, is_trash=False, name__icontains=q)
    else:
        folds = Folder.objects.filter(owner=request.user, parent=curr_fold, is_trash=False)
        fls = File.objects.filter(owner=request.user, folder=curr_fold, is_trash=False)

    crumbs, node = [], curr_fold
    while node is not None:
        crumbs.insert(0, node)
        node = node.parent

    return render(request, 'files/dash.html', {
        'curr_fold': curr_fold, 'folds': folds, 'fls': fls, 'crumbs': crumbs, 'search_q': q,
    })

@login_required
@require_POST
def new_fold(request):
    parent = _own_fold(request, request.POST.get('fold_id'))
    name = request.POST.get('name', '').strip()
    if name:
        Folder.objects.create(name=name[:255], owner=request.user, parent=parent)
        messages.success(request, f'Carpeta "{name}" creada.')
    else:
        messages.error(request, 'La carpeta necesita un nombre.')
    return _go(parent)


@login_required
def ren_fold(request, folder_id):
    fold = get_object_or_404(Folder, pk=folder_id, owner=request.user, is_trash=False)
    form = FoldForm(request.POST or None, instance=fold)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Carpeta renombrada.')
        return _go(fold.parent)
    return render(request, 'files/rename.html', {'form': form, 'fold': fold})

@login_required
@require_POST
def up_fl(request):
    fold = _own_fold(request, request.POST.get('fold_id'))
    files = request.FILES.getlist('upload')
    if not files:
        messages.error(request, 'Selecciona al menos un archivo.')
        return _go(fold)
    ok = 0
    for f in files:
        if f.size > MAX_UPL:
            messages.error(request, f'"{f.name}" supera el límite de {MAX_UPL // (1024 * 1024)} MB.')
            continue
        File.objects.create(name=f.name[:255], owner=request.user, folder=fold, upload=f, size=f.size)
        ok += 1
    if ok:
        messages.success(request, f'{ok} archivo(s) subido(s) correctamente.')
    return _go(fold)


@login_required
def edit_fl(request, file_id):
    """Dueño o usuario con permiso de escritura: renombrar y reemplazar contenido.
    Solo el dueño puede además mover el archivo de carpeta.
    """
    fl = get_object_or_404(File, pk=file_id, is_trash=False)
    if not fl.can_edit(request.user):
        raise PermissionDenied('No tienes permiso de escritura sobre este archivo.')
    is_owner = fl.owner_id == request.user.id

    if request.method == 'POST':
        new_name = request.POST.get('name', '').strip()
        new_up = request.FILES.get('upload')
        old_key = None
        if new_name:
            fl.name = new_name[:255]
        if new_up:
            if new_up.size > MAX_UPL:
                messages.error(request, 'El archivo nuevo supera el límite de tamaño.')
                return redirect('edit_fl', file_id=fl.id)
            old_key = fl.upload.name
            fl.upload = new_up
            fl.size = new_up.size
        if is_owner and 'dest' in request.POST:
            fl.folder = _own_fold(request, request.POST.get('dest'))
        fl.save()
        if old_key:
            fl.upload.storage.delete(old_key)
        messages.success(request, 'Archivo actualizado.')
        return _go(fl.folder) if is_owner else redirect('shrd_w_me')

    dest_opts = []
    if is_owner:
        dest_opts = sorted(
            ((f.id, f.path_lbl()) for f in Folder.objects.filter(owner=request.user, is_trash=False)),
            key=lambda t: t[1],
        )
    return render(request, 'files/edit.html', {'fl': fl, 'is_owner': is_owner, 'dest_opts': dest_opts})


@login_required
def dl_file(request, file_id):
    fl = get_object_or_404(File, pk=file_id, is_trash=False)
    if not fl.can_view(request.user):
        raise PermissionDenied('No tienes permiso para ver este archivo.')
    return _stream(fl)

@login_required
def trash_vw(request):
    """Solo muestra la "raíz" de lo eliminado: si una carpeta está en la papelera,
    su contenido se ve al restaurarla, no suelto en esta lista.
    """
    folds = Folder.objects.filter(owner=request.user, is_trash=True).filter(
        Q(parent__isnull=True) | Q(parent__is_trash=False))
    fls = File.objects.filter(owner=request.user, is_trash=True).filter(
        Q(folder__isnull=True) | Q(folder__is_trash=False))
    return render(request, 'files/trash.html', {'folds': folds, 'fls': fls})


@login_required
@require_POST
def trash_fl(request, file_id):
    fl = get_object_or_404(File, pk=file_id, owner=request.user, is_trash=False)
    fl.mv_trash()
    messages.info(request, f'"{fl.name}" se movió a la papelera.')
    return _go(fl.folder)


@login_required
@require_POST
def trash_fld(request, folder_id):
    fold = get_object_or_404(Folder, pk=folder_id, owner=request.user, is_trash=False)
    fold.mv_trash()
    messages.info(request, f'Carpeta "{fold.name}" y todo su contenido se movieron a la papelera.')
    return _go(fold.parent)


@login_required
@require_POST
def rest_fl(request, file_id):
    fl = get_object_or_404(File, pk=file_id, owner=request.user, is_trash=True)
    fl.restore()
    messages.success(request, f'"{fl.name}" se restauró.')
    return redirect('trash')


@login_required
@require_POST
def rest_fld(request, folder_id):
    fold = get_object_or_404(Folder, pk=folder_id, owner=request.user, is_trash=True)
    fold.restore()
    messages.success(request, f'Carpeta "{fold.name}" se restauró con su contenido.')
    return redirect('trash')


@login_required
@require_POST
def del_fl_perm(request, file_id):
    fl = get_object_or_404(File, pk=file_id, owner=request.user, is_trash=True)
    name = fl.name
    fl.purge()
    messages.warning(request, f'"{name}" se eliminó definitivamente.')
    return redirect('trash')


@login_required
@require_POST
def del_fld_perm(request, folder_id):
    fold = get_object_or_404(Folder, pk=folder_id, owner=request.user, is_trash=True)
    name = fold.name
    fold.purge()
    messages.warning(request, f'Carpeta "{name}" eliminada definitivamente con todo su contenido.')
    return redirect('trash')

@login_required
def shr_file(request, file_id):
    fl = get_object_or_404(File, pk=file_id, owner=request.user, is_trash=False)

    if request.method == 'POST':
        form = ShrForm(request.POST)
        if form.is_valid():
            if form.usr == request.user:
                messages.error(request, 'No puedes compartir un archivo contigo mismo/a.')
            else:
                SharedFile.objects.update_or_create(
                    file=fl, shr_with=form.usr,
                    defaults={'shr_by': request.user, 'perm': form.cleaned_data['perm']},
                )
                messages.success(request, f'Compartido con {form.usr.nombre}.')
                return redirect('shr_file', file_id=fl.id)
    else:
        form = ShrForm()

    lnk = fl.links.filter(active=True).first()
    pub_url = request.build_absolute_uri(reverse('pub_fl', args=[lnk.token])) if lnk else ''
    return render(request, 'files/share.html', {
        'form': form, 'fl': fl,
        'shares': fl.shares.select_related('shr_with'),
        'lnk': lnk, 'pub_url': pub_url,
        'n_rev': fl.links.filter(active=False).count(),
    })


@login_required
@require_POST
def unshr(request, share_id):
    shr = get_object_or_404(SharedFile, pk=share_id, file__owner=request.user)
    fid = shr.file_id
    shr.delete()
    messages.info(request, 'Se revocó el acceso.')
    return redirect('shr_file', file_id=fid)


@login_required
@require_POST
def pub_on(request, file_id):
    fl = get_object_or_404(File, pk=file_id, owner=request.user, is_trash=False)
    if not fl.links.filter(active=True).exists():
        PubLink.objects.create(file=fl, created_by=request.user)
        messages.success(request, 'Enlace público generado.')
    return redirect('shr_file', file_id=fl.id)


@login_required
@require_POST
def pub_off(request, file_id):
    fl = get_object_or_404(File, pk=file_id, owner=request.user)
    fl.links.filter(active=True).update(active=False, revoked_at=timezone.now())
    messages.info(request, 'Enlace público desactivado.')
    return redirect('shr_file', file_id=fl.id)


@login_required
def shrd_w_me(request):
    fl_shr = SharedFile.objects.filter(
        shr_with=request.user, file__is_trash=False
    ).select_related('file', 'shr_by')
    return render(request, 'files/shrd_w_me.html', {'fl_shr': fl_shr})

def _get_lnk(token):
    return PubLink.objects.filter(
        token=token, active=True, file__is_trash=False
    ).select_related('file', 'file__owner').first()


def pub_fl(request, token):
    lnk = _get_lnk(token)
    return render(request, 'files/pub.html', {'lnk': lnk}, status=200 if lnk else 404)


def pub_dl(request, token):
    lnk = _get_lnk(token)
    if not lnk:
        raise Http404('Enlace no disponible.')
    return _stream(lnk.file)
