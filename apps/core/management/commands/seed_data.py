"""
Commande de seed : peuple la base avec des données de démonstration complètes.
Usage : python manage.py seed_data [--reset]
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = 'Peuple la base avec des données de démonstration.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Supprime toutes les données avant de seeder')

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Suppression des données existantes...')
            self._reset()

        self.stdout.write('Création des données de démonstration...')
        with transaction.atomic():
            self._run()
        self.stdout.write(self.style.SUCCESS('Seed terminé avec succès !'))

    # ─── Reset ────────────────────────────────────────────────────────────────

    def _reset(self):
        from apps.nursing.models import VitalSign, NursingNote, CareTask, Careplan
        from apps.laboratory.models import LabOrderItem, LabOrderAudit, LabOrder, LabTest
        from apps.pharmacy.models import DispensationItem, Dispensation, StockMovement, MedicationBatch, Medication
        from apps.billing.models import AccountingEntry, Payment, InvoiceItem, Invoice
        from apps.clinical.models import PrescriptionItem, Prescription, Diagnosis, Consultation
        from apps.hospitalization.models import Transfer, Hospitalization, Bed, Room, Department, Building
        from apps.appointments.models import Appointment, DoctorAvailability
        from apps.patients.models import Patient
        from apps.hr.models import Shift, StaffProfile
        from apps.messaging.models import Message, Conversation

        for Model in [
            VitalSign, NursingNote, CareTask, Careplan,
            LabOrderItem, LabOrderAudit, LabOrder, LabTest,
            DispensationItem, Dispensation, StockMovement, MedicationBatch, Medication,
            AccountingEntry, Payment, InvoiceItem, Invoice,
            PrescriptionItem, Prescription, Diagnosis, Consultation,
            Transfer, Hospitalization, Bed, Room, Department, Building,
            Appointment, DoctorAvailability,
            Shift, StaffProfile,
            Message, Conversation,
            Patient,
        ]:
            Model.objects.all().delete()

        User.objects.exclude(email='dimossijanetsara@gmail.com').exclude(is_superuser=True).delete()

    # ─── Seed principal ───────────────────────────────────────────────────────

    def _run(self):
        self._create_staff()
        self._create_infrastructure()
        self._create_patients()
        self._create_hr_profiles()
        self._create_doctor_availability()
        self._create_appointments()
        self._create_consultations()
        self._create_hospitalizations()
        self._create_lab_tests()
        self._create_lab_orders()
        self._create_medications()
        self._create_invoices()
        self._create_messaging()

    # ─── Staff ────────────────────────────────────────────────────────────────

    def _create_staff(self):
        self.stdout.write('  >> Création du personnel médical...')
        staff_data = [
            ('thomas.martin@sghl.fr',   'MartinThomas123!',  'Thomas',   'Martin',   'DOCTOR'),
            ('claire.dubois@sghl.fr',   'DuboisClaire123!',  'Claire',   'Dubois',   'DOCTOR'),
            ('marie.bertrand@sghl.fr',  'BertrandMarie123!', 'Marie',    'Bertrand', 'NURSE'),
            ('pierre.renard@sghl.fr',   'RenardPierre123!',  'Pierre',   'Renard',   'BIOLOGIST'),
            ('sophie.laurent@sghl.fr',  'LaurentSophie123!', 'Sophie',   'Laurent',  'PHARMACIST'),
            ('jean.moreau@sghl.fr',     'MoreauJean123!',    'Jean',     'Moreau',   'RECEPTIONIST'),
            ('anne.petit@sghl.fr',      'PetitAnne123!',     'Anne',     'Petit',    'ACCOUNTANT'),
            ('lucie.simon@sghl.fr',     'SimonLucie123!',    'Lucie',    'Simon',    'NURSE'),
        ]
        self.staff = {}
        for email, pwd, fn, ln, role in staff_data:
            user, created = User.objects.get_or_create(
                email=email,
                defaults=dict(
                    first_name=fn, last_name=ln, role=role,
                    is_active=True, otp_verified=True,
                    phone=f'+336{fn[:4].upper()}001',
                )
            )
            if created:
                user.set_password(pwd)
                user.save(update_fields=['password'])
            self.staff[role if role not in self.staff else f'{role}2'] = user
        self.doctor1 = User.objects.get(email='thomas.martin@sghl.fr')
        self.doctor2 = User.objects.get(email='claire.dubois@sghl.fr')
        self.nurse1  = User.objects.get(email='marie.bertrand@sghl.fr')
        self.nurse2  = User.objects.get(email='lucie.simon@sghl.fr')
        self.bio     = User.objects.get(email='pierre.renard@sghl.fr')
        self.pharma  = User.objects.get(email='sophie.laurent@sghl.fr')
        self.recept  = User.objects.get(email='jean.moreau@sghl.fr')
        self.account = User.objects.get(email='anne.petit@sghl.fr')
        self.admin   = User.objects.filter(is_superuser=True).first()

    # ─── Infrastructure ───────────────────────────────────────────────────────

    def _create_infrastructure(self):
        from apps.hospitalization.models import Building, Department, Room, Bed
        self.stdout.write('  >> Création de l\'infrastructure...')

        bat_a, _ = Building.objects.get_or_create(name='Bâtiment A', defaults={'description': 'Médecine générale et consultations', 'is_active': True})
        bat_b, _ = Building.objects.get_or_create(name='Bâtiment B', defaults={'description': 'Urgences et soins intensifs', 'is_active': True})

        self.dept_med, _ = Department.objects.get_or_create(
            code='MED-GEN',
            defaults={'building': bat_a, 'name': 'Médecine Générale', 'head_doctor': self.doctor1, 'is_active': True}
        )
        self.dept_cardio, _ = Department.objects.get_or_create(
            code='CARDIO',
            defaults={'building': bat_a, 'name': 'Cardiologie', 'head_doctor': self.doctor2, 'is_active': True}
        )
        self.dept_urg, _ = Department.objects.get_or_create(
            code='URG',
            defaults={'building': bat_b, 'name': 'Urgences', 'head_doctor': self.doctor1, 'is_active': True}
        )
        self.dept_lab, _ = Department.objects.get_or_create(
            code='LABO',
            defaults={'building': bat_a, 'name': 'Laboratoire', 'is_active': True}
        )

        # Rooms et beds
        self.beds = []
        rooms_data = [
            (self.dept_med,   '101', 'STANDARD', 1, 2),
            (self.dept_med,   '102', 'PRIVATE',  1, 1),
            (self.dept_cardio,'201', 'STANDARD', 2, 2),
            (self.dept_cardio,'202', 'ICU',      2, 2),
            (self.dept_urg,   '001', 'EMERGENCY',0, 2),
        ]
        for dept, num, rtype, floor, nb_beds in rooms_data:
            room, _ = Room.objects.get_or_create(
                department=dept, number=num,
                defaults={'room_type': rtype, 'floor': floor, 'is_active': True}
            )
            for i in range(1, nb_beds + 1):
                bed, _ = Bed.objects.get_or_create(
                    room=room, number=f'L{i}',
                    defaults={'status': 'AVAILABLE', 'is_active': True}
                )
                self.beds.append(bed)

    # ─── Patients ─────────────────────────────────────────────────────────────

    def _create_patients(self):
        from apps.patients.models import Patient
        self.stdout.write('  >> Création des patients...')

        patients_data = [
            ('Julien',    'Fontaine',  '1985-03-14', 'M', 'A+',  '+33612345001', 'julien.fontaine@mail.fr',   'Diabète type 2',    '12 rue des Lilas, Paris'),
            ('Émilie',    'Rousseau',  '1972-07-22', 'F', 'B+',  '+33612345002', 'emilie.rousseau@mail.fr',   'Hypertension artérielle', '5 av Victor Hugo, Lyon'),
            ('Marc',      'Lefebvre',  '1958-11-30', 'M', 'O-',  '+33612345003', 'marc.lefebvre@mail.fr',     'BPCO',              '8 bd des Roses, Marseille'),
            ('Isabelle',  'Garnier',   '1995-01-09', 'F', 'AB+', '+33612345004', 'isabelle.garnier@mail.fr',  '',                  '3 rue Pasteur, Toulouse'),
            ('Robert',    'Mercier',   '1949-06-18', 'M', 'A-',  '+33612345005', 'robert.mercier@mail.fr',    'Insuffisance cardiaque, Diabète type 2', '22 rue du Moulin, Bordeaux'),
            ('Nathalie',  'Bonnet',    '1980-09-05', 'F', 'O+',  '+33612345006', 'nathalie.bonnet@mail.fr',   'Asthme',            '7 allée des Chênes, Nantes'),
            ('Didier',    'Chevalier', '1966-04-28', 'M', 'B-',  '+33612345007', 'didier.chevalier@mail.fr',  'Arthrite rhumatoïde', '15 impasse du Lac, Strasbourg'),
            ('Sandrine',  'Morel',     '1988-12-03', 'F', 'A+',  '+33612345008', 'sandrine.morel@mail.fr',    '',                  '9 rue Jean Jaurès, Lille'),
            ('Alain',     'Simon',     '1975-08-19', 'M', 'O+',  '+33612345009', 'alain.simon@mail.fr',       'Hypertension artérielle', '4 bd de la République, Rennes'),
            ('Céline',    'Faure',     '2001-02-14', 'F', 'AB-', '+33612345010', 'celine.faure@mail.fr',      'Allergie aux pénicillines', '1 av de la Gare, Montpellier'),
            ('Henri',     'Durand',    '1952-10-07', 'M', 'B+',  '+33612345011', 'henri.durand@mail.fr',      'Insuffisance rénale chronique, HTA', '33 rue des Acacias, Nice'),
            ('Laurence',  'Michel',    '1968-05-25', 'F', 'A-',  '+33612345012', 'laurence.michel@mail.fr',   'Hypothyroïdie',     '6 rue du Commerce, Toulon'),
        ]

        self.patients = []
        for fn, ln, dob, gender, blood, phone, email, conditions, addr in patients_data:
            p, _ = Patient.objects.get_or_create(
                email=email,
                defaults=dict(
                    first_name=fn, last_name=ln,
                    date_of_birth=date.fromisoformat(dob),
                    gender=gender, blood_type=blood,
                    phone=phone, address=addr,
                    chronic_conditions=conditions,
                    consent_given=True,
                    consent_date=timezone.now() - timedelta(days=30),
                    is_archived=False,
                )
            )
            self.patients.append(p)

    # ─── RH Profiles ──────────────────────────────────────────────────────────

    def _create_hr_profiles(self):
        from apps.hr.models import StaffProfile, Shift
        self.stdout.write('  >> Création des profils RH...')

        profiles_data = [
            (self.doctor1, self.dept_med,   'EMP-001', 'Médecine Générale',    'MED-12345', date(2018, 9, 1)),
            (self.doctor2, self.dept_cardio,'EMP-002', 'Cardiologie',           'MED-67890', date(2015, 3, 15)),
            (self.nurse1,  self.dept_med,   'EMP-003', 'Soins infirmiers',      'INF-11111', date(2020, 6, 1)),
            (self.nurse2,  self.dept_cardio,'EMP-004', 'Soins intensifs',       'INF-22222', date(2021, 1, 10)),
            (self.bio,     self.dept_lab,   'EMP-005', 'Biologie médicale',     'BIO-33333', date(2019, 4, 1)),
            (self.pharma,  self.dept_med,   'EMP-006', 'Pharmacie clinique',    'PHA-44444', date(2017, 7, 1)),
            (self.recept,  self.dept_med,   'EMP-007', 'Accueil et secrétariat','REC-55555', date(2022, 2, 1)),
            (self.account, self.dept_med,   'EMP-008', 'Comptabilité',          'ACC-66666', date(2016, 11, 1)),
        ]
        self.staff_profiles = []
        for user, dept, emp_num, spec, lic, hire in profiles_data:
            sp, _ = StaffProfile.objects.get_or_create(
                user=user,
                defaults=dict(department=dept, employee_number=emp_num,
                              specialization=spec, license_number=lic,
                              hire_date=hire, is_active=True)
            )
            self.staff_profiles.append(sp)

        # Shifts pour 7 jours
        now = timezone.now()
        week_start = now - timedelta(days=now.weekday())
        shift_data = [
            (self.staff_profiles[0], self.dept_med,   'MORNING',   0, 7, 0, 14, 0),
            (self.staff_profiles[0], self.dept_med,   'AFTERNOON', 2, 13, 0, 20, 0),
            (self.staff_profiles[1], self.dept_cardio,'MORNING',   1, 7, 0, 14, 0),
            (self.staff_profiles[1], self.dept_cardio,'ON_CALL',   4, 20, 0, 8, 0),
            (self.staff_profiles[2], self.dept_med,   'MORNING',   0, 6, 30, 14, 30),
            (self.staff_profiles[2], self.dept_med,   'AFTERNOON', 3, 14, 30, 22, 30),
            (self.staff_profiles[3], self.dept_cardio,'NIGHT',     1, 22, 0, 6, 0),
            (self.staff_profiles[4], self.dept_lab,   'MORNING',   0, 8, 0, 16, 0),
        ]
        for sp, dept, stype, day_offset, sh, sm, eh, em in shift_data:
            start = (week_start + timedelta(days=day_offset)).replace(hour=sh, minute=sm, second=0, microsecond=0)
            end   = start + timedelta(hours=(eh - sh if eh >= sh else 24 - sh + eh), minutes=(em - sm))
            Shift.objects.get_or_create(
                staff=sp, department=dept, shift_type=stype,
                start_datetime=start,
                defaults=dict(end_datetime=end, is_confirmed=True)
            )

    # ─── Doctor availability ───────────────────────────────────────────────────

    def _create_doctor_availability(self):
        from apps.appointments.models import DoctorAvailability
        self.stdout.write('  >> Création des disponibilités médecins...')
        for doctor in [self.doctor1, self.doctor2]:
            for day in [0, 1, 2, 3, 4]:  # Lun-Ven
                DoctorAvailability.objects.get_or_create(
                    doctor=doctor, day_of_week=day,
                    defaults=dict(start_time='08:00', end_time='17:00',
                                  slot_duration_minutes=30, is_active=True)
                )

    # ─── Rendez-vous ──────────────────────────────────────────────────────────

    def _create_appointments(self):
        from apps.appointments.models import Appointment
        self.stdout.write('  >> Création des rendez-vous...')
        now = timezone.now()
        appts = [
            (self.patients[0], self.doctor1, 0,  'CONFIRMED', 'Suivi diabète — contrôle HbA1c'),
            (self.patients[1], self.doctor2, 1,  'CONFIRMED', 'Consultation cardiologie — bilan annuel'),
            (self.patients[2], self.doctor1, 2,  'PENDING',   'Contrôle BPCO — spirométrie'),
            (self.patients[3], self.doctor1, 3,  'PENDING',   'Bilan de santé général'),
            (self.patients[4], self.doctor2, 4,  'CONFIRMED', 'Suivi insuffisance cardiaque'),
            (self.patients[5], self.doctor1, 5,  'PENDING',   'Consultation asthme — ajustement traitement'),
            (self.patients[6], self.doctor2, 6,  'CONFIRMED', 'Rhumatologie — douleurs articulaires'),
            (self.patients[7], self.doctor1, 7,  'CANCELLED', 'Visite de contrôle'),
            (self.patients[8], self.doctor1, -1, 'COMPLETED', 'HTA — bilan mensuel'),
            (self.patients[9], self.doctor2, -2, 'COMPLETED', 'Première consultation'),
            (self.patients[10],self.doctor1, -3, 'COMPLETED', 'Suivi insuffisance rénale'),
            (self.patients[11],self.doctor2, -4, 'COMPLETED', 'Hypothyroïdie — ajustement Levothyrox'),
            (self.patients[0], self.doctor2, -7, 'COMPLETED', 'Cardio — douleur thoracique'),
            (self.patients[1], self.doctor1, 10, 'PENDING',   'Résultats labo — rendez-vous de suivi'),
            (self.patients[4], self.doctor1, 14, 'PENDING',   'Consultation pré-opératoire'),
        ]
        for pat, doc, day_delta, status, reason in appts:
            appt_dt = (now + timedelta(days=day_delta)).replace(hour=9, minute=0, second=0, microsecond=0)
            Appointment.objects.get_or_create(
                patient=pat, doctor=doc, appointment_date=appt_dt,
                defaults=dict(duration_minutes=30, reason=reason, status=status)
            )

    # ─── Consultations ────────────────────────────────────────────────────────

    def _create_consultations(self):
        from apps.clinical.models import Consultation, Diagnosis, Prescription, PrescriptionItem
        self.stdout.write('  >> Création des consultations...')
        now = timezone.now()

        consults_data = [
            (self.patients[0], self.doctor1, -5,  'COMPLETED', 'Fatigue, polyurie',          'Diabète type 2 mal équilibré — HbA1c à 9.2%', 'E11.9', 'Diabète de type 2 sans complication'),
            (self.patients[1], self.doctor2, -10, 'COMPLETED', 'Palpitations et dyspnée',    'PA 160/100, FC 92 bpm, légère cardiomégalie', 'I10', 'Hypertension essentielle'),
            (self.patients[2], self.doctor1, -3,  'COMPLETED', 'Aggravation de la toux',     'BPCO stade II — exposition tabagique 40PA', 'J44.1', 'BPCO avec exacerbation aiguë'),
            (self.patients[4], self.doctor2, -7,  'COMPLETED', 'Œdèmes des membres inférieurs', 'IC stade II — fraction d\'éjection 45%',  'I50.9', 'Insuffisance cardiaque non précisée'),
            (self.patients[5], self.doctor1, -2,  'COMPLETED', 'Crise d\'asthme la nuit',    'DEP 70% — crises nocturnes fréquentes',      'J45.1', 'Asthme persistant léger'),
            (self.patients[8], self.doctor1, -14, 'COMPLETED', 'Céphalées matinales',        'HTA stade 1 — PA 145/92',                    'I10',   'Hypertension essentielle'),
            (self.patients[9], self.doctor2, -1,  'IN_PROGRESS','Douleur thoracique gauche', 'ECG en cours, troponine commandée',           'R07.9', 'Douleur thoracique non précisée'),
            (self.patients[10],self.doctor1, -20, 'COMPLETED', 'Asthénie, œdèmes discrets',  'Créatinine 250 µmol/L — IVR stade 3',        'N18.3', 'Maladie rénale chronique stade 3'),
            (self.patients[3], self.doctor1,  0,  'SCHEDULED', 'Bilan général',              '',                                            '', ''),
            (self.patients[11],self.doctor2, -30, 'COMPLETED', 'Prise de poids, fatigue',    'TSH élevée, T4 basse — Levothyrox initié',   'E03.9', 'Hypothyroïdie non précisée'),
        ]

        self.consultations = []
        for pat, doc, day_delta, status, complaint, exam, icd_code, icd_label in consults_data:
            consult_dt = now + timedelta(days=day_delta)
            consult, _ = Consultation.objects.get_or_create(
                patient=pat, doctor=doc, consultation_date__date=consult_dt.date(),
                defaults=dict(
                    status=status, consultation_date=consult_dt,
                    chief_complaint=complaint, physical_exam=exam,
                    anamnesis='Antécédents récupérés du dossier médical.',
                )
            )
            self.consultations.append(consult)

            if icd_code and status == 'COMPLETED':
                Diagnosis.objects.get_or_create(
                    consultation=consult, icd10_code=icd_code,
                    defaults=dict(icd10_label=icd_label, diag_type='PRINCIPAL')
                )
                presc, _ = Prescription.objects.get_or_create(
                    consultation=consult,
                    defaults=dict(prescribed_by=doc, status='VALIDATED', notes='')
                )
                self._add_prescription_items(presc, icd_code)

    def _add_prescription_items(self, presc, icd_code):
        from apps.clinical.models import PrescriptionItem
        items_map = {
            'E11.9': [('Metformine 500mg', '500 mg', '3x/jour', '3 mois', 'Oral', 'Prendre au cours des repas', 90)],
            'I10':   [('Amlodipine 5mg', '5 mg', '1x/jour', '1 mois', 'Oral', 'Matin à jeun', 30),
                      ('Ramipril 5mg', '5 mg', '1x/jour', '1 mois', 'Oral', 'Matin', 30)],
            'J44.1': [('Salbutamol', '100 µg', 'en cas de besoin', '1 mois', 'Inhalation', '2 bouffées', 1),
                      ('Budésonide/Formotérol', '160/4,5 µg', '2x/jour', '1 mois', 'Inhalation', 'Matin et soir', 1)],
            'I50.9': [('Furosémide 40mg', '40 mg', '1x/jour', '1 mois', 'Oral', 'Matin', 30),
                      ('Bisoprolol 5mg', '5 mg', '1x/jour', '1 mois', 'Oral', 'Matin', 30)],
            'J45.1': [('Montélukast 10mg', '10 mg', '1x/soir', '3 mois', 'Oral', 'Soir au coucher', 90)],
            'E03.9': [('Levothyroxine 50µg', '50 µg', '1x/jour', '3 mois', 'Oral', 'À jeun le matin', 90)],
            'N18.3': [('Fer sucrose 200mg', '200 mg', '1x/jour', '1 mois', 'Oral', 'Entre les repas', 30)],
            'R07.9': [('Aspirine 100mg', '100 mg', '1x/jour', '1 mois', 'Oral', 'Avec un repas', 30)],
        }
        for item in items_map.get(icd_code, []):
            PrescriptionItem.objects.get_or_create(
                prescription=presc, medication_name=item[0],
                defaults=dict(dosage=item[1], frequency=item[2], duration=item[3],
                              route=item[4], instructions=item[5], quantity=item[6])
            )

    # ─── Hospitalisations ─────────────────────────────────────────────────────

    def _create_hospitalizations(self):
        from apps.hospitalization.models import Hospitalization, Bed
        from apps.nursing.models import Careplan, CareTask, VitalSign, NursingNote
        self.stdout.write('  >> Création des hospitalisations...')
        now = timezone.now()

        # Marquer des lits comme occupés
        hosp_data = [
            (self.patients[4],  self.beds[0], self.doctor2, 'ACTIVE',     -5,  None,  'Décompensation cardiaque aiguë avec œdèmes pulmonaires'),
            (self.patients[2],  self.beds[1], self.doctor1, 'ACTIVE',     -3,  None,  'Exacerbation BPCO sévère — oxygénothérapie en cours'),
            (self.patients[10], self.beds[4], self.doctor1, 'ACTIVE',     -2,  None,  'Insuffisance rénale aiguë sur chronique — dialyse urgente'),
            (self.patients[6],  self.beds[2], self.doctor2, 'DISCHARGED', -15, -8,    'Crise rhumatoïde sévère'),
            (self.patients[0],  self.beds[3], self.doctor1, 'DISCHARGED', -30, -25,   'Décompensation diabétique — acidocétose'),
        ]

        self.hospitalizations = []
        for pat, bed, doc, status, adm_delta, disc_delta, reason in hosp_data:
            adm_dt = now + timedelta(days=adm_delta)
            disc_dt = (now + timedelta(days=disc_delta)) if disc_delta else None
            hosp, _ = Hospitalization.objects.get_or_create(
                patient=pat, bed=bed,
                defaults=dict(
                    referring_doctor=doc, status=status,
                    admission_date=adm_dt,
                    expected_discharge_date=(adm_dt + timedelta(days=7)).date(),
                    actual_discharge_date=disc_dt,
                    admission_reason=reason,
                    discharge_summary='Patient stable à la sortie.' if disc_dt else '',
                )
            )
            if status == 'ACTIVE':
                bed.status = 'OCCUPIED'
                bed.save(update_fields=['status'])
            self.hospitalizations.append(hosp)

            # Signes vitaux
            for i in range(3):
                record_dt = adm_dt + timedelta(hours=i * 8)
                VitalSign.objects.get_or_create(
                    hospitalization=hosp, recorded_at=record_dt,
                    defaults=dict(
                        recorded_by=self.nurse1,
                        temperature=Decimal('37.2') + Decimal(str(i * 0.1)),
                        systolic_bp=130 + i * 2, diastolic_bp=85 + i,
                        heart_rate=78 + i * 3, respiratory_rate=16,
                        oxygen_saturation=Decimal('97.5'),
                        weight=Decimal('72.0'), height=Decimal('175.0'),
                        pain_score=2,
                    )
                )

            # Plan de soins
            if status == 'ACTIVE':
                careplan, _ = Careplan.objects.get_or_create(
                    hospitalization=hosp,
                    defaults=dict(
                        created_by=self.nurse1, status='ACTIVE',
                        goals='Stabilisation de l\'état clinique, éducation thérapeutique.',
                    )
                )
                tasks_data = [
                    ('Prise des constantes', 'Température, TA, FC, SpO2', 'QID',  '08:00', self.nurse1, 'DONE'),
                    ('Administration traitement', 'Selon ordonnance', 'BID', '08:00', self.nurse1, 'DONE'),
                    ('Pesée quotidienne', 'À jeun le matin', 'DAILY', '07:00', self.nurse2, 'PENDING'),
                    ('Mobilisation passive', 'Kinésithérapie au lit', 'DAILY', '10:00', self.nurse1, 'PENDING'),
                ]
                for title, desc, freq, stime, nurse, st in tasks_data:
                    CareTask.objects.get_or_create(
                        careplan=careplan, title=title,
                        defaults=dict(description=desc, frequency=freq,
                                      scheduled_time=stime, assigned_to=nurse, status=st)
                    )

                NursingNote.objects.get_or_create(
                    hospitalization=hosp, written_by=self.nurse1,
                    defaults=dict(
                        content='Patient coopératif. Traitement bien toléré. Surveillance rapprochée maintenue.',
                        category='OBSERVATION'
                    )
                )

    # ─── Analyses de laboratoire ──────────────────────────────────────────────

    def _create_lab_tests(self):
        from apps.laboratory.models import LabTest
        self.stdout.write('  >> Création des analyses de laboratoire...')
        tests = [
            ('NFS',     'Numération Formule Sanguine',  'Hématologie',   '4.0–10.5 G/L',   'G/L',      '25.00', 4),
            ('GLY',     'Glycémie à jeun',              'Biochimie',     '3.9–6.1 mmol/L', 'mmol/L',   '8.00',  2),
            ('HBA1C',   'Hémoglobine glyquée',          'Biochimie',     '< 7.0 %',         '%',         '18.00', 4),
            ('CHOL',    'Cholestérol total',            'Lipidologie',   '< 5.2 mmol/L',    'mmol/L',   '12.00', 4),
            ('CREAT',   'Créatinine sérique',           'Biochimie',     '53–106 µmol/L',   'µmol/L',   '8.00',  2),
            ('TROPO',   'Troponine I ultra-sensible',   'Cardiologie',   '< 34 ng/L',        'ng/L',      '45.00', 1),
            ('CRP',     'Protéine C-réactive',          'Immunologie',   '< 5 mg/L',         'mg/L',      '10.00', 4),
            ('TSH',     'Thyroid Stimulating Hormone',  'Endocrinologie','0.4–4.0 mUI/L',   'mUI/L',    '15.00', 8),
            ('ALAT',    'Alanine aminotransférase',     'Biochimie',     '< 41 U/L',         'U/L',       '8.00',  4),
            ('DDFRAG',  'D-Dimères',                    'Hémostase',     '< 500 µg/L',       'µg/L',      '22.00', 2),
            ('IONOG',   'Ionogramme sanguin',           'Biochimie',     'Na 135–145, K 3.5–5.0', 'mmol/L', '14.00', 2),
            ('BILI',    'Bilirubine totale',            'Biochimie',     '< 21 µmol/L',     'µmol/L',   '10.00', 4),
        ]
        self.lab_tests = []
        for code, name, cat, nr, unit, price, ta in tests:
            lt, _ = LabTest.objects.get_or_create(
                code=code,
                defaults=dict(name=name, category=cat, normal_range=nr,
                              unit=unit, price=Decimal(price), turnaround_hours=ta, is_active=True)
            )
            self.lab_tests.append(lt)

    def _create_lab_orders(self):
        from apps.laboratory.models import LabOrder, LabOrderItem
        self.stdout.write('  >> Création des commandes de laboratoire...')
        now = timezone.now()

        orders_data = [
            (self.patients[0], self.doctor1, -5,  'PUBLISHED', 'NORMAL',  [('HBA1C', '9.2', True), ('GLY', '12.3', True)]),
            (self.patients[1], self.doctor2, -10, 'VALIDATED', 'NORMAL',  [('NFS', '8.5', False), ('CRP', '22', True)]),
            (self.patients[2], self.doctor1, -3,  'RESULTED',  'URGENT',  [('NFS', '14.2', True), ('CRP', '85', True)]),
            (self.patients[4], self.doctor2, -7,  'PUBLISHED', 'URGENT',  [('TROPO', '55', True), ('NFS', '7.1', False)]),
            (self.patients[8], self.doctor1, -14, 'PUBLISHED', 'NORMAL',  [('CHOL', '6.8', True), ('CREAT', '95', False)]),
            (self.patients[9], self.doctor2, -1,  'IN_PROGRESS','URGENT', [('TROPO', None, None), ('DDFRAG', None, None)]),
            (self.patients[10],self.doctor1, -20, 'PUBLISHED', 'NORMAL',  [('CREAT', '250', True), ('IONOG', '138/4.2', False)]),
            (self.patients[11],self.doctor2, -30, 'PUBLISHED', 'NORMAL',  [('TSH', '8.5', True)]),
            (self.patients[3], self.doctor1,  0,  'ORDERED',   'ROUTINE', [('NFS', None, None), ('GLY', None, None), ('CHOL', None, None)]),
            (self.patients[5], self.doctor1, -2,  'SAMPLED',   'NORMAL',  [('NFS', None, None), ('CRP', None, None)]),
        ]

        self.lab_orders = []
        for pat, doc, day_delta, status, priority, items in orders_data:
            order_dt = now + timedelta(days=day_delta)
            order, _ = LabOrder.objects.get_or_create(
                patient=pat, ordered_by=doc, status=status,
                defaults=dict(
                    priority=priority,
                    clinical_notes='Analyse dans le cadre du suivi habituel.',
                    assigned_to=self.bio,
                    sampled_at=order_dt + timedelta(hours=2) if status not in ('ORDERED',) else None,
                    validated_by=self.bio if status in ('VALIDATED', 'PUBLISHED') else None,
                    validated_at=order_dt + timedelta(hours=6) if status in ('VALIDATED', 'PUBLISHED') else None,
                    published_at=order_dt + timedelta(hours=8) if status == 'PUBLISHED' else None,
                )
            )
            self.lab_orders.append(order)
            for code, value, abnormal in items:
                test = next((t for t in self.lab_tests if t.code == code), None)
                if test:
                    LabOrderItem.objects.get_or_create(
                        order=order, test=test,
                        defaults=dict(
                            result_value=value or '',
                            result_unit=test.unit,
                            is_abnormal=abnormal or False,
                            resulted_at=order_dt + timedelta(hours=5) if value else None,
                        )
                    )

    # ─── Médicaments ──────────────────────────────────────────────────────────

    def _create_medications(self):
        from apps.pharmacy.models import Medication, MedicationBatch, StockMovement
        self.stdout.write('  >> Création des médicaments et stocks...')

        meds_data = [
            ('Metformine', 'Metformine', 'Antidiabétique', 'Comprimé', '500 mg', 'comprimés', 100, '0.08'),
            ('Amlodipine', 'Amlodipine', 'Antihypertenseur', 'Comprimé', '5 mg', 'comprimés', 50, '0.15'),
            ('Ramipril', 'Ramipril', 'IEC', 'Comprimé', '5 mg', 'comprimés', 50, '0.12'),
            ('Furosémide', 'Furosémide', 'Diurétique', 'Comprimé', '40 mg', 'comprimés', 80, '0.05'),
            ('Bisoprolol', 'Bisoprolol', 'Bêta-bloquant', 'Comprimé', '5 mg', 'comprimés', 60, '0.18'),
            ('Salbutamol', 'Salbutamol', 'Bronchodilatateur', 'Aérosol', '100 µg', 'bouffées', 30, '4.50'),
            ('Budésonide/Formotérol', 'Budésonide + Formotérol', 'Corticoïde inhalé', 'Aérosol', '160/4,5 µg', 'bouffées', 20, '18.00'),
            ('Levothyroxine', 'Lévothyroxine sodique', 'Hormones thyroïdiennes', 'Comprimé', '50 µg', 'comprimés', 50, '0.09'),
            ('Aspirine', 'Acide acétylsalicylique', 'Antiagrégant', 'Comprimé', '100 mg', 'comprimés', 100, '0.04'),
            ('Montélukast', 'Montélukast', 'Anti-asthmatique', 'Comprimé', '10 mg', 'comprimés', 50, '0.75'),
            ('Paracétamol', 'Paracétamol', 'Antalgique', 'Comprimé', '1000 mg', 'comprimés', 200, '0.06'),
            ('Amoxicilline', 'Amoxicilline', 'Antibiotique', 'Gélule', '500 mg', 'gélules', 50, '0.22'),
        ]
        self.medications = []
        for name, generic, cat, form, strength, unit, threshold, price in meds_data:
            med, _ = Medication.objects.get_or_create(
                name=name,
                defaults=dict(generic_name=generic, category=cat, dosage_form=form,
                              strength=strength, unit=unit, reorder_threshold=threshold,
                              unit_price=Decimal(price), is_active=True)
            )
            self.medications.append(med)
            batch, created = MedicationBatch.objects.get_or_create(
                medication=med, batch_number=f'LOT-2025-{med.name[:3].upper()}01',
                defaults=dict(
                    quantity=500, supplier='Cerp Rouen',
                    expiry_date=date(2027, 6, 30),
                    purchase_price=Decimal(price) * Decimal('0.7'),
                    received_at=timezone.now() - timedelta(days=60),
                    is_active=True,
                )
            )
            if created:
                StockMovement.objects.create(
                    batch=batch, movement_type='IN', quantity=500,
                    reference='BON-RECEPT-001', performed_by=self.pharma,
                    notes='Réception initiale'
                )

    # ─── Facturation ──────────────────────────────────────────────────────────

    def _create_invoices(self):
        from apps.billing.models import Invoice, InvoiceItem, Payment, AccountingEntry
        self.stdout.write('  >> Création des factures...')
        now = timezone.now()

        invoices_data = [
            (self.patients[0], 'PAID',           'MGEN',    75.00,   75.00,  30.00, [('CONSULTATION', 'Consultation médecin généraliste', 1, 30), ('LAB', 'Bilan HbA1c + glycémie', 1, 26), ('PROCEDURE', 'ECG de repos', 1, 19)]),
            (self.patients[1], 'PAID',           'AXA Santé',95.00, 95.00,  50.00, [('CONSULTATION', 'Consultation cardiologie', 1, 45), ('LAB', 'Bilan cardio complet (NFS, CRP)', 1, 36), ('PROCEDURE', 'Échocardiographie', 1, 14)]),
            (self.patients[2], 'PARTIALLY_PAID', '',        120.00,  60.00,   0.00, [('CONSULTATION', 'Consultation pneumologie', 1, 45), ('HOSPITALIZATION', 'Hospitalisation 3 jours', 3, 25), ('PROCEDURE', 'Spirométrie', 1, 50)]),
            (self.patients[4], 'ISSUED',         'Harmonie Mutuelle', 280.00, 0.00, 150.00, [('HOSPITALIZATION', 'Hospitalisation soins intensifs cardiologie', 5, 50), ('MEDICATION', 'Furosémide IV perfusion', 10, 3), ('PROCEDURE', 'Écho cardiaque doppler', 1, 80)]),
            (self.patients[8], 'PAID',           '',         60.00,  60.00,   0.00, [('CONSULTATION', 'Consultation HTA', 1, 30), ('LAB', 'Bilan lipidique + créatinine', 1, 24), ('MEDICATION', 'Amlodipine 1 mois', 30, 0.20)]),
            (self.patients[6], 'PAID',           'Malakoff Humanis', 310.00, 310.00, 200.00, [('HOSPITALIZATION', 'Hospitalisation rhumatologie 7 jours', 7, 30), ('PROCEDURE', 'Ponction articulaire', 1, 120), ('MEDICATION', 'Corticoïdes IV', 5, 8)]),
            (self.patients[10],'DRAFT',          '',        180.00,   0.00,   0.00, [('HOSPITALIZATION', 'Hospitalisation néphologie', 2, 50), ('LAB', 'Bilan rénal complet', 1, 22), ('PROCEDURE', 'Dialyse séance 1', 1, 108)]),
            (self.patients[3], 'ISSUED',         '',         55.00,   0.00,   0.00, [('CONSULTATION', 'Bilan de santé général', 1, 30), ('LAB', 'NFS + bilan général', 1, 25)]),
        ]

        for pat, status, insurer, total, paid, insurance, items in invoices_data:
            inv, _ = Invoice.objects.get_or_create(
                patient=pat, status=status,
                defaults=dict(
                    issued_by=self.account,
                    insurance_provider=insurer,
                    insurance_coverage=Decimal(str(insurance)),
                    subtotal=Decimal(str(total)),
                    total=Decimal(str(total)),
                    amount_paid=Decimal(str(paid)),
                )
            )
            for itype, desc, qty, uprice in items:
                InvoiceItem.objects.get_or_create(
                    invoice=inv, description=desc,
                    defaults=dict(item_type=itype, quantity=qty, unit_price=Decimal(str(uprice)),
                                  discount_percent=Decimal('0'))
                )
            if paid > 0:
                Payment.objects.get_or_create(
                    invoice=inv, amount=Decimal(str(paid)),
                    defaults=dict(method='CARD', received_by=self.recept,
                                  notes='Paiement par carte bancaire')
                )

    # ─── Messagerie ───────────────────────────────────────────────────────────

    def _create_messaging(self):
        from apps.messaging.models import Conversation, Message
        self.stdout.write('  >> Création des messages...')
        now = timezone.now()

        conv_data = [
            (
                'Résultats analyses M. Fontaine',
                [self.doctor1, self.admin],
                [
                    (self.doctor1, -2, 'Bonjour, les résultats d\'HbA1c de M. Fontaine sont à 9.2%. Il faut ajuster le traitement. Je prévois une consultation la semaine prochaine.'),
                    (self.admin,   -1, 'Bien reçu. Je note le rendez-vous. Souhaitez-vous que je contacte le patient pour prévenir ?'),
                    (self.doctor1,  0, 'Oui merci, prévenez-le et assurez-vous qu\'il prend son traitement correctement.'),
                ]
            ),
            (
                'Admission urgence — Patient Chevalier',
                [self.doctor2, self.nurse1, self.recept],
                [
                    (self.recept,  -5, 'M. Chevalier vient d\'arriver aux urgences pour une crise rhumatismale sévère. Douleur VAS 8/10.'),
                    (self.doctor2, -5, 'Je prends en charge. Préparez une chambre en rhumato et lancez le bilan inflammatoire complet.'),
                    (self.nurse1,  -5, 'Chambre 201-L1 prête. Bilan commandé au laboratoire. Patient installé sous O2.'),
                    (self.doctor2, -4, 'Bonne prise en charge. Administrez Méthylprednisolone 80mg IV et appliquez le protocole douleur.'),
                ]
            ),
            (
                'Planning soins semaine 28',
                [self.nurse1, self.nurse2, self.doctor1],
                [
                    (self.nurse1,  -3, 'Bonjour à tous. Rappel : semaine 28, 3 patients en hospitalisation active. Veuillez confirmer vos créneaux.'),
                    (self.nurse2,  -3, 'Je prends les gardes de nuit lundi et mercredi. Marie, tu gères les matins ?'),
                    (self.nurse1,  -2, 'Confirmé. Dr Martin, serez-vous disponible pour la visite quotidienne à 9h ?'),
                    (self.doctor1, -2, 'Oui, je serai là de 9h à 11h chaque matin cette semaine.'),
                ]
            ),
            (
                'Stock Furosémide — alerte réapprovisionnement',
                [self.pharma, self.admin],
                [
                    (self.pharma, -1, 'Alerte stock : Furosémide 40mg sous le seuil critique (45 unités restantes). Commande urgente nécessaire.'),
                    (self.admin,  -1, 'Commande passée auprès de Cerp Rouen. Livraison prévue dans 48h. Numéro de commande : CMD-2026-0089.'),
                ]
            ),
        ]

        for subject, participants, messages in conv_data:
            conv, _ = Conversation.objects.get_or_create(
                subject=subject,
                defaults=dict(is_active=True)
            )
            conv.participants.set(participants)
            for sender, day_delta, content in messages:
                sent_at = now + timedelta(days=day_delta)
                Message.objects.get_or_create(
                    conversation=conv, sender=sender, content=content[:50],
                    defaults=dict(content=content, is_read=True, read_at=sent_at + timedelta(hours=1))
                )

