# Generated by Django 5.1.1 on 2024-09-26 23:44

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0003_patient_lab_tests_patient_vital_signs_patient_weight"),
    ]

    operations = [
        migrations.CreateModel(
            name="PatientRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "request_type",
                    models.CharField(
                        choices=[
                            ("appointment", "Appointment Change"),
                            ("medication", "Medication Change"),
                        ],
                        max_length=20,
                    ),
                ),
                ("details", models.TextField()),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="chat.patient"
                    ),
                ),
            ],
        ),
    ]
