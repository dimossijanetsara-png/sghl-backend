from ninja import NinjaAPI
from ninja.security import HttpBearer
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()


class JWTAuth(HttpBearer):
    def authenticate(self, request, token):
        try:
            access_token = AccessToken(token)
            user = User.objects.get(id=access_token['user_id'])
            if not user.is_active:
                return None
            request.user = user
            return user
        except Exception:
            return None


jwt_auth = JWTAuth()

api = NinjaAPI(
    title='SGHL API',
    version='1.0.0',
    description='Système de Gestion Hospitalière et de Laboratoire',
    docs_url='/docs',
    auth=jwt_auth,
)


@api.get('/sante', auth=None, tags=['Système'])
def health_check(request):
    from django.db import connection
    from django.core.cache import cache
    db_ok = False
    cache_ok = False
    try:
        connection.ensure_connection()
        db_ok = True
    except Exception:
        pass
    try:
        cache.set('health', 'ok', 5)
        cache_ok = cache.get('health') == 'ok'
    except Exception:
        pass
    return {
        'status': 'ok' if (db_ok and cache_ok) else 'degraded',
        'database': 'ok' if db_ok else 'error',
        'cache': 'ok' if cache_ok else 'error',
        'version': '1.0.0',
    }


# Enregistrement des routers de chaque module
from apps.authentication.api import router as auth_router
from apps.patients.api import router as patients_router
from apps.clinical.api import router as clinical_router
from apps.hospitalization.api import router as hospitalization_router
from apps.nursing.api import router as nursing_router
from apps.laboratory.api import router as laboratory_router
from apps.pharmacy.api import router as pharmacy_router
from apps.billing.api import router as billing_router
from apps.hr.api import router as hr_router
from apps.appointments.api import router as appointments_router
from apps.dashboard.api import router as dashboard_router

api.add_router('/auth', auth_router, tags=['Authentification'])
api.add_router('/patients', patients_router, tags=['Patients'])
api.add_router('/clinique', clinical_router, tags=['Clinique'])
api.add_router('/hospitalisation', hospitalization_router, tags=['Hospitalisation'])
api.add_router('/soins', nursing_router, tags=['Soins Infirmiers'])
api.add_router('/laboratoire', laboratory_router, tags=['Laboratoire'])
api.add_router('/pharmacie', pharmacy_router, tags=['Pharmacie'])
api.add_router('/facturation', billing_router, tags=['Facturation'])
api.add_router('/rh', hr_router, tags=['Ressources Humaines'])
api.add_router('/rendez-vous', appointments_router, tags=['Rendez-vous'])
api.add_router('/dashboard', dashboard_router, tags=['Dashboard'])
