from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/register/', views.reg_view, name='register'),

    path('', views.dash, name='dash'),
    path('folder/new/', views.new_fold, name='new_fold'),
    path('folder/<int:fold_id>/', views.dash, name='fold_det'),
    path('folder/<int:folder_id>/rename/', views.ren_fold, name='ren_fold'),

    path('files/upload/', views.up_fl, name='up_fl'),
    path('file/<int:file_id>/edit/', views.edit_fl, name='edit_fl'),
    path('download/<int:file_id>/', views.dl_file, name='dl_file'),

    path('trash/', views.trash_vw, name='trash'),
    path('trash/file/<int:file_id>/', views.trash_fl, name='trash_fl'),
    path('trash/folder/<int:folder_id>/', views.trash_fld, name='trash_fld'),
    path('restore/file/<int:file_id>/', views.rest_fl, name='rest_fl'),
    path('restore/folder/<int:folder_id>/', views.rest_fld, name='rest_fld'),
    path('delete/file/<int:file_id>/', views.del_fl_perm, name='del_fl_perm'),
    path('delete/folder/<int:folder_id>/', views.del_fld_perm, name='del_fld_perm'),

    path('share/file/<int:file_id>/', views.shr_file, name='shr_file'),
    path('unshare/<int:share_id>/', views.unshr, name='unshr'),
    path('public-link/on/<int:file_id>/', views.pub_on, name='pub_on'),
    path('public-link/off/<int:file_id>/', views.pub_off, name='pub_off'),
    path('shared-with-me/', views.shrd_w_me, name='shrd_w_me'),

    path('p/<str:token>/', views.pub_fl, name='pub_fl'),
    path('p/<str:token>/download/', views.pub_dl, name='pub_dl'),
]
