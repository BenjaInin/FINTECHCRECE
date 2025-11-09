from django import template
from datetime import datetime

register = template.Library()

@register.filter
def format_date(value):
    """Filtro para formatear la fecha a un formato específico."""
    if isinstance(value, datetime):
        return value.strftime('%d-%b-%Y')  # Ajusta el formato según lo necesites
    return value  # Si no es un objeto datetime, se devuelve el valor original