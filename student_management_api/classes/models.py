from django.db import models
from teachers.models import TeacherProfile
from students.models import StudentProfile

class Class(models.Model):
    name = models.CharField(max_length=50)
    section = models.CharField(max_length=10)
    class_teacher = models.ForeignKey(
        TeacherProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='class_teacher'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('name', 'section')
        verbose_name_plural = "Classes"

    def __str__(self):
        return f"{self.name} - {self.section}"


class Enrollment(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='enrollments')
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='enrollments')
    joined_date = models.DateField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('student', 'class_assigned')

    def __str__(self):
        return f"{self.student.user.username} → {self.class_assigned}"
