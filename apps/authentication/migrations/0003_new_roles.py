from django.db import migrations
import django.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0002_user_otp_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=django.db.models.fields.CharField(
                choices=[
                    ('ADMIN', 'Superutilisateur'),
                    ('DOCTOR', 'Médecin'),
                    ('NURSE', 'Infirmier(e)'),
                    ('BIOLOGIST', 'Biologiste'),
                    ('PHARMACIST', 'Pharmacien(ne)'),
                    ('RECEPTIONIST', 'Secrétaire / Réceptionniste'),
                    ('ACCOUNTANT', 'Comptable'),
                    ('PATIENT', 'Patient'),
                    ('LABTECH', 'Technicien(ne) de laboratoire'),
                    ('OTHER', 'Autre personnel'),
                ],
                default='PATIENT',
                max_length=20,
            ),
        ),
    ]
