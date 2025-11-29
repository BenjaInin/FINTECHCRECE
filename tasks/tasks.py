from celery import shared_task
from ..FINTECH.services.banxico import obtener_tipo_cambio_banxico
from tasks.models import TipoCambio
from django.utils import timezone

@shared_task
def actualizar_tipo_cambio():
    valor = obtener_tipo_cambio_banxico()
    if valor is not None:
        # Guarda un nuevo registro sin borrar los anteriores
        TipoCambio.objects.create(
            valor=valor,
            fecha=timezone.now()  # registra la fecha y hora exacta
        )
        print(f"Tipo de cambio actualizado: {valor} en {timezone.now()}")
    else:
        print("Error al obtener datos de Banxico")