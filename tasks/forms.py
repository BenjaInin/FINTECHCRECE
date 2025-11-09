from django import forms
from .models import Usuario
from .models import CatTerceros, CatTipMovimientos, Usuario, HisMovimientos
class LoginForm(forms.Form):
    username = forms.CharField(label='Usuario', max_length=255, widget=forms.TextInput(attrs={'placeholder': 'Ingresa tu correo o teléfono'}))
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput(attrs={'placeholder': 'Ingresa tu contraseña'}))

class RegisterForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['COD_USUARIO', 'TIP_USUARIO', 'COD_PERMISOS', 'COD_PASS', 'FEC_ACTUALIZACION', 'MCA_INHABILITADO']

    contraseña_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirma tu contraseña'}))

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('COD_PASS')
        password_confirm = cleaned_data.get('contraseña_confirm')

        if password != password_confirm:
            raise forms.ValidationError('Las contraseñas no coinciden')
        return cleaned_data
    
class MovimientoForm(forms.ModelForm):
    # ID_TERCERO: Select que muestra nombre completo, pero guarda ID_TERCERO
    # Se usa ModelChoiceField con un queryset a todos los terceros
    ID_TERCERO = forms.ModelChoiceField(
        queryset=CatTerceros.objects.all(),
        required=True,
        label='Tercero (Cliente)',
        empty_label="Seleccione el cliente",
        # Usamos el método __str__ del modelo CatTerceros para mostrar el nombre completo
    )
    
    # TIP_TERCERO: Usamos ChoiceField ya que solo son 1 y 2
    TIP_TERCERO_CHOICES = [
        (1, 'Accionista'),
        (2, 'Propietario'),
    ]
    TIP_TERCERO = forms.ChoiceField(
        choices=TIP_TERCERO_CHOICES,
        required=True,
        label='Tipo de Tercero',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    # COD_MOVIMIENTO: Select que muestra DESC_MOVIMIENTO, pero guarda COD_MOVIMIENTO
    COD_MOVIMIENTO = forms.ModelChoiceField(
        queryset=CatTipMovimientos.objects.all(),
        required=True,
        label='Movimiento a Realizar',
        empty_label="Seleccione el tipo de movimiento",
    )

    # Campos de monto (inicialmente no requeridos para la validación del formulario base)
    IMP_RETIRO = forms.DecimalField(
        max_digits=9, 
        decimal_places=2, 
        required=False, 
        label='Importe de Retiro',
        widget=forms.NumberInput(attrs={'placeholder': 'Monto a retirar'})
    )
    IMP_DEPOSITO = forms.DecimalField(
        max_digits=9, 
        decimal_places=2, 
        required=False, 
        label='Importe de Depósito',
        widget=forms.NumberInput(attrs={'placeholder': 'Monto a depositar'})
    )

    class Meta:
        # Usamos HisMovimientos como base, pero sobreescribimos los campos select en el formulario
        model = HisMovimientos
        fields = ['ID_TERCERO', 'TIP_TERCERO', 'COD_MOVIMIENTO', 'IMP_RETIRO', 'IMP_DEPOSITO']
    
    # Lógica de limpieza y validación condicional
    def clean(self):
        cleaned_data = super().clean()
        cod_movimiento = cleaned_data.get('COD_MOVIMIENTO')
        imp_retiro = cleaned_data.get('IMP_RETIRO')
        imp_deposito = cleaned_data.get('IMP_DEPOSITO')
        
        # Si no se seleccionó movimiento, la validación se detiene aquí (los campos ModelChoiceField ya lo validaron)
        if not cod_movimiento:
            return cleaned_data

        # Obtener el tipo de movimiento ('D' o 'R') directamente del objeto seleccionado
        tip_movimiento = cod_movimiento.TIP_MOVIMIENTO
        
        # Validar lógica de Depósito ('D')
        if tip_movimiento == 'D':
            # Debe haber un depósito y el retiro debe ser None o 0
            if not imp_deposito or imp_deposito <= 0:
                self.add_error('IMP_DEPOSITO', 'Este movimiento requiere un importe de depósito positivo.')
            
            # Asegurar que el retiro sea nulo o cero para el insert
            cleaned_data['IMP_RETIRO'] = None

        # Validar lógica de Retiro ('R')
        elif tip_movimiento == 'R':
            # Debe haber un retiro y el depósito debe ser None o 0
            if not imp_retiro or imp_retiro <= 0:
                self.add_error('IMP_RETIRO', 'Este movimiento requiere un importe de retiro positivo.')
            
            # Asegurar que el depósito sea nulo o cero para el insert
            cleaned_data['IMP_DEPOSITO'] = None
            
        # Limpieza de valores (para evitar que se inserten 0.00 en la BD, se prefiere NULL)
        if cleaned_data.get('IMP_RETIRO') == 0:
            cleaned_data['IMP_RETIRO'] = None
        if cleaned_data.get('IMP_DEPOSITO') == 0:
            cleaned_data['IMP_DEPOSITO'] = None

        return cleaned_data
    
   