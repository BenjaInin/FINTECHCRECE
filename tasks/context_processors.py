# tasks/context_processors.py
from .models import Usuario, CatTerceros  
from .views import get_valor_cuenta, get_saldo_prestamo

def datos_usuario_basicos(request):
    """
    Devuelve nombre y apellidos usando el COD_USUARIO guardado en la sesión,
    tomando los datos desde CatTerceros.
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return {}

    try:
        usuario = Usuario.objects.get(COD_USUARIO=user_id)
        tercero = CatTerceros.objects.get(COD_USUARIO=usuario.COD_USUARIO)
        valor_cuenta = get_valor_cuenta(tercero.ID_TERCERO, tercero.TIP_TERCERO)
        if valor_cuenta >= 1000:
            prestamo_disponible = valor_cuenta * 2 if valor_cuenta <= 10000 else 10000
        else:
            prestamo_disponible = 0
        saldo_prestamo = get_saldo_prestamo(tercero.ID_TERCERO, tercero.TIP_TERCERO)
        
        return {
            'usuario': usuario,
            'nombre': tercero.NOM_TERCERO,
            'ape_paterno': tercero.APE_PATERNO,
            'ape_materno': tercero.APE_MATERNO,
            'valor_cuenta': valor_cuenta,
            'prestamo_disponible': prestamo_disponible,
            'saldo_prestamo': saldo_prestamo,
        }

    except (Usuario.DoesNotExist, CatTerceros.DoesNotExist):
        return {}
