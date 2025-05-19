# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='schedule',
            name='slot_duration',
            field=models.IntegerField(choices=[(30, '30 minutes'), (60, '1 hour'), (90, '1 hour 30 minutes'), (120, '2 hours')], default=30),
        ),
        migrations.AddField(
            model_name='schedule',
            name='is_available',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='appointment',
            name='end_time',
            field=models.TimeField(null=True),
        ),
        migrations.AlterField(
            model_name='appointment',
            name='status',
            field=models.CharField(choices=[('CONFIRMED', 'Confirmed'), ('CANCELLED', 'Cancelled'), ('COMPLETED', 'Completed')], default='CONFIRMED', max_length=20),
        ),
        migrations.AlterField(
            model_name='appointment',
            name='reason',
            field=models.TextField(),
        ),
    ] 