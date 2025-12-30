import logging
import bcrypt  # type: ignore
import pandas as pd
from django.db.models import Q
from django.contrib import messages
from .models import Movimiento
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
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from tasks.models import TipoCambio
from django.core.mail import send_mail
from django.urls import reverse
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.timezone import localtime
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import os
import traceback
from decimal import Decimal
from decimal import Decimal, ROUND_HALF_UP
from reportlab.lib.units import cm
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404

# ------------------------------------- FUNCION HOME ----------------------------------------------
def home(request):
    """
    Función que renderiza la página de inicio interactiva (landing page).
    Esta vista no requiere autenticación.
    """
    return render(request, 'home.html')
# ----------------------------------------------CONFIG.HTML---------------------------------------------------------
def config(request):
    return render(request, 'config.html')

#----------------------------------------------PRESTAMO----------------------------------------------

def prestamo(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    usuario = Usuario.objects.get(COD_USUARIO=user_id)
    tercero = CatTerceros.objects.get(COD_USUARIO=usuario)

    inicio_prestamo = get_inicio_prestamo_activo(
        tercero.ID_TERCERO,
        tercero.TIP_TERCERO
    )

    # Seguridad
    if not inicio_prestamo:
        return redirect("dashboard")

    # =========================
    # TOTAL INTERESES PAGADOS
    # =========================
    total_intereses_pagados = (
        HisMovimientos.objects.filter(
            ID_TERCERO__ID_TERCERO=tercero.ID_TERCERO,
            TIP_TERCERO=tercero.TIP_TERCERO,
            FEC_REGISTRO__gte=inicio_prestamo,
            COD_MOVIMIENTO__COD_MOVIMIENTO=3
        ).aggregate(total=Sum('IMP_DEPOSITO'))['total'] or 0
    )

    # =========================
    # TOTAL CAPITAL PAGADO
    # =========================
    total_capital_pagado = (
        HisMovimientos.objects.filter(
            ID_TERCERO__ID_TERCERO=tercero.ID_TERCERO,
            TIP_TERCERO=tercero.TIP_TERCERO,
            FEC_REGISTRO__gte=inicio_prestamo,
            COD_MOVIMIENTO__COD_MOVIMIENTO=4
        ).aggregate(total=Sum('IMP_DEPOSITO'))['total'] or 0
    )

    # =========================
    # TOTAL PRÉSTAMOS
    # =========================
    total_prestamos = (
        HisMovimientos.objects.filter(
            ID_TERCERO__ID_TERCERO=tercero.ID_TERCERO,
            TIP_TERCERO=tercero.TIP_TERCERO,
            FEC_REGISTRO__gte=inicio_prestamo,
            COD_MOVIMIENTO__COD_MOVIMIENTO=2
        ).aggregate(total=Sum('IMP_RETIRO'))['total'] or 0
    )

    # =========================
    # TOTAL INTERESES DEL PRÉSTAMO
    # =========================
    total_intereses_prestamo = (
        HisMovimientos.objects.filter(
            ID_TERCERO__ID_TERCERO=tercero.ID_TERCERO,
            TIP_TERCERO=tercero.TIP_TERCERO,
            FEC_REGISTRO__gte=inicio_prestamo,
            COD_MOVIMIENTO__COD_MOVIMIENTO=6
        ).aggregate(total=Sum('IMP_RETIRO'))['total'] or 0
    )

    # =========================
    # TOTALES
    # =========================
    total_pagado = total_intereses_pagados + total_capital_pagado
    total_credito = total_prestamos + total_intereses_prestamo
    saldo_total_pendiente = total_credito - total_pagado

    progreso_pago = round((total_pagado / total_credito) * 100, 2) if total_credito else 0
    progreso_pago = min(progreso_pago, 100)

    # =========================
    # MOVIMIENTOS
    # =========================
    movimientos = HisMovimientos.objects.filter(
        ID_TERCERO__ID_TERCERO=tercero.ID_TERCERO,
        TIP_TERCERO=tercero.TIP_TERCERO,
        FEC_REGISTRO__gte=inicio_prestamo,
        COD_MOVIMIENTO__COD_MOVIMIENTO__in=[2, 3, 4, 6]
    ).select_related('COD_MOVIMIENTO').order_by('-FEC_REGISTRO')

    lista_pagos = []
    for mov in movimientos:
        monto = float(mov.IMP_DEPOSITO or mov.IMP_RETIRO or 0)
        lista_pagos.append({
            'fecha': mov.FEC_REGISTRO,
            'descripcion': mov.COD_MOVIMIENTO.DESC_MOVIMIENTO,
            'pago': monto,
            'estado': 'PROCESADO'
        })
        
    
    # =========================
    # PRÓXIMA FECHA DE PAGO
    # =========================

    proxima_fecha_pago = get_proxima_fecha_pago(
        tercero.ID_TERCERO,
        tercero.TIP_TERCERO
    )

    # =========================
    # RENDER
    # =========================
    return render(request, "prestamo.html", {
        "saldo_total_pendiente": saldo_total_pendiente,
        "total_prestamos": total_prestamos,
        "total_intereses_prestamo": total_intereses_prestamo,
        "total_intereses_pagados": total_intereses_pagados,
        "total_capital_pagado": total_capital_pagado,
        "total_credito": total_credito,
        "total_pagado": total_pagado,
        "progreso_pago": progreso_pago,
        "lista_pagos": lista_pagos,
        "proxima_fecha_pago": proxima_fecha_pago,
    })
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
    # Limpiar mensajes pendientes
    list(messages.get_messages(request))

    terceros = CatTerceros.objects.all().order_by('NOM_TERCERO')
    movimientos = CatTipMovimientos.objects.all()
    tiptercero = CatTipoTercero.objects.all()

    # -----------------------------
    # POST
    # -----------------------------
    if request.method == 'POST':

        # =====================================================
        # 🟢 CARGA MASIVA DESDE EXCEL
        # =====================================================
        if request.FILES.get('archivo'):
            archivo = request.FILES['archivo']

            try:
                df = pd.read_excel(archivo, dtype={'id_tercero': str})

                user_id = request.session.get('user_id')
                usuario = Usuario.objects.get(COD_USUARIO=user_id)

                with transaction.atomic():
                    for index, fila in df.iterrows():
                        imp_retiro = None
                        imp_deposito = None

                        if not pd.isna(fila['imp_retiro']):
                            imp_retiro = fila['imp_retiro']

                        if not pd.isna(fila['imp_deposito']):
                            imp_deposito = fila['imp_deposito']
                         # 🔹 Limpiar y formatear ID_TERCERO

                        id_tercero = str(fila['id_tercero']).strip().zfill(5)

# 🔹 Buscar tercero usando filter + first
                        tercero = CatTerceros.objects.filter(ID_TERCERO=id_tercero).first()
                        if not tercero:
                            messages.warning(request, f"No existe el tercero: '{id_tercero}'")
                            continue  # Salta esta fila
                    
                        # 🔹 Buscar código de movimiento usando filter + first
                        cod_mov = CatTipMovimientos.objects.filter(COD_MOVIMIENTO=fila['cod_movimiento']).first()
                        if not cod_mov:
                            messages.warning(request, f"No existe el código de movimiento: '{fila['cod_movimiento']}'")
                            continue  # saltar esta fila

                        # FK
                        tercero = CatTerceros.objects.get(ID_TERCERO=fila['id_tercero'])
                        cod_mov = CatTipMovimientos.objects.get(
                            COD_MOVIMIENTO=fila['cod_movimiento']
                        )

                        HisMovimientos.objects.create(
                            ID_TERCERO=tercero,
                            TIP_TERCERO=1,
                            COD_MOVIMIENTO=cod_mov,
                            FEC_REGISTRO=fila['fec_registro'],
                            FEC_ACTUALIZACION=fila['fec_registro'],
                            IMP_RETIRO=imp_retiro,
                            IMP_DEPOSITO=imp_deposito,
                            MCA_INHABILITADO='N',
                            COD_USUARIO=usuario
                        )

                messages.success(request, "Archivo Excel cargado correctamente")
                return redirect('registro')

            except Exception as e:
                traceback.print_exc()
                messages.error(request, f"Error al cargar Excel: {e}")

        # =====================================================
        # 🔵 REGISTRO MANUAL
        # =====================================================
        else:
            try:
                id_tercero_id = request.POST.get('ID_TERCERO')
                cod_movimiento_id = request.POST.get('COD_MOVIMIENTO')
                imp_retiro = request.POST.get('IMP_RETIRO') or None
                imp_deposito = request.POST.get('IMP_DEPOSITO') or None

                fecha_registro = datetime.strptime(
                    request.POST.get('FEC_REGISTRO'),
                    '%Y-%m-%d'
                ).date()

                user_id = request.session.get('user_id')
                usuario = Usuario.objects.get(COD_USUARIO=user_id)

                tercero = CatTerceros.objects.get(ID_TERCERO=id_tercero_id)
                cod_movimiento = CatTipMovimientos.objects.get(
                    COD_MOVIMIENTO=cod_movimiento_id
                )

                HisMovimientos.objects.create(
                    ID_TERCERO=tercero,
                    TIP_TERCERO=1,
                    COD_MOVIMIENTO=cod_movimiento,
                    FEC_REGISTRO=fecha_registro,
                    FEC_ACTUALIZACION=timezone.now().date(),
                    IMP_RETIRO=imp_retiro,
                    IMP_DEPOSITO=imp_deposito,
                    MCA_INHABILITADO='N',
                    COD_USUARIO=usuario
                )

                messages.success(request, "Movimiento registrado correctamente")
                return redirect('registro')

            except Exception as e:
                messages.error(request, f"Error al registrar movimiento: {e}")

    # -----------------------------
    # GET
    # -----------------------------
    return render(request, 'registro.html', {
        'terceros': terceros,
        'movimientos': movimientos,
        'tiptercero': tiptercero
    })
#-----------------------------------------Usuarios------------------------------------------------------------------------
def usuarios_view(request):
    query = request.GET.get('q', '')
    usuarios = CatTerceros.objects.select_related('COD_USUARIO')
    if query:
        usuarios = usuarios.filter(
            Q(NOM_TERCERO__icontains=query) |
            Q(APE_PATERNO__icontains=query) |
            Q(APE_MATERNO__icontains=query) |
            Q(COD_USUARIO__CORREO__icontains=query)
        )

    context = {
        'usuarios': usuarios,
        'total_usuarios': usuarios.count(),
        'usuarios_activos': usuarios.filter(MCA_INHABILITADO='N').count(),
        'usuarios_inactivos': usuarios.filter(MCA_INHABILITADO='S').count(),
        'query' :query
    }

    return render(request, 'usuarios.html', context)

def movimientos_usuario(request, id_tercero):
    """
    Devuelve los movimientos de un tercero en formato JSON
    para mostrar en el modal.
    Funciona tanto si el ID viene con ceros a la izquierda como sin ellos.
    """

    # Convertimos a string y generamos versión con ceros a la izquierda
    id_tercero_str = str(id_tercero)
    id_tercero_zfill = id_tercero_str.zfill(5)  # Por ejemplo, '2' -> '00002'

    # Filtramos movimientos por ambos posibles formatos
    movimientos = HisMovimientos.objects.filter(
        ID_TERCERO__ID_TERCERO__in=[id_tercero_str, id_tercero_zfill]
    ).order_by('FEC_REGISTRO')

    # Convertimos el queryset a lista de diccionarios
    data = []
    for m in movimientos:
        data.append({
            'id': m.ID,
            'id_tercero': m.ID_TERCERO.ID_TERCERO,
            'fecha': m.FEC_REGISTRO.strftime('%Y-%m-%d') if m.FEC_REGISTRO else '',
            'concepto': m.COD_MOVIMIENTO.DESC_MOVIMIENTO,
            'deposito': float(m.IMP_DEPOSITO) if m.IMP_DEPOSITO else 0,
            'retiro': float(m.IMP_RETIRO) if m.IMP_RETIRO else 0
        })

    return JsonResponse(data, safe=False)
@require_POST
def eliminar_movimiento(request, id):
    mov = get_object_or_404(HisMovimientos, ID=id)
    mov.delete()
    return JsonResponse({'ok': True})

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
            
            # Tasa promedio
            tasa_promedio = get_tasa_promedio(tercero.ID_TERCERO, tercero.TIP_TERCERO)


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
                'tasa_promedio': tasa_promedio,

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
     # Limpia mensajes anteriores
    list(messages.get_messages(request))

    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    try:
        # =========================
        # USUARIO LOGUEADO
        # =========================
        usuario = Usuario.objects.get(COD_USUARIO=user_id)
        tercero_usuario = CatTerceros.objects.get(COD_USUARIO=usuario)

        # Para select (admin)
        terceros = CatTerceros.objects.all()

        # Por defecto: el propio usuario
        id_tercero = tercero_usuario.ID_TERCERO
        tip_tercero = tercero_usuario.TIP_TERCERO
        nombre_completo = f"{tercero_usuario.NOM_TERCERO} {tercero_usuario.APE_PATERNO} {tercero_usuario.APE_MATERNO}"

        # =========================
        # ADMIN: captura selección
        # =========================
        if request.method == 'POST' and usuario.COD_PERMISOS == 99:
            id_tercero = request.POST.get('id_tercero')
            try:
                tercero_seleccionado = CatTerceros.objects.get(ID_TERCERO=id_tercero)
                tip_tercero = tercero_seleccionado.TIP_TERCERO
                nombre_completo = f"{tercero_seleccionado.NOM_TERCERO} {tercero_seleccionado.APE_PATERNO} {tercero_seleccionado.APE_MATERNO}"
            except CatTerceros.DoesNotExist:
                nombre_completo = "Usuario no encontrado"
                tip_tercero = None

        # =========================
        # MOVIMIENTOS
        # =========================
        movimientos = HisMovimientos.objects.filter(
            ID_TERCERO__ID_TERCERO=id_tercero,
            TIP_TERCERO=tip_tercero
        ).select_related('COD_MOVIMIENTO').order_by('FEC_REGISTRO')

        # =========================
        # VARIABLES DE CONTROL
        # =========================
        saldo_acumulado = 0
        suma_depositos = 0
        suma_retiros = 0
        sumatorias_por_tipo = {}
        prestamo_por_liquidar = 0

        # =========================
        # PROCESAMIENTO
        # =========================
        suma_prestamo = 0        # para COD_MOVIMIENTO 2
        suma_pago_capital = 0    # para COD_MOVIMIENTO 4
        prestamo_por_liquidar = 0

        for mov in movimientos:
            imp_deposito = float(mov.IMP_DEPOSITO or 0)
            imp_retiro = float(mov.IMP_RETIRO or 0)

            saldo_mov = imp_deposito - imp_retiro
            saldo_acumulado += saldo_mov
            mov.saldo_acumulado = saldo_acumulado

            suma_depositos += imp_deposito
            suma_retiros += imp_retiro

            tipo_movimiento = mov.COD_MOVIMIENTO.DESC_MOVIMIENTO
            cod_movimiento = mov.COD_MOVIMIENTO.COD_MOVIMIENTO

            # ------------------------------
            # OMITIMOS agregar PRESTAMO a sumatorias_por_tipo dentro del bucle
            # ------------------------------
            if tipo_movimiento != 'PRESTAMO':  
                sumatorias_por_tipo[tipo_movimiento] = (
                    sumatorias_por_tipo.get(tipo_movimiento, 0)
                    + abs(imp_deposito)
                    + abs(imp_retiro)
                )

            # ------------------------------
            # PRÉSTAMO POR LIQUIDAR (POSITIVO)
            # ------------------------------
            if tipo_movimiento == 'PRESTAMO':
                prestamo_por_liquidar += imp_retiro
                suma_prestamo += imp_retiro  # para el cálculo final
            elif tipo_movimiento == 'PAG.CAPIT.PREST.':
                prestamo_por_liquidar -= imp_deposito
                suma_pago_capital += imp_deposito  # para el cálculo final

        # ------------------------------
        # ASIGNAR LOS RESULTADOS
        # ------------------------------
        sumatorias_por_tipo['PRESTAMO PARA LIQUIDAR'] = prestamo_por_liquidar
        sumatorias_por_tipo['PRESTAMO'] = suma_prestamo - suma_pago_capital

        now = timezone.now()
        # ORDEN DE CONCEPTOS
        orden_conceptos = [
            'DEPOSITO AHORR.',
            'PRESTAMO',
            'INTER.PRESTAMO',
            'PAG.INTE.PREST.',
            'PAG.CAPIT.PREST.',
            'RENDIMIENTO DEL PERIODO',
            'PRESTAMO PARA LIQUIDAR'
        ]

        sumatorias_ordenadas = {}

        for concepto in orden_conceptos:
            if concepto in sumatorias_por_tipo:
                sumatorias_ordenadas[concepto] = sumatorias_por_tipo[concepto]

        # Reemplazamos el original
        sumatorias_por_tipo = sumatorias_ordenadas

        # =========================
        # RENDER
        # =========================
        return render(request, 'lista_movimientos.html', {
            'usuario': usuario,
            'nombre_completo': nombre_completo,
            'movimientos': movimientos,
            'sumatorias_por_tipo': sumatorias_por_tipo,
            'saldo_total': saldo_acumulado,
            'suma_depositos': suma_depositos,
            'suma_retiros': suma_retiros,
            'saldo_acumulado': saldo_acumulado,
            'terceros': terceros,
            'selected_id_tercero': id_tercero,
            'selected_tip_tercero': tip_tercero,
            'now': now
        })

    except Usuario.DoesNotExist:
        return redirect('login')
    except CatTerceros.DoesNotExist:
        return render(
            request,
            'lista_movimientos.html',
            {'error': 'No se encontró información del tercero.'}
        )
#-------------------------------------Saldo prestamo -------------------------------------------------------------#
def get_saldo_prestamo(id_tercero, tip_tercero):
    """
    Retorna el saldo REAL del préstamo:
    (Préstamo + Intereses) - (Pagos de interés + Pagos a capital)
    """

    # Cargos (lo que incrementa la deuda)
    # CARGOS → lo que genera deuda
    total_prestamo = HisMovimientos.objects.filter(
        ID_TERCERO__ID_TERCERO=id_tercero,
        TIP_TERCERO=tip_tercero,
        COD_MOVIMIENTO__COD_MOVIMIENTO__in=[2, 6]  # PRÉSTAMO + INTERÉS
    ).aggregate(total=Sum('IMP_RETIRO'))['total'] or Decimal('0')

    # ABONOS → lo que paga deuda
    total_pagos = HisMovimientos.objects.filter(
        ID_TERCERO__ID_TERCERO=id_tercero,
        TIP_TERCERO=tip_tercero,
        COD_MOVIMIENTO__COD_MOVIMIENTO__in=[3, 4]  # PAGOS
    ).aggregate(total=Sum('IMP_DEPOSITO'))['total'] or Decimal('0')

    saldo = Decimal(total_prestamo) - Decimal(total_pagos)

    # Si ya está liquidado → no mostrar
    if saldo <= 0:
        return Decimal('0.00')

    return saldo.quantize(Decimal('0.00'))
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
#-------------------------------------Funcion disponible retiro-----------------------------------------------    
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
#------------------------------------------Funcion para generar reporte-------------------------------------
def dibujar_marco(canvas, doc):
    canvas.saveState()
    
    ancho, alto = letter
    
    margen = 18  # espacio entre el borde y el marco
    canvas.setStrokeColor(colors.HexColor('#0B2C4A'))  # azul marino
    canvas.setLineWidth(3)

    canvas.rect(
        margen,
        margen,
        ancho - margen*2,
        alto - margen*2
    )

    canvas.restoreState()
    
def dibujar_encabezado(canvas, doc):
    width, height = letter

    logo_path = os.path.join(settings.BASE_DIR, 'tasks', 'static', 'images', 'logo.png')

    if os.path.exists(logo_path):
        # Posición: esquina inferior izquierda del encabezado
        canvas.drawImage(
            logo_path,
            1.5 * cm,                # X
            height - 3.5 * cm,         # Y
            width=4 * cm,
            preserveAspectRatio=True,
            mask='auto'
        )

def generar_reporte_pdf(request):

    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    try:
        # =================== OBTENER USUARIO Y TERCERO ===================
        usuario = Usuario.objects.get(COD_USUARIO=user_id)

        # Revisar si se envió un tercero por GET (solo admin)
        id_tercero_get = request.GET.get('id_tercero')

        if usuario.COD_PERMISOS == 99 and id_tercero_get:  # admin seleccionando otro usuario
            try:
                tercero = CatTerceros.objects.get(ID_TERCERO=id_tercero_get)
            except CatTerceros.DoesNotExist:
                return HttpResponse("Usuario seleccionado no existe")
        else:
            tercero = CatTerceros.objects.get(COD_USUARIO=usuario)

        nombre_completo = f"{tercero.NOM_TERCERO} {tercero.APE_PATERNO} {tercero.APE_MATERNO}"

        # =================== FILTRO FECHA ===================
        # Parámetros GET para rango de fechas
        # Fecha de emisión
        fecha_emision = timezone.now().strftime('%d-%m-%Y')
        mes_inicio = request.GET.get('month_start')
        año_inicio = request.GET.get('year_start')
        mes_fin = request.GET.get('month_end')
        año_fin = request.GET.get('year_end')

        if mes_inicio and año_inicio:
            start_date = f"{año_inicio}-{mes_inicio}-01"

            # Si mes_fin y año_fin existen Y son diferentes al inicio
            if mes_fin and año_fin and (mes_fin != mes_inicio or año_fin != año_inicio):
                end_date = f"{año_fin}-{mes_fin}-01"
                # Ajustar para incluir todo el mes final
                end_date = (datetime.strptime(end_date, "%Y-%m-%d") + relativedelta(months=1)).strftime("%Y-%m-%d")
            else:
                # Solo un mes
                end_date = f"{año_inicio}-{str(int(mes_inicio)+1).zfill(2)}-01" if mes_inicio != '12' else f"{int(año_inicio)+1}-01-01"

            movimientos = HisMovimientos.objects.filter(
                ID_TERCERO__ID_TERCERO=tercero.ID_TERCERO,
                TIP_TERCERO=tercero.TIP_TERCERO,
                FEC_REGISTRO__gte=start_date,
                FEC_REGISTRO__lt=end_date
            ).select_related('COD_MOVIMIENTO').order_by('FEC_REGISTRO')


        if not movimientos:
            return HttpResponse("No hay movimientos")

        saldo_acumulado = 0
        suma_depositos = 0
        suma_retiros = 0
        sumatorias_por_tipo = {}

        for mov in movimientos:
            dep = float(mov.IMP_DEPOSITO or 0)
            ret = float(mov.IMP_RETIRO or 0)

            saldo_acumulado += dep - ret
            suma_depositos += dep
            suma_retiros += ret

            tipo = mov.COD_MOVIMIENTO.DESC_MOVIMIENTO
            sumatorias_por_tipo[tipo] = sumatorias_por_tipo.get(tipo, 0) + dep + ret

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Estado_de_cuenta_{tercero.NOM_TERCERO} {tercero.APE_PATERNO} {tercero.APE_MATERNO}_{fecha_emision}.pdf"'

        doc = SimpleDocTemplate(response, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # =================== TITULO ===================
        titulo = Paragraph(f"<b>Estado de Cuenta</b><br/>{nombre_completo}", styles['Title'])
        
        elements.append(titulo)
        elements.append(Spacer(1, 15))

        # =================== BLOQUE SUPERIOR ===================
        periodo = f"{movimientos.first().FEC_REGISTRO:%d-%m-%Y} al {movimientos.last().FEC_REGISTRO:%d-%m-%Y}"
        fecha_emision = timezone.now().strftime('%d-%m-%Y')

        info = [
            [Paragraph(f"<b>Periodo:</b> {periodo}", styles['Normal'])],
            [Paragraph(f"<b>Fecha de consulta:</b> {fecha_emision}", styles['Normal'])]
        ]

        info_table = Table(info, colWidths=[300])
        
        info_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),       # Centra el texto dentro
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (3,3), (-1,-1), 6),
        ]))

        # Contenedor para centrar la tabla en la página
        info_container = Table([[info_table]], colWidths=[500])
        info_container.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))

        elements.append(info_container)
        elements.append(Spacer(1, 14))

        resumen_data = [["Concepto", "Importe"]]
        for k, v in sumatorias_por_tipo.items():
            resumen_data.append([k, f"${v:,.2f}"])

        resumen_data += [
            ["Total depósitos", f"${suma_depositos:,.2f}"],
            ["Total retiros", f"${suma_retiros:,.2f}"],
            ["Saldo final", f"${saldo_acumulado:,.2f}"]
        ]

        resumen_table = Table(resumen_data, colWidths=[160, 100])

        style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4CAF50')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ])

        for i in range(1, len(resumen_data)):
            style.add('BACKGROUND', (0,i), (-1,i), colors.HexColor('#bef2d4') if i%2==0 else colors.white)

        style.add('FONTNAME', (0, len(resumen_data)-3), (-1, len(resumen_data)-1), 'Helvetica-Bold')
        resumen_table.setStyle(style)

        bloque = Table([[ resumen_table]], colWidths=[300, 260])
        elements.append(bloque)
        elements.append(Spacer(1, 20))

        # =================== TABLA MOVIMIENTOS ===================
        data = [["Fecha", "Concepto", "Retiros", "Depósitos", "Saldo"]]
        saldo_temp = 0

        for mov in movimientos:
            ret = float(mov.IMP_RETIRO or 0)
            dep = float(mov.IMP_DEPOSITO or 0)
            saldo_temp += dep - ret

            data.append([
                mov.FEC_REGISTRO.strftime('%d-%m-%Y'),
                mov.COD_MOVIMIENTO.DESC_MOVIMIENTO,
                f"${ret:,.2f}" if ret else "-",
                f"${dep:,.2f}" if dep else "-",
                f"${saldo_temp:,.2f}"
            ])

        tabla = Table(data, colWidths=[120, 200, 80, 80, 80])

        style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4CAF50')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DDDDDD')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER')
        ])

        for i in range(1, len(data)):
            style.add('BACKGROUND', (0,i), (-1,i), colors.HexColor('#bef2d4') if i%2==0 else colors.white)

        tabla.setStyle(style)
        elements.append(tabla)

        doc.build(
            elements,
            onFirstPage=lambda c, d: (dibujar_marco(c, d), dibujar_encabezado(c, d)),
            onLaterPages=lambda c, d: (dibujar_marco(c, d), dibujar_encabezado(c, d)),
        )

        return response

    except:
        return redirect('login')


#--------------------------------------------Temporal de correo----------------------------------------------- 
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
#-----------------------------Funcion fecha proximo pago-----------------------------------------------------------------------------------
def get_proxima_fecha_pago(id_tercero, tip_tercero):
    """
    Retorna la próxima fecha de pago del crédito activo.
    Si el crédito está liquidado, retorna None.
    """

    # =========================
    # 1️⃣ FECHA DEL PRÉSTAMO
    # =========================
     # 🔎 1. Detectar inicio del préstamo activo
    prestamo = (
        HisMovimientos.objects.filter(
            ID_TERCERO__ID_TERCERO=id_tercero,
            TIP_TERCERO=tip_tercero,
            COD_MOVIMIENTO__COD_MOVIMIENTO=2
        ).order_by('-FEC_REGISTRO').first()
    )

    if not prestamo:
        return None

    inicio_prestamo = prestamo.FEC_REGISTRO

    # 💰 2. Calcular saldo solo del préstamo activo
    cargos = HisMovimientos.objects.filter(
        ID_TERCERO__ID_TERCERO=id_tercero,
        TIP_TERCERO=tip_tercero,
        FEC_REGISTRO__gte=inicio_prestamo,
        COD_MOVIMIENTO__COD_MOVIMIENTO__in=[2, 6]
    ).aggregate(total=Sum('IMP_RETIRO'))['total'] or 0

    pagos = HisMovimientos.objects.filter(
        ID_TERCERO__ID_TERCERO=id_tercero,
        TIP_TERCERO=tip_tercero,
        FEC_REGISTRO__gte=inicio_prestamo,
        COD_MOVIMIENTO__COD_MOVIMIENTO__in=[3, 4]
    ).aggregate(total=Sum('IMP_DEPOSITO'))['total'] or 0

    if cargos - pagos <= 0:
        return None  # préstamo ya liquidado

    # 📅 3. Calcular próxima fecha de pago
    fecha_base = inicio_prestamo + relativedelta(months=1) + timedelta(days=1)

    return fecha_base
# -------------------------------------Vista para cargar en excel-------------------------------------
COLUMNAS_REQUERIDAS = {
    'id_tercero',
    'fec_registro',
    'cod_movimiento',
    'imp_retiro',
    'imp_deposito',
}

def cargar_excel(request):
    if request.method == 'POST':
        if 'archivo' not in request.FILES:
            return render(request, 'registro.html', {
                'error': 'No se recibió el archivo'
            })

        archivo = request.FILES['archivo']

        try:
            df = pd.read_excel(archivo, dtype={'id_tercero': str})
            print(df.head())

            with transaction.atomic():
                for index, fila in df.iterrows():
                    print("Procesando fila:", fila.to_dict())

                    imp_retiro = None
                    imp_deposito = None

                    if not pd.isna(fila['imp_retiro']):
                        imp_retiro = fila['imp_retiro']

                    if not pd.isna(fila['imp_deposito']):
                        imp_deposito = fila['imp_deposito']
                    
                    # 🔹 Limpiar y formatear ID_TERCERO
                    id_tercero = str(fila['id_tercero']).strip().zfill(5)

                    # 🔹 Buscar tercero usando filter + first para evitar errores
                    tercero = CatTerceros.objects.filter(ID_TERCERO=id_tercero).first()
                    if not tercero:
                        messages.warning(request, f"No existe el tercero: '{id_tercero}'")
                        continue  # Salta esta fila
                    
                    Movimiento.objects.create(
                        id_tercero=fila['id_tercero'],
                        fec_registro=fila['fec_registro'],
                        cod_movimiento=fila['cod_movimiento'],
                        imp_retiro=imp_retiro,
                        imp_deposito=imp_deposito,
                    )

            return render(request, 'registro.html', {
                'mensaje': 'Archivo cargado correctamente'
            })

        except Exception as e:
            traceback.print_exc()
            return render(request, 'registro.html', {
                'error': str(e)
            })

    return render(request, 'registro.html')

#----------------------OBTENER EL INICIO DEL PRESTAMO -----------------------------------------------
def get_inicio_prestamo_activo(id_tercero, tip_tercero):

    ultimo_prestamo = (
        HisMovimientos.objects.filter(
            ID_TERCERO__ID_TERCERO=id_tercero,
            TIP_TERCERO=tip_tercero,
            COD_MOVIMIENTO__COD_MOVIMIENTO=2
        )
        .order_by('-FEC_REGISTRO')
        .first()
    )

    return ultimo_prestamo.FEC_REGISTRO if ultimo_prestamo else None
#----------------------------------------Funcion Tasa Promedio ------------------------------------------
def get_tasa_promedio(id_tercero, tip_tercero):
    # Total ahorrado
    total_ahorro = HisMovimientos.objects.filter(
        ID_TERCERO__ID_TERCERO=id_tercero,
        TIP_TERCERO=tip_tercero,
        COD_MOVIMIENTO__COD_MOVIMIENTO=1
    ).aggregate(total=Sum('IMP_DEPOSITO'))['total'] or 0

    total_rendimiento = HisMovimientos.objects.filter(
        ID_TERCERO__ID_TERCERO=id_tercero,
        TIP_TERCERO=tip_tercero,
        COD_MOVIMIENTO__COD_MOVIMIENTO=5
    ).aggregate(total=Sum('IMP_DEPOSITO'))['total'] or 0

    if total_ahorro <= 0:
        return 0

    tasa = (total_rendimiento / total_ahorro) * 100
    return round(tasa, 2)
