from django.db import models

# Modelo para generar acceso.
class Usuario(models.Model):
    COD_USUARIO = models.CharField(max_length=50, unique=True,  primary_key=True)
    TIP_USUARIO = models.CharField(max_length=3)
    CORREO = models.CharField(max_length=50)
    COD_PERMISOS = models.IntegerField()
    COD_PASS = models.CharField(max_length=125)
    FEC_ACTUALIZACION = models.DateField(max_length=50)
    MCA_INHABILITADO = models.CharField(max_length=1)
    NUM_TEL = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.COD_USUARIO
    
    class Meta:
        db_table = 'CAT_USUARIOS'  
        managed = False
 
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
        managed = False  # Si no quieres que Django gestione la tabla

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
        managed = False

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
        managed = False  # Si no quieres que Django gestione la tabla


#Modelo para obtener movimientos HIS_MOVIMIENTOS
class HisMovimientos(models.Model):
    id = models.AutoField(primary_key=True)  # Nuevo campo auto_incremental
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
        unique_together = (
            'ID_TERCERO', 'TIP_TERCERO', 'COD_MOVIMIENTO', 'FEC_REGISTRO', 'FEC_ACTUALIZACION'
        )
        managed = False  # Django no gestionará la tabla

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
        managed = False  # Django no gestionará la tabla
    def __str__(self):
        return f"{self.COD_USUARIO} - {self.ID_TERCERO}"