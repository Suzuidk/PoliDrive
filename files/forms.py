from django import forms
from django.contrib.auth import password_validation

from .models import Folder, Usuario


class RegForm(forms.ModelForm):
    password1 = forms.CharField(label='Contraseña', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput)

    class Meta:
        model = Usuario
        fields = ('nombre', 'email')

    def clean_email(self):
        em = self.cleaned_data['email'].strip().lower()
        if Usuario.objects.filter(email__iexact=em).exists():
            raise forms.ValidationError('Ya existe una cuenta con ese correo.')
        return em

    def clean(self):
        data = super().clean()
        p1, p2 = data.get('password1'), data.get('password2')
        if p1 and p2:
            if p1 != p2:
                self.add_error('password2', 'Las contraseñas no coinciden.')
            else:
                try:
                    password_validation.validate_password(p1, self.instance)
                except forms.ValidationError as err:
                    self.add_error('password1', err)
        return data

    def save(self, commit=True):
        usr = super().save(commit=False)
        usr.set_password(self.cleaned_data['password1'])  # hash, nunca texto plano
        if commit:
            usr.save()
        return usr


class FoldForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ['name']
        labels = {'name': 'Nombre de la carpeta'}


class ShrForm(forms.Form):
    email = forms.CharField(label='Compartir con (correo del usuario)', max_length=190)
    perm = forms.ChoiceField(
        label='Permiso',
        choices=[('view', 'Solo lectura'), ('edit', 'Lectura y escritura')],
        initial='view',
    )

    def clean_email(self):
        value = self.cleaned_data['email'].strip()
        self.usr = Usuario.objects.filter(email__iexact=value).first()
        if not self.usr:
            raise forms.ValidationError('No existe ningún usuario registrado con ese correo.')
        return value
