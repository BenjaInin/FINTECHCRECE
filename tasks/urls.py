from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
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

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)