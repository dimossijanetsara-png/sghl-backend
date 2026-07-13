"""Authentication Celery tasks for email notifications."""
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
import logging

logger = logging.getLogger('apps.authentication')


@shared_task(bind=True, max_retries=3)
def send_welcome_email(self, user_id):
    """Send welcome email to new user."""
    try:
        from apps.authentication.models import User

        user = User.objects.get(id=user_id)

        subject = 'Bienvenue sur SGHL - Système de Gestion Hospitalière'
        message = f"""
Bienvenue {user.get_full_name()},

Votre compte a été créé avec succès sur le Système de Gestion Hospitalière et de Laboratoire (SGHL).

Email: {user.email}
Rôle: {user.get_role_display()}

Veuillez vous connecter à l'application pour accéder à vos services.

Cordialement,
L'équipe SGHL
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        logger.info(f'Welcome email sent to {user.email}')
        return {'status': 'success', 'user_email': user.email}

    except Exception as exc:
        logger.error(f'send_welcome_email failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_password_reset_email(self, user_id, reset_token):
    """Send password reset email to user."""
    try:
        from apps.authentication.models import User

        user = User.objects.get(id=user_id)

        reset_url = f"{settings.PATIENT_PORTAL_URL}/reset-password?token={reset_token}"

        subject = 'Réinitialisation de votre mot de passe SGHL'
        message = f"""
Bonjour {user.get_full_name()},

Vous avez demandé une réinitialisation de votre mot de passe SGHL.

Cliquez sur le lien ci-dessous pour réinitialiser votre mot de passe:
{reset_url}

Ce lien expire dans 24 heures.

Si vous n'avez pas demandé cette réinitialisation, ignorez cet e-mail.

Cordialement,
L'équipe SGHL
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        logger.info(f'Password reset email sent to {user.email}')
        return {'status': 'success', 'user_email': user.email}

    except Exception as exc:
        logger.error(f'send_password_reset_email failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_mfa_setup_email(self, user_id):
    """Send MFA setup confirmation email."""
    try:
        from apps.authentication.models import User

        user = User.objects.get(id=user_id)

        subject = 'Authentification multi-facteurs activée - SGHL'
        message = f"""
Bonjour {user.get_full_name()},

L'authentification multi-facteurs (MFA) a été activée sur votre compte SGHL.

À partir de maintenant, vous devrez entrer un code temporaire en plus de votre mot de passe lors de la connexion.

Si vous ne reconnaissez pas cette action, veuillez contacter immédiatement l'administrateur.

Cordialement,
L'équipe SGHL
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        logger.info(f'MFA setup email sent to {user.email}')
        return {'status': 'success', 'user_email': user.email}

    except Exception as exc:
        logger.error(f'send_mfa_setup_email failed: {str(exc)}')
        raise self.retry(exc=exc, countdown=60)
