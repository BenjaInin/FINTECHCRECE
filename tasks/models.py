from django.db import models
from django.utils import timezone
import uuid

def user_directory_path(instance, filename):
    # Genera nombre único y crea carpeta por usuario
    extension = filename.split('.')[-1]
    filename = f"foto_{uuid.uuid4()}.{extension}"
    return f"fotos_perfil/{instance.COD_USUARIO}/{filename}"


# Modelo para generar acceso.
class Usuario(models.Model):
    COD_USUARIO = models.CharField(max_length=50, unique=True,  primary_key=True)
    TIP_USUARIO = models.CharField(max_length=3)
    CORREO = models.CharField(max_length=50)
    COD_PERMISOS = models.IntegerField()
    COD_PASS = models.CharField(max_length=125)
    FEC_ACTUALIZACION = models.DateField(default=timezone.now)
    MCA_INHABILITADO = models.CharField(max_length=1)
    NUM_TEL = models.CharField(max_length=20, null=True, blank=True) 
    FOTO_PERFIL = models.ImageField(upload_to=user_directory_path,null=True,blank=True)
    def __str__(self):
        return self.COD_USUARIO
    
    class Meta:
        db_table = 'CAT_USUARIOS'  
        managed = True
 
# Modelo para CAT_TERCEROS (Tabla de terceros) 
class CatTerceros(models.Model):
    ID_TERCERO = models.CharField(max_length=5, primary_key=True)
    TIP_TERCERO = models.IntegerField()
    NOM_TERCERO = models.CharField(max_length=70)
    APE_PATERNO = models.CharField(max_length=30, null=True, blank=True)
    APE_MATERNO = models.CharField(max_length=30, null=True, blank=True)
    FEC_ACTUALIZACION = models.DateField(null=True, blank=True)
    MCA_INHABILITADO = models.CharField(max_length=1)
    COD_USUARIO = models.ForeignKey(
        Usuario, 
        on_delete=models.CASCADE, 
        to_field='COD_USUARIO', 
        db_column='COD_USUARIO'  # Esto asegura que Django use 'COD_USUARIO' directamente
    )
    
    def __str__(self):
        return f"{self.NOM_TERCERO} {self.APE_PATERNO} {self.APE_MATERNO}" 
    
    class Meta:
        db_table = 'CAT_TERCEROS'  
        managed = True  

#Modelo para tipo de tercero CAT_TIP_TERCERO
class CatTipoTercero(models.Model):
    TIP_TERCERO = models.IntegerField(primary_key=True)
    DESC_TIP_TERCERO = models.CharField(max_length=50)
    FEC_ACTUALIZACION = models.DateField(null=True, blank=True)
    MCA_INHABILITADO = models.CharField(max_length=1)
    COD_USUARIO = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        to_field='COD_USUARIO',
        db_column='COD_USUARIO'
    )

    def __str__(self):
        return f"{self.TIP_TERCERO} {self.DESC_TIP_TERCERO}"

    class Meta:
        db_table = 'CAT_TIP_TERCEROS'
        managed = True

#Modelo para tipo de movimientos CAT_TIP_MOVIMIENTOS
class CatTipMovimientos(models.Model):
    COD_MOVIMIENTO = models.IntegerField(primary_key=True)
    DESC_MOVIMIENTO = models.CharField(max_length=50)
    TIP_MOVIMIENTO = models.CharField(max_length=1)
    FEC_ACTUALIZACION = models.DateField(null=True, blank=True)
    MCA_INHABILITADO = models.CharField(max_length=1)
    COD_USUARIO = models.ForeignKey(
        Usuario, 
        on_delete=models.CASCADE, 
        to_field='COD_USUARIO', 
        db_column='COD_USUARIO'  # Esto asegura que Django use 'COD_USUARIO' directamente
    )

    def __str__(self):
        return f"{self.COD_MOVIMIENTO} {self.DESC_MOVIMIENTO}"
    class Meta:
        db_table = 'CAT_TIP_MOVIMIENTOS'  
        managed = True  


#Modelo para obtener movimientos HIS_MOVIMIENTOS
class HisMovimientos(models.Model):
    ID = models.AutoField(primary_key=True)  # Nuevo campo auto_incremental
    ID_TERCERO = models.ForeignKey(CatTerceros, on_delete=models.CASCADE, db_column='ID_TERCERO')
    TIP_TERCERO = models.IntegerField()
    COD_MOVIMIENTO = models.ForeignKey(CatTipMovimientos, on_delete=models.CASCADE, db_column='COD_MOVIMIENTO')
    FEC_REGISTRO = models.DateField(null=True, blank=True)
    FEC_ACTUALIZACION = models.DateField(null=True, blank=True)
    IMP_RETIRO = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    IMP_DEPOSITO = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    MCA_INHABILITADO = models.CharField(max_length=1)
    COD_USUARIO = models.ForeignKey(Usuario, on_delete=models.CASCADE, to_field='COD_USUARIO', db_column='COD_USUARIO')

    class Meta:
        db_table = 'HIS_MOVIMIENTOS'  
        managed = True  

    def __str__(self):
        return f"Movimiento {self.COD_MOVIMIENTO.DESC_MOVIMIENTO} - {self.FEC_REGISTRO}"
    
    #Modelo para obtener CAT_TER_USUARIO
class CatTerUsuario(models.Model):
    COD_USUARIO = models.CharField(max_length=50, unique=True,  primary_key=True)
    ID_TERCERO = models.CharField(max_length=5) 
    TIP_TERCERO = models.IntegerField()
    FEC_ACTUALIZACION = models.DateField(null=True, blank=True)
    MCA_INHABILITADO = models.CharField(max_length=1)

    
    class Meta:
        db_table = 'CAT_TER_USUARIO'
        managed = True 
    def __str__(self):
        return f"{self.COD_USUARIO} - {self.ID_TERCERO}"

#Modelo para obtener tipo de cambio dolar
class TipoCambio(models.Model):
    valor = models.DecimalField(max_digits=10, decimal_places=4)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'tipocambio'  # nombre claro y fijo de la tabla
        managed = True 
    def __str__(self):
        return f"{self.valor} ({self.fecha})"
    
#Modelo para insertar datos por excel
class Movimiento(models.Model):
    id = models.AutoField(primary_key=True)  # AUTO_INCREMENT

    id_tercero = models.DateField()
    tip_tercero = models.IntegerField(default=1)

    fec_registro = models.DateField()
    cod_movimiento = models.CharField(max_length=50)

    imp_retiro = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    imp_deposito = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    fec_actualizacion = models.DateField()
    mca_inhabilitado = models.CharField(max_length=1, default='N')

    cod_usuario = models.CharField(max_length=50, default='jagaliciais')
    
    class Meta:
        db_table = 'HIS_MOVIMIENTOS'
        managed = False  # MUY IMPORTANTE
    
    def save(self, *args, **kwargs):
        # FEC_ACTUALIZACION siempre igual a FEC_REGISTRO
        self.fec_actualizacion = self.fec_registro
        super().save(*args, **kwargs)