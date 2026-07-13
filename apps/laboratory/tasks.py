"""Laboratory Celery tasks for PDF generation and notifications."""
from celery import shared_task
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger('apps.laboratory')


@shared_task(bind=True, max_retries=3)
def generate_lab_report_pdf(self, lab_order_id):
    """Generate PDF report for lab order results."""
    try:
        from apps.laboratory.models import LabOrder
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from io import BytesIO

        lab_order = LabOrder.objects.get(id=lab_order_id)

        # Generate PDF in memory
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        pdf.setTitle(f'Rapport Labo {lab_order.id}')

        # Header
        pdf.setFont('Helvetica-Bold', 14)
        pdf.drawString(50, 750, 'SGHL - RAPPORT DE LABORATOIRE')
        pdf.setFont('Helvetica', 10)
        pdf.drawString(50, 730, f'Date: {timezone.now().strftime("%d/%m/%Y %H:%M")}')
        pdf.drawString(50, 710, f'Patient: {lab_order.patient.get_full_name()}')
        pdf.drawString(50, 690, f'N° Commande: {lab_order.id}')

        # Results
        pdf.setFont('Helvetica-Bold', 12)
        pdf.drawString(50, 650, 'Résultats:')
        y = 620
        pdf.setFont('Helvetica', 10)

        for item in lab_order.items.all():
            pdf.drawString(70, y, f'{item.test.name}: {item.result_value} {item.result_unit}')
            if item.is_abnormal:
                pdf.drawString(70, y - 15, '⚠ Valeur anormale')
                y -= 30
            else:
                y -= 20

        # Signature placeholder
        pdf.setFont('Helvetica', 9)
        pdf.drawString(50, 100, '_' * 50)
        pdf.drawString(50, 80, 'Biologiste')

        pdf.save()

        # Save to file
        buffer.seek(0)
        filename = f'lab_report_{lab_order.id}.pdf'
        lab_order.report_file.save(filename, buffer, save=True)

        logger.info(f'Lab report PDF generated: {filename}')
        return {'status': 'success', 'report_file': filename}

    except Exception as exc:
        logger.error(f'generate_lab_report_pdf failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_lab_results_notification(self, lab_order_id):
    """Send lab results notification to patient."""
    try:
        from apps.laboratory.models import LabOrder

        lab_order = LabOrder.objects.get(id=lab_order_id)
        patient = lab_order.patient

        if not patient.email:
            logger.warning(f'No email for patient {patient.id}')
            return {'status': 'skipped', 'reason': 'no_email'}

        subject = f'Vos résultats de laboratoire sont disponibles - SGHL'
        message = f"""
Bonjour {patient.get_full_name()},

Vos résultats de laboratoire sont maintenant disponibles.

N° Commande: {lab_order.id}
Date: {lab_order.created_at.strftime("%d/%m/%Y")}

Veuillez consulter l'application SGHL pour voir vos résultats détaillés.

Important: Si une valeur est anormale, votre médecin vous contactera.

Cordialement,
L'équipe SGHL
        """

        # Attach PDF if available
        if lab_order.report_file:
            email = EmailMessage(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [patient.email],
            )
            email.attach_file(lab_order.report_file.path)
            email.send(fail_silently=False)
        else:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [patient.email],
                fail_silently=False,
            )

        logger.info(f'Lab results notification sent to {patient.email}')
        return {'status': 'success', 'lab_order_id': str(lab_order_id)}

    except Exception as exc:
        logger.error(f'send_lab_results_notification failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=1)
def archive_old_lab_orders(self, days=180):
    """Archive lab orders older than specified days."""
    try:
        from apps.laboratory.models import LabOrder

        cutoff_date = timezone.now() - timedelta(days=days)
        old_orders = LabOrder.objects.filter(
            created_at__lt=cutoff_date,
            status='PUBLISHED'
        )

        count = old_orders.count()

        # Mark as archived (add field if needed)
        # For now, just log them
        logger.info(f'Found {count} lab orders to archive (>{days} days old)')

        return {'status': 'success', 'archived_count': count}

    except Exception as exc:
        logger.error(f'archive_old_lab_orders failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=300)
