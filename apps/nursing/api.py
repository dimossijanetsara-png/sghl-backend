from typing import List
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.pagination import paginate, PageNumberPagination

from apps.core.models import create_audit_log
from apps.authentication.permissions import require_permission
from .models import Careplan, CareTask, VitalSign, NursingNote
from .schemas import (
    CareplanCreateSchema, CareplanOut, CareTaskSchema, CareTaskOut, CareTaskDoneSchema,
    VitalSignSchema, VitalSignOut, NursingNoteSchema, NursingNoteOut,
)

router = Router()


def _get_ip(request):
    x = request.META.get('HTTP_X_FORWARDED_FOR')
    return x.split(',')[0].strip() if x else request.META.get('REMOTE_ADDR', '')


# --- Plans de soins ---
@router.post('/plans', response=CareplanOut)
@require_permission('nursing:write')
def create_careplan(request, payload: CareplanCreateSchema):
    from apps.hospitalization.models import Hospitalization
    hosp = get_object_or_404(Hospitalization, id=payload.hospitalization_id, status='ACTIVE')
    plan = Careplan.objects.create(
        hospitalization=hosp,
        created_by=request.auth,
        goals=payload.goals or '',
        notes=payload.notes or '',
    )
    tasks = []
    for t in (payload.tasks or []):
        tasks.append(CareTask(
            careplan=plan,
            title=t.title,
            description=t.description or '',
            frequency=t.frequency,
            scheduled_time=t.scheduled_time,
            assigned_to_id=t.assigned_to_id,
            prescription_item_id=t.prescription_item_id,
        ))
    if tasks:
        CareTask.objects.bulk_create(tasks)
    return {
        'id': plan.id,
        'hospitalization_id': plan.hospitalization_id,
        'status': plan.status,
        'goals': plan.goals,
        'notes': plan.notes,
        'created_at': plan.created_at,
        'tasks': list(plan.tasks.all()),
    }


@router.get('/plans/{plan_id}', response=CareplanOut)
@require_permission('nursing:read')
def get_careplan(request, plan_id: str):
    plan = get_object_or_404(Careplan, id=plan_id)
    return {
        'id': plan.id,
        'hospitalization_id': plan.hospitalization_id,
        'status': plan.status,
        'goals': plan.goals,
        'notes': plan.notes,
        'created_at': plan.created_at,
        'tasks': list(plan.tasks.all()),
    }


@router.post('/taches/{task_id}/effectuer', response=CareTaskOut)
@require_permission('nursing:write')
def mark_task_done(request, task_id: str, payload: CareTaskDoneSchema):
    task = get_object_or_404(CareTask, id=task_id)
    task.status = 'DONE'
    task.done_at = timezone.now()
    task.done_by = request.auth
    task.notes = payload.notes or ''
    task.save(update_fields=['status', 'done_at', 'done_by', 'notes'])
    return task


# --- Constantes vitales ---
@router.post('/hospitalisations/{hosp_id}/constantes', response=VitalSignOut)
@require_permission('nursing:write')
def record_vitals(request, hosp_id: str, payload: VitalSignSchema):
    from apps.hospitalization.models import Hospitalization
    hosp = get_object_or_404(Hospitalization, id=hosp_id)
    vital = VitalSign.objects.create(
        hospitalization=hosp,
        recorded_by=request.auth,
        **payload.dict(),
    )
    return vital


@router.get('/hospitalisations/{hosp_id}/constantes', response=List[VitalSignOut])
@require_permission('nursing:read')
def list_vitals(request, hosp_id: str):
    from apps.hospitalization.models import Hospitalization
    hosp = get_object_or_404(Hospitalization, id=hosp_id)
    return list(VitalSign.objects.filter(hospitalization=hosp))


# --- Notes infirmières ---
@router.post('/hospitalisations/{hosp_id}/notes', response=NursingNoteOut)
@require_permission('nursing:write')
def add_nursing_note(request, hosp_id: str, payload: NursingNoteSchema):
    from apps.hospitalization.models import Hospitalization
    hosp = get_object_or_404(Hospitalization, id=hosp_id)
    note = NursingNote.objects.create(
        hospitalization=hosp,
        written_by=request.auth,
        content=payload.content,
        category=payload.category or '',
    )
    return note


@router.get('/hospitalisations/{hosp_id}/notes', response=List[NursingNoteOut])
@require_permission('nursing:read')
def list_nursing_notes(request, hosp_id: str):
    from apps.hospitalization.models import Hospitalization
    hosp = get_object_or_404(Hospitalization, id=hosp_id)
    return list(NursingNote.objects.filter(hospitalization=hosp))
