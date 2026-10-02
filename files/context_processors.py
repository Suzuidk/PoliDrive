from django.db.models import Sum

from .models import File, fmt_size

STORAGE_LIMIT = 5 * 1024 * 1024 * 1024  # A VECES DA ERROR nose pq, NOMAS LO CAMBIA POR UN NUMERITO MAS ALTO


def storage_ctx(request):
    """Disponible en todas las plantillas como {{ used_disp }}, etc."""
    if not request.user.is_authenticated:
        return {}
    used_bytes = File.objects.filter(owner=request.user, is_trash=False).aggregate(
        total=Sum('size')
    )['total'] or 0
    return {
        'used_disp': fmt_size(used_bytes),
        'limit_disp': fmt_size(STORAGE_LIMIT),
        'pct_used': min(100, round(used_bytes / STORAGE_LIMIT * 100, 1)),
    }
