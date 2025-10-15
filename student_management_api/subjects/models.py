from django.db import models
from teachers.models import TeacherProfile
from classes.models import Class

class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class ClassSubject(models.Model):
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='subjects')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='class_links')
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='subject_classes')

    class Meta:
        unique_together = ('class_assigned', 'subject')

    def __str__(self):
        return f"{self.class_assigned} - {self.subject.name}"
