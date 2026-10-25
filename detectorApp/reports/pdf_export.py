import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    HRFlowable,
)
from django.conf import settings
from django.contrib.staticfiles import finders


# ---------------------------------------------------------------------------
# Palette — mêmes tokens que STYLE_GUIDE.md, pour rester cohérent avec le web
# ---------------------------------------------------------------------------
NAVY = colors.HexColor('#1E3A5F')
TEXT_PRIMARY = colors.HexColor('#1B2430')
TEXT_SECONDARY = colors.HexColor('#5B6472')
BORDER = colors.HexColor('#E3E6EB')
SUCCESS = colors.HexColor('#15803D')
SUCCESS_BG = colors.HexColor('#DCFCE7')
DANGER = colors.HexColor('#B91C1C')
DANGER_BG = colors.HexColor('#FEE2E2')
WARNING = colors.HexColor('#B45309')
WARNING_BG = colors.HexColor('#FEF3C7')
PAGE_BG = colors.HexColor('#F7F8FA')


def _styles():
    base = getSampleStyleSheet()
    return {
        'title': ParagraphStyle('Title', parent=base['Title'], fontSize=17,
            spaceAfter=2, alignment=TA_CENTER, textColor=NAVY,
            fontName='Helvetica-Bold'),
        'subtitle': ParagraphStyle('Subtitle', parent=base['Normal'],
            fontSize=8.5, alignment=TA_CENTER, textColor=TEXT_SECONDARY),
        'section': ParagraphStyle('Section', parent=base['Heading2'],
            fontSize=11.5, spaceBefore=10, spaceAfter=4,
            textColor=TEXT_PRIMARY, fontName='Helvetica-Bold'),
        'stat_number': ParagraphStyle('StatNum', parent=base['Normal'],
            fontSize=20, leading=24, fontName='Helvetica-Bold',
            alignment=TA_CENTER, textColor=TEXT_PRIMARY),
        'stat_label': ParagraphStyle('StatLabel', parent=base['Normal'],
            fontSize=7.5, alignment=TA_CENTER, textColor=TEXT_SECONDARY,
            fontName='Helvetica'),
        'cell': ParagraphStyle('Cell', parent=base['Normal'], fontSize=8.5,
            textColor=TEXT_PRIMARY, leading=11),
        'cell_center': None,  # set below (depends on 'cell')
        'header': ParagraphStyle('Header', parent=base['Normal'], fontSize=8,
            fontName='Helvetica-Bold', textColor=colors.white,
            alignment=TA_CENTER),
        'empty': ParagraphStyle('Empty', parent=base['Normal'], fontSize=9,
            textColor=TEXT_SECONDARY, alignment=TA_CENTER,
            fontName='Helvetica-Oblique'),
        'footer': ParagraphStyle('Footer', parent=base['Normal'], fontSize=7,
            textColor=colors.HexColor('#8A93A3'), alignment=TA_CENTER),
    }


def _page_decoration(canvas, doc):
    """En-tête discret + pied de page avec numérotation, sur chaque page."""
    canvas.saveState()
    width, height = A4

    # Ligne fine en pied de page + numéro
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(20 * mm, 14 * mm, width - 20 * mm, 14 * mm)

    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(TEXT_SECONDARY)
    canvas.drawString(20 * mm, 10 * mm,
        "Système de Gestion des Présences — Rapport généré automatiquement")
    canvas.drawRightString(width - 20 * mm, 10 * mm, f"Page {doc.page}")

    canvas.restoreState()


def _status_table(students, styles, header_bg, badge_bg, badge_color, label):
    """Construit une table académique propre : en-tête plein, colonne statut
    en badge coloré, header répété en cas de saut de page, pas de
    zebra-striping (cohérent avec STYLE_GUIDE.md — pas de décoration
    inutile)."""
    header_row = [
        Paragraph('Photo', styles['header']),
        Paragraph('Nom', styles['header']),
        Paragraph('Classe', styles['header']),
        Paragraph('Statut', styles['header']),
    ]
    rows = [header_row]
    for student in students:
        if student.face_image and os.path.exists(student.face_image.path):
            photo = Image(student.face_image.path, width=12 * mm, height=12 * mm)
        else:
            photo = Paragraph('—', styles['cell_center'])
        rows.append([
            photo,
            Paragraph(student.name, styles['cell']),
            Paragraph(student.classroom.name, styles['cell']),
            Paragraph(f'<font color="{badge_color}"><b>{label}</b></font>',
                       styles['cell_center']),
        ])

    table = Table(rows, colWidths=[18 * mm, 78 * mm, 62 * mm, 32 * mm],
                   repeatRows=1)
    table.setStyle(TableStyle([
        # En-tête
        ('BACKGROUND', (0, 0), (-1, 0), header_bg),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        # Corps — pas de zebra, juste des séparateurs fins et cohérents
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('TOPPADDING', (0, 1), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -2), 0.4, BORDER),
        # Cadre extérieur propre
        ('BOX', (0, 0), (-1, -1), 0.6, BORDER),
        # Colonne statut = badge : fond coloré sur toute la colonne
        ('BACKGROUND', (3, 1), (3, -1), badge_bg),
    ]))
    return table


def _section_title(text, styles):
    return [
        Paragraph(text, styles['section']),
        HRFlowable(width='100%', thickness=0.6, color=BORDER,
                   spaceBefore=0, spaceAfter=6),
    ]


def generate_pdf(report, buffer):
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        title="Rapport de présence",
    )

    styles = _styles()
    styles['cell_center'] = ParagraphStyle('CellCenter', parent=styles['cell'],
        alignment=TA_CENTER)

    elements = []

    # -----------------------------------------------------------------
    # En-tête du document
    # -----------------------------------------------------------------
    logo_path = finders.find('detectorApp/img/logo.png')
    if logo_path:
        logo = Image(logo_path, width=64 * mm, height=20 * mm)
        logo.hAlign = 'CENTER'
        elements.append(logo)
        elements.append(Spacer(1, 3 * mm))

    elements.append(Paragraph("Rapport de présence", styles['title']))
    elements.append(Paragraph(
        f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
        styles['subtitle']))
    elements.append(Spacer(1, 5 * mm))

    # -----------------------------------------------------------------
    # Informations de la séance
    # -----------------------------------------------------------------
    check = report.attendance_check
    classrooms = check.classrooms.all()
    classroom_names = ', '.join(c.name for c in classrooms) if classrooms else '—'

    info_rows = [
        ['Date', check.created_at.strftime('%d/%m/%Y à %H:%M')],
        ['Enseignant', check.performed_by.get_full_name() or check.performed_by.username],
        ['Email', check.performed_by.email or 'Non renseigné'],
        ['Classe(s)', classroom_names],
    ]
    info_data = [
        [Paragraph(f'<b>{label}</b>', styles['cell']), Paragraph(value, styles['cell'])]
        for label, value in info_rows
    ]
    info_table = Table(info_data, colWidths=[35 * mm, 135 * mm])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEBELOW', (0, 0), (-1, -1), 0.4, BORDER),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 6 * mm))

    # -----------------------------------------------------------------
    # Statistiques résumées
    # -----------------------------------------------------------------
    present_count = report.present_students.count()
    absent_count = report.absent_students.count()
    unidentified_count = len(report.unidentified_faces or [])

    def stat_cell(count, label, border_color, bg_color):
        cell = Table(
            [[Paragraph(str(count), styles['stat_number'])],
             [Spacer(1, 2 * mm)],
             [Paragraph(label, styles['stat_label'])]],
            colWidths=[52 * mm],
        )
        cell.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 0),
            ('TOPPADDING', (0, 2), (-1, 2), 0),
            ('BOTTOMPADDING', (0, 2), (-1, 2), 8),
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('BOX', (0, 0), (-1, -1), 0.6, border_color),
        ]))
        return cell

    stats_row = Table([[
        stat_cell(present_count, 'PRÉSENTS', SUCCESS, SUCCESS_BG),
        stat_cell(absent_count, 'ABSENTS', DANGER, DANGER_BG),
        stat_cell(unidentified_count, 'NON IDENTIFIÉS', WARNING, WARNING_BG),
    ]], colWidths=[56 * mm, 56 * mm, 56 * mm])
    stats_row.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(stats_row)
    elements.append(Spacer(1, 4 * mm))

    # -----------------------------------------------------------------
    # 1. Tableaux — présents / absents (avant les photos, comme demandé)
    # -----------------------------------------------------------------
    elements += _section_title(f"Élèves présents ({present_count})", styles)
    if present_count > 0:
        elements.append(_status_table(
            report.present_students.all(), styles,
            header_bg=NAVY, badge_bg=SUCCESS_BG, badge_color='#15803D',
            label='PRÉSENT',
        ))
    else:
        elements.append(Paragraph('Aucun élève présent.', styles['empty']))
    elements.append(Spacer(1, 6 * mm))

    elements += _section_title(f"Élèves absents ({absent_count})", styles)
    if absent_count > 0:
        elements.append(_status_table(
            report.absent_students.all(), styles,
            header_bg=NAVY, badge_bg=DANGER_BG, badge_color='#B91C1C',
            label='ABSENT',
        ))
    else:
        elements.append(Paragraph('Aucun élève absent.', styles['empty']))
    elements.append(Spacer(1, 6 * mm))

    # Visages non identifiés — grille compacte
    if unidentified_count > 0:
        elements += _section_title(
            f"Visages non identifiés ({unidentified_count})", styles)
        thumbs = []
        for face_url in report.unidentified_faces:
            face_path = face_url.replace(settings.MEDIA_URL, '')
            face_full_path = os.path.join(settings.MEDIA_ROOT, face_path)
            if os.path.exists(face_full_path):
                thumbs.append(Image(face_full_path, width=18 * mm, height=18 * mm))
        if thumbs:
            for i in range(0, len(thumbs), 7):
                row = thumbs[i:i + 7]
                while len(row) < 7:
                    row.append(Paragraph('', styles['cell']))
                grid = Table([row], colWidths=[25 * mm] * 7)
                grid.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ]))
                elements.append(grid)
        elements.append(Spacer(1, 6 * mm))

    # -----------------------------------------------------------------
    # 2. Photos — après les tableaux, comme demandé
    # -----------------------------------------------------------------
    has_annotated = check.source_image and os.path.exists(check.source_image.path)
    has_original = (hasattr(check, 'original_image') and check.original_image
                     and os.path.exists(check.original_image.path))

    if has_annotated or has_original:
        elements += _section_title("Photos de la séance", styles)

    if has_annotated:
        elements.append(Paragraph("Photo annotée", styles['cell']))
        elements.append(Spacer(1, 2 * mm))
        img = Image(check.source_image.path, width=170 * mm, height=100 * mm)
        img.hAlign = 'CENTER'
        elements.append(img)
        elements.append(Spacer(1, 5 * mm))

    if has_original:
        elements.append(Paragraph("Photo originale", styles['cell']))
        elements.append(Spacer(1, 2 * mm))
        img = Image(check.original_image.path, width=170 * mm, height=100 * mm)
        img.hAlign = 'CENTER'
        elements.append(img)

    doc.build(elements, onFirstPage=_page_decoration, onLaterPages=_page_decoration)
    return buffer