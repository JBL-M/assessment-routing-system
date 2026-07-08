from django.db import migrations, models


def normalize_attachment_types(apps, schema_editor):
    Profile = apps.get_model('users', 'Profile')

    Profile.objects.filter(attachment_type__in=['industrial', 'internship']).update(
        attachment_type='work_based'
    )
    Profile.objects.filter(attachment_type__in=['research', 'fieldwork', 'other']).update(
        attachment_type='service_based'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_profile_organization_latitude_and_more'),
    ]

    operations = [
        migrations.RunPython(normalize_attachment_types, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='profile',
            name='attachment_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('service_based', 'Service-Based Learning'),
                    ('work_based', 'Work-Based Learning'),
                ],
                max_length=30,
            ),
        ),
    ]
