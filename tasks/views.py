import logging
import bcrypt  # type: ignore
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from django.shortcuts import render, redirect
from .forms import LoginForm, RegisterForm
from .models import Usuario, CatTerceros, CatTipMovimientos,CatTipoTercero,CatTerUsuario
from django.db.models import Sum
from django.shortcuts import render, redirect
from .models import HisMovimientos, CatTerceros
from django.db.models import Sum
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.db.models.functions import ExtractMonth, ExtractYear
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle,Paragraph, Image,Spacer
from reportlab.lib import colors
from django.conf import settings
from reportlab.lib.styles import getSampleStyleSheet
from django.contrib import messages
from django.db import transaction
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render
from tasks.models import TipoCambio
from django.core.mail import send_mail
from django.urls import reverse
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
import os


# ------------------------------------- FUNCION HOME ----------------------------------------------
def home(request):
    """
    Función que renderiza la página de inicio interactiva (landing page).
    Esta vista no requiere autenticación.
    """
    return render(request, 'home.html')
# -------------------------------------------------------------------------------------------------------
def config(request):
    return render(request, 'config.html')
# ------------------------------------- FUNCION PERFIL ----------------------------------------------
def perfil(request):
      # Verificar si hay usuario en sesión
    user_id = request.session.get('user_id')
    if not user_id:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Debes iniciar sesión para acceder al perfil.'})
        messages.error(request, "Debes iniciar sesión para acceder al perfil.")
        return redirect('login')

    try:
        usuario = Usuario.objects.get(COD_USUARIO=user_id)
        tercero = CatTerceros.objects.get(COD_USUARIO=usuario.COD_USUARIO)
    except Usuario.DoesNotExist:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Usuario no encontrado.'})
        messages.error(request, "No se encontró el usuario.")
        return redirect('login')
    except CatTerceros.DoesNotExist:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Información del tercero no encontrada.'})
        messages.error(request, "No se encontró la información del tercero.")
        return redirect('dashboard')

    # Manejar POST
    if request.method == 'POST':
        nuevo_correo = request.POST.get('correo', '').strip()
        cambios_realizados = False
        mensajes = []

        # Actualizar correo si cambió
        if nuevo_correo and nuevo_correo != usuario.CORREO:
            usuario.CORREO = nuevo_correo
            cambios_realizados = True
            mensajes.append("Correo actualizado correctamente.")

        # Actualizar foto de perfil si se subió
        if 'FOTO_PERFIL' in request.FILES:
            usuario.FOTO_PERFIL = request.FILES['FOTO_PERFIL']
            cambios_realizados = True
            mensajes.append("Foto de perfil actualizada correctamente.")

        if cambios_realizados:
            usuario.save()
            response_data = {'success': True, 'messages': mensajes}
        else:
            response_data = {'success': False, 'message': 'No se realizaron cambios.'}

        # Retornar JSON si es AJAX
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse(response_data)

        # Si no es AJAX, redirigir
        if cambios_realizados:
            messages.success(request, "Cambios guardados correctamente.")
        else:
            messages.info(request, "No se realizaron cambios.")
        return redirect('perfil')

    # GET: enviar datos al template
    contexto = {
        'usuario': usuario,
        'nombre': tercero.NOM_TERCERO,
        'ape_paterno': tercero.APE_PATERNO,
        'ape_materno': tercero.APE_MATERNO,
        # 'prestamo_disponible': ... si tienes ese dato
    }

    return render(request, 'perfil.html', contexto)
# ---------------------------------------FUNCION REGISTRAME----------------------------------------------------------------

# Configurar logs
logger = logging.getLogger(__name__)
def registrame(request):
    if request.method == 'POST':
        try:
            logger.info("=== Iniciando proceso de registro de usuario ===")

            # Obtener datos del formulario
            NOM_TERCERO = request.POST.get('NOM_TERCERO', '').strip()
            APE_PATERNO = request.POST.get('APE_PATERNO', '').strip()
            APE_MATERNO = request.POST.get('APE_MATERNO', '').strip()
            CORREO = request.POST.get('CORREO_USUARIO', '').strip()
            NUM_TEL = request.POST.get('TELEFONO_USUARIO', '').strip()
            COD_PASS = request.POST.get('COD_PASS', '').strip()
        
            logger.info(f"Datos recibidos -> Nombre: {NOM_TERCERO}, Paterno: {APE_PATERNO}, Materno: {APE_MATERNO}, Correo: {CORREO}, Teléfono: {NUM_TEL}")

            #Validaciones
            if not all([NOM_TERCERO, APE_PATERNO, APE_MATERNO, CORREO, NUM_TEL, COD_PASS]):
                logger.warning("Campos incompletos detectados")
                messages.error(request, "Por favor completa todos los campos.")
                return redirect('registrame')

            # Generar COD_USUARIO
            COD_USUARIO = (NOM_TERCERO[:2] + APE_PATERNO + APE_MATERNO[:2]).lower()
            contador = 1
            original = COD_USUARIO
            while Usuario.objects.filter(COD_USUARIO=COD_USUARIO).exists():
                COD_USUARIO = f"{original}{contador}"
                contador += 1
            logger.info(f"COD_USUARIO generado: {COD_USUARIO}")

           # Encriptar contraseña con make_password (Django estándar)
            COD_PASS_HASH = make_password(COD_PASS)
            logger.info("Contraseña encriptada con make_password correctamente")

            # Fecha actual
            FEC_ACTUALIZACION = timezone.now().date()
            logger.info(f"Fecha actual del servidor: {FEC_ACTUALIZACION}")

            # Nuevo ID_TERCERO consecutivo
            ultimo = CatTerceros.objects.all().values_list('ID_TERCERO', flat=True)
            if ultimo:
                try:
                    ids_validos = [int(i) for i in ultimo if str(i).isdigit()]
                    nuevo_id_num = max(ids_validos) + 1 if ids_validos else 1
                    nuevo_id = str(nuevo_id_num).zfill(5)
                except Exception as e:
                    logger.warning(f"No se pudo calcular el ID_TERCERO: {e}")
                    nuevo_id = '00001'
            else:
                nuevo_id = '00001'
            logger.info(f"Nuevo ID_TERCERO generado: {nuevo_id}")

            # Inserción en tablas
            with transaction.atomic():
                # CAT_USUARIOS
                usuario = Usuario.objects.create(
                    COD_USUARIO=COD_USUARIO,
                    CORREO=CORREO,
                    TIP_USUARIO='ACC',
                    COD_PERMISOS=1,
                    COD_PASS=COD_PASS_HASH,
                    FEC_ACTUALIZACION=FEC_ACTUALIZACION,
                    MCA_INHABILITADO='N',
                    NUM_TEL=NUM_TEL
                )
                logger.info(f"Usuario insertado en CAT_USUARIOS con COD_USUARIO: {usuario.COD_USUARIO}")

                # CAT_TERCEROS
                CatTerceros.objects.create(
                    ID_TERCERO=nuevo_id,
                    TIP_TERCERO=1,
                    NOM_TERCERO=NOM_TERCERO,
                    APE_PATERNO=APE_PATERNO,
                    APE_MATERNO=APE_MATERNO,
                    FEC_ACTUALIZACION=FEC_ACTUALIZACION,
                    MCA_INHABILITADO='N',
                    COD_USUARIO=usuario
                )

                # CAT_TER_USUARIO
                CatTerUsuario.objects.create(
                    COD_USUARIO=usuario.COD_USUARIO,
                    ID_TERCERO=nuevo_id,
                    TIP_TERCERO=1,
                    FEC_ACTUALIZACION=FEC_ACTUALIZACION,
                    MCA_INHABILITADO='N'
                )
                logger.info(f"Tercero insertado en CAT_TERCEROS y CAT_TER_USUARIO con ID_TERCERO: {nuevo_id}")

            # Mensaje de éxito con SweetAlert
            messages.success(request, "¡Bienvenido! Has sido registrado en CRECE LANA 🎉")
            return redirect('registrame')

        except Exception as e:
            logger.error(f"Error durante el registro: {str(e)}", exc_info=True)
            messages.error(request, f"Error al registrar usuario: {str(e)}")
            return redirect('registrame')

    return render(request, 'registrarse.html')
# ------------------------------------- FUNCION REGISTRO ----------------------------------------------
def registro(request):
     # Limpiar mensajes pendientes (para evitar mensajes de vistas previas)
    list(messages.get_messages(request))  

      # Obtener listas para los selects del formulario
    terceros = CatTerceros.objects.all().order_by('NOM_TERCERO')
    movimientos = CatTipMovimientos.objects.all()
    tiptercero = CatTipoTercero.objects.all()

    # --- Si el formulario fue enviado ---
    if request.method == 'POST':
        try:
            # Obtener los valores enviados desde el formulario HTML
            id_tercero_id = request.POST.get('ID_TERCERO')
            tip_tercero = request.POST.get('TIP_TERCERO')
            cod_movimiento_id = request.POST.get('COD_MOVIMIENTO')
            imp_retiro = request.POST.get('IMP_RETIRO') or None
            imp_deposito = request.POST.get('IMP_DEPOSITO') or None

            # Obtener el usuario que está logueado
            user_id = request.session.get('user_id')
            usuario = Usuario.objects.get(COD_USUARIO=user_id)

            # Obtener las referencias de claves foráneas
            tercero = CatTerceros.objects.get(ID_TERCERO=id_tercero_id)
            cod_movimiento = CatTipMovimientos.objects.get(COD_MOVIMIENTO=cod_movimiento_id)

            # Fechas
            fecha_actual = timezone.now().date()

            # Crear registro en la tabla HIS_MOVIMIENTOS
            HisMovimientos.objects.create(
                ID_TERCERO=tercero,
                TIP_TERCERO=tip_tercero,
                COD_MOVIMIENTO=cod_movimiento,
                FEC_REGISTRO=fecha_actual,
                FEC_ACTUALIZACION=fecha_actual,
                IMP_RETIRO=imp_retiro,
                IMP_DEPOSITO=imp_deposito,
                MCA_INHABILITADO='N',
                COD_USUARIO=usuario
            )

            messages.success(request, "Movimiento registrado correctamente ")
            return redirect('registro')

        except Exception as e:
            messages.error(request, f"Error al registrar el movimiento: {str(e)}")

    # --- Mostrar formulario por primera vez o si hay error ---
    return render(request, 'registro.html', {
        'terceros': terceros,
        'movimientos': movimientos,
        'tiptercero': tiptercero
    })
#-------------------------------------Funcion Dashboard----------------------------------------------
def dashboard(request):
    user_id = request.session.get('user_id')  # Obtener el COD_USUARIO desde la sesión

    if user_id:
        try:
            # Obtener el objeto Usuario con el COD_USUARIO desde la sesión
            usuario = Usuario.objects.get(COD_USUARIO=user_id)
            
            # Obtener el objeto CatTerceros asociado al usuario logueado
            tercero = CatTerceros.objects.get(COD_USUARIO=usuario.COD_USUARIO)

            # -------Selector de año (sin afectar tu lógica anterior)
            from datetime import datetime
            anio_actual = datetime.now().year
            anio_seleccionado = request.GET.get("anio", anio_actual)

            try:
                anio_seleccionado = int(anio_seleccionado)
            except:
                anio_seleccionado = anio_actual

            # Años disponibles por movimientos reales
            anos_disponibles_query = (
                HisMovimientos.objects
                .filter(ID_TERCERO=tercero.ID_TERCERO, TIP_TERCERO=tercero.TIP_TERCERO)
                .dates('FEC_REGISTRO', 'year')
            )

            anos_disponibles = sorted(list(set([d.year for d in anos_disponibles_query])), reverse=True)

            if not anos_disponibles:
                anos_disponibles = [anio_actual]

            # Obtener el valor de la cuenta usando la función get_valor_cuenta
            valor_cuenta = get_valor_cuenta(tercero.ID_TERCERO, tercero.TIP_TERCERO)
            
            # Calcular el valor para préstamo
            if valor_cuenta >= 1000:
                prestamo_disponible = valor_cuenta * 2 if valor_cuenta <= 10000 else 10000
            else:
                prestamo_disponible = 0
            
            # Pasamos el año para tus funciones (si lo necesitan)
            # Si tus funciones no aceptan año, no pasa nada: siguen igual.
            # Convertir las listas de aportaciones y rendimientos a JSON
            try:
                aportaciones = get_aportaciones_por_mes(tercero.ID_TERCERO, tercero.TIP_TERCERO, anio_seleccionado)
            except:
                aportaciones = get_aportaciones_por_mes(tercero.ID_TERCERO, tercero.TIP_TERCERO)

            try:
                rendimientos = get_rendimientos_por_mes(tercero.ID_TERCERO, tercero.TIP_TERCERO, anio_seleccionado)
            except:
                rendimientos = get_rendimientos_por_mes(tercero.ID_TERCERO, tercero.TIP_TERCERO)

            aportaciones_float = [float(a) if a is not None else 0 for a in aportaciones]
            rendimientos_float = [float(r) if r is not None else 0 for r in rendimientos]

            # Ultimos movimientos
            ultimos_movimientos = get_ultimos_movimientos(tercero.ID_TERCERO, tercero.TIP_TERCERO)
            
            # OBTENER SALDO DEL PRÉSTAMO usando el tercero ya obtenido
            saldo_prestamo = get_saldo_prestamo(tercero.ID_TERCERO, tercero.TIP_TERCERO)

            # Convertir las listas a JSON
            aportaciones_json = json.dumps(aportaciones_float)
            rendimientos_json = json.dumps(rendimientos_float)

            # Obtener el valor de disponible_retiro
            disponible_retiro = get_disponible_retiro(tercero.ID_TERCERO, tercero.TIP_TERCERO)

            # Obtener el último tipo de cambio
            tipo_cambio = TipoCambio.objects.order_by('-fecha').first()  # último registrado

            # Pasar los datos al template
            return render(request, 'dashboard.html', {
                'usuario': usuario,
                'cod_usuario': usuario.COD_USUARIO,
                'nombre': tercero.NOM_TERCERO,
                'ape_paterno': tercero.APE_PATERNO,
                'ape_materno': tercero.APE_MATERNO,
                'valor_cuenta': valor_cuenta,
                'prestamo_disponible': prestamo_disponible,
                'aportaciones': aportaciones_json,
                'rendimientos': rendimientos_json,
                'disponible_retiro': disponible_retiro,
                'ultimos_movimientos': ultimos_movimientos,
                "saldo_prestamo": saldo_prestamo,
                'tipo_cambio_usd': tipo_cambio.valor if tipo_cambio else "N/D",
                'anio_seleccionado': anio_seleccionado,
                'anos_disponibles': anos_disponibles,
            })
        
        except Usuario.DoesNotExist:
            return redirect('login')
        except CatTerceros.DoesNotExist:
            return render(request, 'dashboard.html', {'error': 'No se encontró información del tercero.'})
    else:
        return redirect('login')

#----------------------------------------Funcion login------------------------------------------------
def login_view(request):
    list(messages.get_messages(request))  # Limpia mensajes previos

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            identificador = form.cleaned_data['username']
            password = form.cleaned_data['password']

            print("Intento de login con:", identificador)

            try:
                # Buscar por usuario, correo o teléfono
                user = (
                    Usuario.objects.filter(COD_USUARIO=identificador).first()
                    or Usuario.objects.filter(CORREO=identificador).first()
                    or Usuario.objects.filter(NUM_TEL=identificador).first()
                )

                # Caso 1: usuario no encontrado
                if not user:
                    print("No se encontró ningún usuario con ese identificador.")
                    return render(request, 'login.html', {'form': form, 'error_code': 'usuario'})

                print(f"Usuario encontrado: {user.COD_USUARIO} ({user.CORREO})")

                # Caso 2: usuario inhabilitado
                if user.MCA_INHABILITADO == 'S':
                    print("Usuario inhabilitado.")
                    return render(request, 'login.html', {'form': form, 'error_code': 'inhabilitado'})

                # Caso 3: contraseña correcta
                if check_password(password, user.COD_PASS):
                    print("Contraseña verificada correctamente.")
                    request.session['user_id'] = user.COD_USUARIO
                    return redirect('dashboard')

                # Caso 4: compatibilidad por si el password está sin encriptar
                elif user.COD_PASS == password:
                    print("Contraseña coincide sin encriptar (modo compatibilidad).")
                    request.session['user_id'] = user.COD_USUARIO
                    return redirect('dashboard')

                # Caso 5: contraseña incorrecta
                else:
                    print(" Contraseña incorrecta.")
                    return render(request, 'login.html', {'form': form, 'error_code': 'password'})

            except Exception as e:
                print(" Error durante el login:", str(e))
                return render(request, 'login.html', {
                    'form': form,
                    'error_code': 'error',
                    'error_message': str(e)
                })
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})

#--------------------------FUNCIONES DE DATE Y MONTOS---------------------------------------------------
def format_date(date):
    return date.strftime('&Y-%b-%d') if date else ''

def format_money(amount):
    return f"${amount:,.2f}"
#-----------------------Ultimos movimientos -------------------------------------------------------#
def get_ultimos_movimientos(id_tercero, tip_tercero):
    """
    Obtiene los últimos 5 movimientos del usuario ordenados por fecha.
    """
    return HisMovimientos.objects.filter(
        ID_TERCERO=id_tercero,
        TIP_TERCERO=tip_tercero
    ).select_related('COD_MOVIMIENTO') \
     .order_by('-FEC_REGISTRO')[:5]

#-------------------------------Funcion Lista Movimientos-------------------------------------------------
def lista_movimientos(request):
    list(messages.get_messages(request))  # Esto vacía los mensajes pendientes
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    try:
        usuario = Usuario.objects.get(COD_USUARIO=user_id)
        tercero_usuario = CatTerceros.objects.get(COD_USUARIO=usuario)

        # Obtener todos los terceros para el select (solo administradores)
        terceros = CatTerceros.objects.all()  # Puedes filtrar según tu lógica

        # Valores iniciales por defecto: el propio tercero del usuario
        id_tercero = tercero_usuario.ID_TERCERO
        tip_tercero = tercero_usuario.TIP_TERCERO

        if request.method == 'POST' and usuario.COD_PERMISOS == 99:
            # Obtener el tercero seleccionado del formulario
            id_tercero = request.POST.get('id_tercero')
            # Obtener automáticamente el TIP_TERCERO del tercero seleccionado
            tercero_seleccionado = CatTerceros.objects.get(ID_TERCERO=id_tercero)
            tip_tercero = tercero_seleccionado.TIP_TERCERO

        # Filtrar movimientos usando ID_TERCERO y TIP_TERCERO
        movimientos = HisMovimientos.objects.filter(
            ID_TERCERO__ID_TERCERO=id_tercero,
            TIP_TERCERO=tip_tercero
        ).select_related('COD_MOVIMIENTO').order_by('FEC_REGISTRO')

        # Procesamiento de saldos
        saldo_acumulado = 0
        saldo_total = 0
        suma_depositos = 0
        suma_retiros = 0
        sumatorias_por_tipo = {}
        prestamo_por_liquidar = 0

        for mov in movimientos:
            imp_retiro = float(mov.IMP_RETIRO or 0)
            imp_deposito = float(mov.IMP_DEPOSITO or 0)
            saldo_acumulado += imp_deposito + imp_retiro
            saldo_total += imp_deposito + imp_retiro
            suma_depositos += imp_deposito
            suma_retiros += imp_retiro 
            mov.saldo_acumulado = saldo_acumulado

            tipo_movimiento = mov.COD_MOVIMIENTO.DESC_MOVIMIENTO
            sumatorias_por_tipo[tipo_movimiento] = sumatorias_por_tipo.get(tipo_movimiento, 0) + imp_deposito + imp_retiro

            if tipo_movimiento in ['PRESTAMO', 'PAG.CAPIT.PREST.']:
                prestamo_por_liquidar += imp_deposito + imp_retiro

        sumatorias_por_tipo['Prestamo por liquidar:'] = prestamo_por_liquidar
        now = timezone.now()

        return render(request, 'lista_movimientos.html', {
            'usuario': usuario,
            'nombre_completo': f"{tercero_usuario.NOM_TERCERO} {tercero_usuario.APE_PATERNO} {tercero_usuario.APE_MATERNO}",
            'movimientos': movimientos,
            'sumatorias_por_tipo': sumatorias_por_tipo,
            'saldo_total': saldo_total,
            'suma_depositos': suma_depositos,
            'suma_retiros': suma_retiros,
            'saldo_acumulado': saldo_acumulado,
            'terceros': terceros,  # Para el select
            'selected_id_tercero': id_tercero,
            'selected_tip_tercero': tip_tercero,  # Se usa internamente, no se muestra
            'now': now
        })

    except Usuario.DoesNotExist:
        return redirect('login')
    except CatTerceros.DoesNotExist:
        return render(request, 'lista_movimientos.html', {'error': 'No se encontró información del tercero.'})
#-------------------------------------Saldo prestamo -------------------------------------------------------------#
def get_saldo_prestamo(id_tercero, tip_tercero):
    """
    Retorna el saldo del préstamo de un tercero específico.
    Considera los movimientos 'PRESTAMO' y 'PAG.CAPIT.PREST.'
    """
    movimientos = HisMovimientos.objects.filter(
        ID_TERCERO__ID_TERCERO=id_tercero,
        TIP_TERCERO=tip_tercero
    ).select_related('COD_MOVIMIENTO')

    saldo_prestamo = 0
    for mov in movimientos:
        imp_deposito = float(mov.IMP_DEPOSITO or 0)
        imp_retiro = float(mov.IMP_RETIRO or 0)
        tipo_movimiento = mov.COD_MOVIMIENTO.DESC_MOVIMIENTO
        if tipo_movimiento in ['PRESTAMO', 'PAG.CAPIT.PREST.']:
            saldo_prestamo += (imp_deposito - imp_retiro) * -1

    return round(saldo_prestamo, 2)
#-----------------------------Salir logout----------------------------------------------------------------

def logout_view(request):
    request.session.flush()  # Elimina toda la información de la sesión
    return redirect('login')

#----------------------------------Funciones necesarias para operaciones de FINTECH-----------------------
def get_valor_cuenta(id_tercero, tip_tercero):
    # Realizamos la consulta de los depósitos donde COD_MOVIMIENTO es 1
    deposito_1 = HisMovimientos.objects.filter(
        ID_TERCERO=id_tercero,
        TIP_TERCERO=tip_tercero,
        COD_MOVIMIENTO=1
    ).aggregate(
        suma_deposito_1=Sum('IMP_DEPOSITO')
    )['suma_deposito_1'] or 0

    # Realizamos la consulta de los depósitos donde COD_MOVIMIENTO es 5
    deposito_5 = HisMovimientos.objects.filter(
        ID_TERCERO=id_tercero,
        TIP_TERCERO=tip_tercero,
        COD_MOVIMIENTO=5
    ).aggregate(
        suma_deposito_5=Sum('IMP_DEPOSITO')
    )['suma_deposito_5'] or 0

    # Sumamos ambos resultados para obtener el valor total de la cuenta
    valor_cuenta = deposito_1 + deposito_5

    return valor_cuenta



#------------------------------------Funcion aportacion por mes----------------------------------------- 
def get_aportaciones_por_mes(id_tercero, tip_tercero, anio):
    aportaciones = HisMovimientos.objects.filter(
        ID_TERCERO=id_tercero,
        TIP_TERCERO=tip_tercero,
        COD_MOVIMIENTO=1,
        FEC_REGISTRO__year=anio
    ).annotate(
        mes=ExtractMonth('FEC_REGISTRO')
    ).values('mes').annotate(
        total_aportaciones=Sum('IMP_DEPOSITO')
    ).order_by('mes')

    aportaciones_mes = [0] * 12
    acumulado = 0

    for ap in aportaciones:
        mes = ap['mes'] - 1
        acumulado += ap['total_aportaciones']
        aportaciones_mes[mes] = acumulado

    # Completar meses sin datos
    for i in range(1, 12):
        if aportaciones_mes[i] == 0 and aportaciones_mes[i-1] != 0:
            aportaciones_mes[i] = aportaciones_mes[i-1]

    return aportaciones_mes

#-------------------------------Funcion rendimiento por mes---------------------------------------------- 
def get_rendimientos_por_mes(id_tercero, tip_tercero, anio):
    rendimientos = HisMovimientos.objects.filter(
        ID_TERCERO=id_tercero,
        TIP_TERCERO=tip_tercero,
        COD_MOVIMIENTO__in=[1,5],
        FEC_REGISTRO__year=anio
    ).annotate(
        mes=ExtractMonth('FEC_REGISTRO')
    ).values('mes').annotate(
        total_rendimientos=Sum('IMP_DEPOSITO')
    ).order_by('mes')

    rend_mes = [0] * 12
    acumulado = 0

    for r in rendimientos:
        mes = r['mes'] - 1
        acumulado += r['total_rendimientos']
        rend_mes[mes] = acumulado

    for i in range(1, 12):
        if rend_mes[i] == 0 and rend_mes[i-1] != 0:
            rend_mes[i] = rend_mes[i-1]

    return rend_mes
#-----------------------------Funcion disponible retiro--------------------------------    
def get_disponible_retiro(id_tercero, tip_tercero):
    # Filtrar los movimientos de tipo 5 para el tercero y tipo de tercero dados
    movimientos = HisMovimientos.objects.filter(
        ID_TERCERO=id_tercero, 
        TIP_TERCERO=tip_tercero, 
        COD_MOVIMIENTO=5
    )
    
    # Sumar el campo IMP_DEPOSITO
    disponible_retiro = movimientos.aggregate(Sum('IMP_DEPOSITO'))['IMP_DEPOSITO__sum']
    
    # Si no hay resultados, devolver 0
    return disponible_retiro if disponible_retiro else 0 
#------------------Funcion para generar reporte-----------------
def generar_reporte_pdf(request):
    user_id = request.session.get('user_id')

    if not user_id:
        return redirect('login')

    try:
        # Obtener datos del usuario y tercero
        usuario = Usuario.objects.get(COD_USUARIO=user_id)
        tercero = CatTerceros.objects.get(COD_USUARIO=usuario)

        movimientos = []
        saldo_acumulado = 0
        suma_depositos = 0
        suma_retiros = 0

        # Obtener parámetros de fecha
        mes = request.GET.get('month')
        año = request.GET.get('year')

        if mes and año:
            start_date = f"{año}-{mes}-01"
            end_date = f"{int(año) + 1}-01-01" if mes == '12' else f"{año}-{str(int(mes) + 1).zfill(2)}-01"

            movimientos = HisMovimientos.objects.filter(
                ID_TERCERO__ID_TERCERO=tercero.ID_TERCERO,
                TIP_TERCERO=tercero.TIP_TERCERO,
                FEC_REGISTRO__gte=start_date,
                FEC_REGISTRO__lt=end_date
            ).select_related('COD_MOVIMIENTO').order_by('FEC_REGISTRO')
        else:
            movimientos = HisMovimientos.objects.filter(
                ID_TERCERO__ID_TERCERO=tercero.ID_TERCERO,
                TIP_TERCERO=tercero.TIP_TERCERO
            ).select_related('COD_MOVIMIENTO').order_by('FEC_REGISTRO')
        # Crear PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="reporte_movimientos_{usuario.COD_USUARIO}.pdf"'
        doc = SimpleDocTemplate(response, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        # ===== ENCABEZADO =====
        logo_path = os.path.join(settings.BASE_DIR, 'tasks', 'static', 'images', 'logo.png')  # ajusta si tu carpeta cambia

        if os.path.exists(logo_path):
            logo = Image(logo_path, width=120, height=50)
        else:
            logo = Paragraph("", styles["Normal"])  # No mostrar nada si no hay logo
        titulo = Paragraph("<b>Reporte de Movimientos</b>", styles["Title"])
        header_data = [[logo, titulo]]
        header_table = Table(header_data, colWidths=[150, 400])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (1, 1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (1, 1), 10),
            ('TOPPADDING', (0, 0), (1, 1), -10),
            ('LEFTPADDING', (0, 0), (1, 1), 40),
            ('RIGHTPADDING', (0, 0), (1, 1), 0),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 20))
        # ===== TABLA PRINCIPAL =====
        data = [["Fecha", "Descripción Movimiento", "Retiro", "Depósito", "Saldo Acumulado"]]
        for mov in movimientos:
            imp_retiro = float(mov.IMP_RETIRO or 0)
            imp_deposito = float(mov.IMP_DEPOSITO or 0)
            if imp_retiro:
                imp_retiro = -abs(imp_retiro)
            saldo_acumulado += imp_deposito + imp_retiro
            suma_depositos += imp_deposito
            suma_retiros += abs(imp_retiro)
            data.append([
                mov.FEC_REGISTRO.strftime('%d-%m-%Y'),
                mov.COD_MOVIMIENTO.DESC_MOVIMIENTO,
                f"${imp_retiro:,.2f}" if imp_retiro else "-",
                f"${imp_deposito:,.2f}" if imp_deposito else "-",
                f"${saldo_acumulado:,.2f}"
            ])
        # Crear tabla de movimientos
        table = Table(data)
        table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), (76/255, 175/255, 80/255)),  # verde encabezado
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
        ]))
        elements.append(table)
        # Construir el PDF
        doc.build(elements)
        return response
    except Usuario.DoesNotExist:
        return redirect('login')
    except CatTerceros.DoesNotExist:
        return HttpResponse("No se encontró información del tercero", status=404)
#Temporal de correo 
logger = logging.getLogger(__name__)
def test_password_reset(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            try:
                # domain_override asegura que no use RequestSite
                form.save(
                    domain_override='127.0.0.1:8000', 
                    use_https=False,
                    from_email='crecetuLana <crecetulanaoficial@gmail.com>'
                )
                logger.info(f"Correo de restablecimiento enviado a: {form.cleaned_data['email']}")
                return HttpResponse("Correo enviado correctamente")
            except Exception as e:
                # Captura cualquier error y lo registra
                logger.error(f"Error al enviar correo de restablecimiento: {str(e)}", exc_info=True)
                return HttpResponse(f"Ocurrió un error al enviar el correo: {str(e)}")
        else:
            logger.warning(f"Formulario inválido: {form.errors}")
            return HttpResponse(f"Formulario inválido: {form.errors}")
    return render(request, 'password_reset.html')

#----------------------------------------------------Configuración del token firmado--------------------------------------------------------------------
signer = TimestampSigner()
TOKEN_TIMEOUT = 1800  # 30 minutos

#--------------------------------------------------------------Usuario envía correo para resetear contraseña-------------------------------------------
def password_reset_request(request):
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            usuario = Usuario.objects.get(CORREO=email)
        except Usuario.DoesNotExist:
            return render(request, "password_reset_sent.html")

        token = signer.sign(usuario.COD_USUARIO)
        reset_url = request.build_absolute_uri(
            reverse("password_reset_confirm", kwargs={"token": token})
        )

        subject = "Restablecimiento de contraseña - crecetuLana"
        from_email = "crecetulanaoficial@gmail.com"
        to = email

        text_content = f"Para restablecer tu contraseña, visita: {reset_url}"
        html_content = render_to_string("emails/password_reset.html", {"reset_url": reset_url, "usuario": usuario})

        msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        return render(request, "password_reset_sent.html")
    return render(request, "password_reset_form.html")
# ----------------------------------------Usuario hace clic en el link del correo---------------------------------------------------------------
def password_reset_confirm(request, token):
    try:
        # Recuperar UID desde el token firmado y validarlo
        uid = signer.unsign(token, max_age=TOKEN_TIMEOUT)
        usuario = Usuario.objects.get(pk=uid)
    except SignatureExpired:
        logger.warning("Token expirado")
        return render(request, "password_reset_invalid.html")
    except (BadSignature, Usuario.DoesNotExist):
        logger.error("Token inválido o usuario no encontrado")
        return render(request, "password_reset_invalid.html")
    # Si el método es POST, actualizar contraseña
    if request.method == "POST":
        p1 = request.POST.get("password1")
        p2 = request.POST.get("password2")
        if p1 != p2:
            return render(request, "password_reset_confirm.html", {
                "error": "Las contraseñas no coinciden."
            })
        # Guardar contraseña (se hashea correctamente)
        usuario.COD_PASS = make_password(p1)
        usuario.save()
        logger.info(f"Contraseña actualizada correctamente para {usuario.CORREO}")
        return redirect("password_reset_complete")
    return render(request, "password_reset_confirm.html")
# ---------------------------------------------Finalización del proceso-------------------------------------------------------
def password_reset_complete(request):
    return render(request, "password_reset_complete.html")
