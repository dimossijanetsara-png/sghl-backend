from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='otp_code',
            field=models.CharField(blank=True, max_length=6),
        ),
        migrations.AddField(
            model_name='user',
            name='otp_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='otp_verified',
            field=models.BooleanField(default=False),
        ),
    ]
