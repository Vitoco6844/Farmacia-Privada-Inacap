"""Archivos generados por la aplicación, sin dependencia del entorno de Codex."""
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from math import ceil
import re
from xml.sax.saxutils import escape


def texto(valor):
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', str(valor))


def visible(valor):
    if isinstance(valor, datetime):
        return valor.strftime('%d/%m/%Y %H:%M')
    if isinstance(valor, date):
        return valor.strftime('%d/%m/%Y')
    if isinstance(valor, Decimal):
        return f'{valor:,.0f}'.replace(',', '.')
    return texto(valor)


def generar_excel(*, titulo, cabeceras, datos, filtros, generado, usuario, totales, tipo):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    ws = wb.active
    ws.title = {'ventas': 'Ventas', 'inventario': 'Inventario', 'compras': 'Compras'}.get(tipo, 'Historial')
    ancho = len(cabeceras)
    anchos = [14, 22, 16, 42, 12, 18, 20, 24] if tipo == 'ventas' else [16, 48, 27, 17, 17, 14, 29]

    if tipo not in ('ventas', 'inventario'):
        anchos = [24] * ancho

    def escribir(fila, columna, valor):
        celda = ws.cell(fila, columna)
        # Excel solo representa con precisión 15 dígitos significativos.
        if isinstance(valor, (Decimal, int)) and abs(valor) > 999999999999999:
            valor = str(valor)
        if isinstance(valor, str):
            celda.value = texto(valor)
            # Obligar texto incluso si comienza por =, +, -, @ o tabulador.
            celda.data_type = 's'
        else:
            celda.value = valor
        celda.alignment = Alignment(vertical='top', wrap_text=True)
        return celda

    for fila, contenido in [(1, titulo), (2, f'Generado: {generado} · Usuario: {usuario} · Hora Santiago'),
            (3, f'Filtros: {filtros}'), (4, f'Registros: {totales["filas"]} · Envases: {totales["envases"]}')]:
        escribir(fila, 1, contenido)
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=ancho)
    ws['A1'].font = Font(name='Calibri', size=18, bold=True, color='11594B')
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[3].height = 35
    for c, valor in enumerate(cabeceras, 1):
        celda = escribir(6, c, valor)
        celda.fill = PatternFill('solid', fgColor='167461')
        celda.font = Font(bold=True, color='FFFFFF')
    for f, registro in enumerate(datos, 7):
        for c, valor in enumerate(registro, 1):
            celda = escribir(f, c, valor)
            if isinstance(valor, datetime):
                celda.number_format = 'dd/mm/yyyy hh:mm'
            elif isinstance(valor, date):
                celda.number_format = 'dd/mm/yyyy'
            elif isinstance(valor, (Decimal, int)):
                celda.number_format = '#,##0'
            if f % 2 == 0:
                celda.fill = PatternFill('solid', fgColor='F0F6F2')
        lineas = max((max(1, ceil(len(visible(valor)) / (anchos[c] * .85))) for c, valor in enumerate(registro)), default=1)
        ws.row_dimensions[f].height = max(30, lineas * 15)
    final = len(datos) + 8
    escribir(final, 1, 'Total envases')
    escribir(final, 2, totales['envases'])
    if tipo == 'ventas':
        escribir(final + 1, 1, 'Importe de líneas antes de descuentos CLP')
        celda = escribir(final + 1, 2, totales['total'])
        celda.number_format = '#,##0'
    ws.freeze_panes = 'A7'
    ws.auto_filter.ref = f'A6:{get_column_letter(ancho)}{max(6, len(datos) + 6)}'
    for c, valor in enumerate(anchos, 1):
        ws.column_dimensions[get_column_letter(c)].width = valor
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = '1:6'
    ws.oddFooter.center.text = 'Prototipo académico · Página &P de &N'
    salida = BytesIO()
    wb.save(salida)
    return salida.getvalue()


def generar_pdf(*, titulo, cabeceras, datos, filtros, generado, usuario, totales, tipo):
    import reportlab
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    fuente = 'Helvetica'
    fuente_bold = 'Helvetica-Bold'
    carpeta = Path(reportlab.__file__).parent / 'fonts'
    if (carpeta / 'Vera.ttf').exists():
        if 'FarmaciaSans' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('FarmaciaSans', carpeta / 'Vera.ttf'))
            pdfmetrics.registerFont(TTFont('FarmaciaSansBold', carpeta / 'VeraBd.ttf'))
        fuente, fuente_bold = 'FarmaciaSans', 'FarmaciaSansBold'
    estilo = ParagraphStyle('celda', fontName=fuente, fontSize=8, leading=11, alignment=TA_LEFT, wordWrap='CJK')
    encabezado = ParagraphStyle('encabezado', parent=estilo, fontName=fuente_bold, textColor=colors.white)
    titulo_estilo = ParagraphStyle('titulo', parent=estilo, fontName=fuente_bold, fontSize=20, leading=26, textColor=colors.HexColor('#11594B'))
    meta = ParagraphStyle('meta', parent=estilo, fontSize=9, leading=14)

    def parrafo(valor, formato=estilo):
        return Paragraph(escape(visible(valor)), formato)

    salida = BytesIO()
    doc = SimpleDocTemplate(salida, pagesize=landscape(A4), leftMargin=28, rightMargin=28,
        topMargin=30, bottomMargin=35, title=titulo, author=texto(usuario))
    elementos = [parrafo(titulo, titulo_estilo), Spacer(1, 10),
        parrafo(f'Generado: {generado} · Usuario: {usuario} · Hora Santiago', meta),
        parrafo(f'Filtros: {filtros}', meta),
        parrafo(f'Registros: {totales["filas"]} · Envases: {totales["envases"]}' +
            (f' · Importe antes de descuentos: $ {visible(totales["total"])} CLP' if tipo == 'ventas' else ''), meta), Spacer(1, 16)]
    if datos:
        filas = [[parrafo(c, encabezado) for c in cabeceras]] + [[parrafo(v) for v in fila] for fila in datos]
        proporciones = [48, 85, 64, 180, 48, 78, 80, 110] if tipo == 'ventas' else [65, 220, 120, 78, 72, 52, 90]
        if tipo not in ('ventas', 'inventario'):
            proporciones = [1] * len(cabeceras)
        anchos = [doc.width * v / sum(proporciones) for v in proporciones]
        tabla = Table(filas, colWidths=anchos, repeatRows=1, hAlign='LEFT')
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#167461')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0F6F2')]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 7),
            ('RIGHTPADDING', (0, 0), (-1, -1), 7), ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -1), .3, colors.HexColor('#DCE7E0')),
        ]))
        elementos.append(tabla)
    else:
        elementos.append(parrafo('No hay registros para los filtros seleccionados.', meta))

    def pie(canvas, documento):
        canvas.saveState()
        canvas.setFont(fuente, 8)
        canvas.setFillColor(colors.HexColor('#63756B'))
        canvas.drawString(28, 18, 'Farmacia Privada INACAP · Reporte académico, sin validez tributaria')
        canvas.drawRightString(documento.pagesize[0] - 28, 18, f'Página {documento.page}')
        canvas.restoreState()
    doc.build(elementos, onFirstPage=pie, onLaterPages=pie)
    return salida.getvalue()
