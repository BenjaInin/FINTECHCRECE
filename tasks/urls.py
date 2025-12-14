from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('registrame/', views.registrame, name='registrame'),
    path('config/', views.config, name='config'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('perfil/', views.perfil, name='perfil'),
    path('registro/', views.registro, name='registro'),
    path('logout/', views.logout_view, name='logout'),
    path('lista_movimientos/', views.lista_movimientos, name='lista_movimientos'),
    path('generar_reporte_pdf/', views.generar_reporte_pdf, name='generar_reporte_pdf'),
    # Path para remplazo de contraseña
   
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [

    # 1) Usuario ingresa su correo
    path('password_reset/', 
        views.password_reset_request, 
        name='password_reset'),

    # 2) Usuario hace clic en el correo
    path(
        'password_reset_confirm/<token>/',
        views.password_reset_confirm,
        name='password_reset_confirm'),

    # 3) Finalizado
    path('password_reset_complete/',
        views.password_reset_complete,
        name='password_reset_complete'),
]