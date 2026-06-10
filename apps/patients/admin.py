from django.contrib import admin
from .models import Patient, PatientDocument


class PatientDocumentInline(admin.TabularInline):
    model = PatientDocument
    extra = 0
    readonly_fields = ('mime_type', 'file_size', 'uploaded_by', 'created_at')


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('record_number', 'get_full_name', 'date_of_birth', 'gender', 'blood_type', 'is_archived')
    list_filter = ('gender', 'blood_type', 'is_archived', 'consent_given')
    search_fields = ('first_name', 'last_name', 'record_number', 'national_id', 'phone')
    readonly_fields = ('id', 'record_number', 'created_at', 'updated_at')
    inlines = [PatientDocumentInline]
    fieldsets = (
        ('Identite', {'fields': ('record_number', 'first_name', 'last_name', 'date_of_birth', 'gender', 'national_id')}),
        ('Coordonnees', {'fields': ('phone', 'email', 'address', 'city')}),
        ('Medical', {'fields': ('blood_type', 'allergies', 'chronic_conditions')}),
        ('Urgence', {'fields': ('emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation')}),
        ('Assurance', {'fields': ('insurance_provider', 'insurance_number')}),
        ('Consentement', {'fields': ('consent_given', 'consent_date')}),
        ('Archive', {'fields': ('is_archived', 'archived_at')}),
    )
