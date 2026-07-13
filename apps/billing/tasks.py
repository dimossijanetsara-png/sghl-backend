"""Billing Celery tasks for invoice generation and accounting."""
from celery import shared_task
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger('apps.billing')


@shared_task(bind=True, max_retries=3)
def generate_invoice_pdf(self, invoice_id):
    """Generate PDF invoice document."""
    try:
        from apps.billing.models import Invoice
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from io import BytesIO

        invoice = Invoice.objects.select_related('patient').prefetch_related('items').get(id=invoice_id)

        # Generate PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20, bottomMargin=20)
        elements = []

        # Title
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1f4788'),
            alignment=1
        )
        elements.append(Paragraph('FACTURE SGHL', title_style))
        elements.append(Spacer(1, 12))

        # Invoice info
        info_data = [
            ['N° Facture:', invoice.invoice_number, 'Date:', invoice.created_at.strftime('%d/%m/%Y')],
            ['Statut:', invoice.get_status_display(), 'Patient:', invoice.patient.get_full_name()],
        ]
        info_table = Table(info_data)
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 12))

        # Items table
        items_data = [['Description', 'Quantité', 'P.U.', 'Total']]
        for item in invoice.items.all():
            items_data.append([
                item.description,
                str(item.quantity),
                f'{item.unit_price:.2f}',
                f'{item.total_price:.2f}',
            ])

        items_table = Table(items_data)
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 12))

        # Totals
        totals_data = [
            ['Sous-total:', f'{invoice.subtotal:.2f}'],
            ['Remise:', f'{invoice.discount:.2f}'],
            ['TVA:', f'{invoice.tax:.2f}'],
            ['Total:', f'{invoice.total:.2f}'],
            ['Montant payé:', f'{invoice.amount_paid:.2f}'],
            ['Solde:', f'{invoice.balance_due:.2f}'],
        ]
        totals_table = Table(totals_data)
        totals_table.setStyle(TableStyle([
            ('FONTNAME', (-2, 0), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (-2, -1), (-1, -1), colors.lightgreen),
        ]))
        elements.append(totals_table)

        # Build PDF
        doc.build(elements)

        # Save to file
        buffer.seek(0)
        filename = f'invoice_{invoice.invoice_number}.pdf'
        invoice.pdf_file.save(filename, buffer, save=True)

        logger.info(f'Invoice PDF generated: {filename}')
        return {'status': 'success', 'invoice_file': filename}

    except Exception as exc:
        logger.error(f'generate_invoice_pdf failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_invoice_email(self, invoice_id):
    """Send invoice to patient by email."""
    try:
        from apps.billing.models import Invoice

        invoice = Invoice.objects.get(id=invoice_id)
        patient = invoice.patient

        if not patient.email:
            logger.warning(f'No email for patient {patient.id}')
            return {'status': 'skipped', 'reason': 'no_email'}

        subject = f'Votre facture SGHL - {invoice.invoice_number}'
        message = f"""
Bonjour {patient.get_full_name()},

Veuillez trouver ci-joint votre facture pour les services fournis par SGHL.

N° Facture: {invoice.invoice_number}
Date: {invoice.created_at.strftime("%d/%m/%Y")}
Montant: {invoice.total:.2f}
Statut: {invoice.get_status_display()}

En cas de questions, veuillez contacter notre service facturation.

Cordialement,
L'équipe SGHL
        """

        email = EmailMessage(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [patient.email],
        )

        # Attach PDF if available
        if invoice.pdf_file:
            email.attach_file(invoice.pdf_file.path)

        email.send(fail_silently=False)

        logger.info(f'Invoice email sent to {patient.email}')
        return {'status': 'success', 'invoice_id': str(invoice_id)}

    except Exception as exc:
        logger.error(f'send_invoice_email failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=1)
def generate_monthly_accounting_report(self):
    """Generate monthly accounting report."""
    try:
        from apps.billing.models import Invoice, AccountingEntry
        from django.db.models import Sum

        now = timezone.now()
        start_date = now.replace(day=1)

        # Get invoices for the month
        invoices = Invoice.objects.filter(
            created_at__month=start_date.month,
            created_at__year=start_date.year,
            status='PAID'
        )

        total_revenue = invoices.aggregate(Sum('total'))['total__sum'] or 0
        entries_count = AccountingEntry.objects.filter(
            timestamp__month=start_date.month,
            timestamp__year=start_date.year
        ).count()

        report = {
            'period': start_date.strftime('%B %Y'),
            'invoices': invoices.count(),
            'total_revenue': float(total_revenue),
            'accounting_entries': entries_count,
            'generated_at': now.isoformat(),
        }

        logger.info(f'Monthly accounting report generated: {report}')
        return {'status': 'success', 'report': report}

    except Exception as exc:
        logger.error(f'generate_monthly_accounting_report failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=300)
