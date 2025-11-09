# tasks/context_processors.py
from .models import Usuario, CatTerceros  

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

        return {
            'usuario': usuario,
            'nombre': tercero.NOM_TERCERO,
            'ape_paterno': tercero.APE_PATERNO,
            'ape_materno': tercero.APE_MATERNO,
        }

    except (Usuario.DoesNotExist, CatTerceros.DoesNotExist):
        return {}
