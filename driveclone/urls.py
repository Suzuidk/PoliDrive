from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('files.urls')),
]
# Nota: NO se expone /media/. Los archivos son privados y solo se entregan
# a través de las vistas de descarga, que validan permisos.
