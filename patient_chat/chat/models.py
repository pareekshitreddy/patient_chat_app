from django.db import models

class Patient(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField()
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    medical_condition = models.CharField(max_length=100)
    medication_regimen = models.TextField()
    last_appointment = models.DateTimeField()
    next_appointment = models.DateTimeField()
    doctor_name = models.CharField(max_length=100)
    lab_tests = models.TextField(null=True, blank=True)
    vital_signs = models.TextField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    class Meta:
        unique_together = ('first_name', 'last_name', 'date_of_birth')

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Message(models.Model):
    sender = models.CharField(max_length=10)  # 'patient' or 'bot'
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
class PatientRequest(models.Model):
    REQUEST_TYPES = [
        ('appointment', 'Appointment Change'),
        ('medication', 'Medication Change'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    details = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient} - {self.request_type} at {self.timestamp}"

