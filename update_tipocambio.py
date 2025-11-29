#!/usr/bin/env python
import os
import django
from django.utils import timezone

# Configuración Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "FINTECH.settings")
django.setup()

from FINTECH.services.banxico import obtener_tipo_cambio_banxico
from tasks.models import TipoCambio

# Obtener nuevo valor
nuevo_valor = obtener_tipo_cambio_banxico()
if nuevo_valor is None:
    print("Error al obtener datos de Banxico")
    exit(1)

# Obtener registro existente (solo uno)
try:
    tipo_cambio = TipoCambio.objects.first()
except TipoCambio.DoesNotExist:
    tipo_cambio = None

# Actualizar solo si cambió
if tipo_cambio:
    if tipo_cambio.valor != nuevo_valor:
        tipo_cambio.valor = nuevo_valor
        tipo_cambio.fecha = timezone.now()
        tipo_cambio.save()
        print(f"Tipo de cambio actualizado: {nuevo_valor}")
    else:
        print("Tipo de cambio sin cambios")
else:
    # Si no existe registro, crear
    TipoCambio.objects.create(valor=nuevo_valor, fecha=timezone.now())
    print(f"Tipo de cambio creado: {nuevo_valor}")
