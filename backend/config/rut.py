"""Validación del RUT chileno (Rol Único Tributario) compartida por todos los módulos.

Acepta las formas habituales de escritura (12.345.678-5, 12345678-5, 123456785, con k minúscula)
y las normaliza a «12345678-5»: sin puntos, con guion y dígito verificador en mayúscula.
"""
import re

from django.core.exceptions import ValidationError

_PATRON = re.compile(r'^(\d{1,8})-?([\dK])$')


def digito_verificador(cuerpo):
    """Calcula el dígito verificador con el algoritmo módulo 11."""
    suma = sum(int(n) * (2 + i % 6) for i, n in enumerate(reversed(str(cuerpo))))
    resto = 11 - suma % 11
    return 'K' if resto == 10 else '0' if resto == 11 else str(resto)


def normalizar_rut(valor):
    """Devuelve el RUT normalizado o lanza ValidationError con un mensaje para el usuario."""
    texto = (valor or '').replace('.', '').replace(' ', '').upper().strip()
    coincidencia = _PATRON.match(texto)
    if not coincidencia:
        raise ValidationError('Ingresa un RUT válido, por ejemplo 12.345.678-5.', code='rut_formato')
    cuerpo, dv = coincidencia.groups()
    cuerpo = cuerpo.lstrip('0')
    if not cuerpo or not 1_000_000 <= int(cuerpo) <= 99_999_999:
        raise ValidationError('El RUT debe tener entre 7 y 8 dígitos antes del guion.', code='rut_largo')
    if digito_verificador(cuerpo) != dv:
        raise ValidationError('El dígito verificador del RUT no coincide.', code='rut_dv')
    return f'{cuerpo}-{dv}'


def es_rut_valido(valor):
    try:
        normalizar_rut(valor)
    except ValidationError:
        return False
    return True


def formatear_rut(valor):
    """Presenta un RUT normalizado con puntos: 12.345.678-5."""
    cuerpo, dv = normalizar_rut(valor).split('-')
    return f'{int(cuerpo):,}'.replace(',', '.') + f'-{dv}'
