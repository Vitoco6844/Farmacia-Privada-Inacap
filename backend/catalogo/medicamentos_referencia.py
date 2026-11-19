"""Precios publicados consultados el 19-10-2026; no se actualizan automáticamente.

Se copia el precio normal/farmacia por envase, no promociones ni membresías.
Los códigos internos y de barras son ficticios. No son identificadores ISP/GTIN.
La condición no corroborada se deja Por verificar y bloquea ventas.
"""
from datetime import date

FECHA_CONSULTA = date(2026, 10, 19)
MEDICAMENTOS = [
    dict(codigo='MED-001', barras='9900000001001', nombre='Paracetamol PHARMARIS',
         presentacion='500 mg · Envase de 16 comprimidos', precio=840, condicion='Venta directa',
         farmacia='Cruz Verde', tipo='Precio normal publicado',
         fuente='https://beta.cruzverde.cl/paracetamol-500-mg-16-comprimidos/272241.html',
         nota='Condición de venta directa contrastada con folleto de paracetamol ISP. Precio normal, no oferta.'),
    dict(codigo='MED-002', barras='9900000001002', nombre='Ibuprofeno Laboratorio Chile',
         presentacion='400 mg · Envase de 20 comprimidos', precio=2199, condicion='Por verificar',
         farmacia='Farmacias Ahumada', tipo='Precio normal publicado',
         fuente='https://www.farmaciasahumada.cl/ibuprofeno-400-mg-x-20-comprimidos-chile-86596.html',
         nota='No se usa el precio Familia Ahumada. Condición pendiente de comprobación para esta presentación.'),
    dict(codigo='MED-003', barras='9900000001003', nombre='Loratadina Laboratorio Chile',
         presentacion='10 mg · Envase de 30 comprimidos', precio=2599, condicion='Por verificar',
         farmacia='Salcobrand', tipo='Precio Farmacia publicado',
         fuente='https://salcobrand.cl/products/labchileloratadina-b-10mg-30-comprimidos?current_store_id=1&default_sku=434912',
         nota='No se usa el precio Internet ni MiSalcobrand. Condición pendiente de comprobación.'),
    dict(codigo='MED-004', barras='9900000001004', nombre='Omeprazol',
         presentacion='20 mg · Envase de 30 cápsulas', precio=3099, condicion='Por verificar',
         farmacia='Salcobrand', tipo='Precio Farmacia publicado',
         fuente='https://salcobrand.cl/products/omeprazol-b-20mg-30-capsulas?default_sku=430270&taxon_id=1600',
         nota='Presentación tomada del título de la ficha. No se usa precio Internet. Condición pendiente.'),
    dict(codigo='MED-005', barras='9900000001005', nombre='Metformina',
         presentacion='850 mg · Envase de 60 comprimidos', precio=5999, condicion='Por verificar',
         farmacia='Salcobrand', tipo='Precio Farmacia publicado',
         fuente='https://salcobrand.cl/products/metformina-b-850mg-60-comprimidos?current_store_id=1&default_sku=435930',
         nota='No se usa precio Internet ni de socios. Condición pendiente de comprobación.'),
    dict(codigo='MED-006', barras='9900000001006', nombre='Aspirina Bayer',
         presentacion='500 mg · Envase de 40 comprimidos', precio=4999, condicion='Venta directa',
         farmacia='Salcobrand', tipo='Precio Farmacia publicado',
         fuente='https://salcobrand.cl/products/aspirina-500mg-40-comprimidos?default_sku=150020&taxon_id=12754',
         nota='La ficha indica venta libre. No se usa precio Internet ni SBPay.'),
]
