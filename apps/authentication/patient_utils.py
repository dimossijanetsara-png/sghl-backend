"""
Utilitaires pour l'isolation des données patients.
Un utilisateur avec le rôle PATIENT ne peut accéder qu'à ses propres données.
"""
from ninja.errors import HttpError


def get_patient_profile(user):
    """
    Retourne l'objet Patient lié à un utilisateur de rôle PATIENT.
    Lève une HttpError 404 si aucun profil patient n'est associé.
    """
    from apps.patients.models import Patient
    try:
        return Patient.objects.get(user=user)
    except Patient.DoesNotExist:
        raise HttpError(404, 'Profil patient introuvable. Contactez l\'administration.')


def enforce_patient_filter(request, queryset, patient_field='patient_id'):
    """
    Si l'utilisateur est PATIENT, filtre le queryset à ses propres données.
    Sinon, retourne le queryset tel quel.

    Usage:
        qs = enforce_patient_filter(request, Appointment.objects.all())
    """
    if request.auth.role == 'PATIENT':
        patient = get_patient_profile(request.auth)
        return queryset.filter(**{patient_field: patient.id})
    return queryset


def assert_patient_owns(request, obj, patient_field='patient_id'):
    """
    Vérifie qu'un objet appartient au patient connecté.
    Lève HttpError 403 si l'accès n'est pas autorisé.
    """
    if request.auth.role != 'PATIENT':
        return  # Les autres rôles ont accès

    patient = get_patient_profile(request.auth)
    obj_patient_id = str(getattr(obj, patient_field, None))
    if obj_patient_id != str(patient.id):
        raise HttpError(403, 'Accès refusé : vous ne pouvez accéder qu\'à vos propres données')
