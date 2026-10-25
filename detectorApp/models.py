from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Extension du modèle User Django avec Super Manager et classes assignées."""
    is_super_manager = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return f"{self.get_full_name() or self.username}"


class ClassRoom(models.Model):
    """Une classe/groupe/spécialité (ex: 'Master Data Science')."""
    name = models.CharField("Nom", max_length=100)
    description = models.TextField("Description", blank=True)
    users = models.ManyToManyField(
        User,
        related_name="accessible_classes",
        blank=True,
        verbose_name="Utilisateurs assignés"
    )

    class Meta:
        verbose_name = "Classe"
        verbose_name_plural = "Classes"

    def __str__(self):
        return self.name


class Student(models.Model):
    """Élève enrôlé avec son visage de référence."""
    name = models.CharField("Nom", max_length=200)
    classroom = models.ForeignKey(
        ClassRoom,
        on_delete=models.CASCADE,
        related_name="students",
        verbose_name="Classe"
    )
    face_image = models.ImageField(
        "Visage recadré",
        upload_to="students/",
        null=True,
        blank=True
    )
    face_encoding = models.JSONField("Encodage facial", null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Créé par"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Élève"
        verbose_name_plural = "Élèves"

    def __str__(self):
        return f"{self.name} ({self.classroom.name})"


class PendingFace(models.Model):
    face_image = models.ImageField("Visage recadré", upload_to="pending_faces/")
    face_encoding = models.JSONField("Encodage facial")
    source_image = models.ImageField("Photo source", upload_to="pending_faces/")
    classroom = models.ForeignKey(ClassRoom, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Classe présélectionnée")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Créé par")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Visage en attente"
        verbose_name_plural = "Visages en attente"


class AttendanceCheck(models.Model):
    """Session de reconnaissance (check) – photo uploadée + comparaison."""
    source_image = models.ImageField(
        "Photo de classe",
        upload_to="attendance_photos/"
    )
    original_image = models.ImageField(
        "Photo originale",
        upload_to="attendance_photos/",
        null=True,
        blank=True
    )
    classrooms = models.ManyToManyField(
        ClassRoom,
        related_name="checks",
        verbose_name="Classes concernées"
    )
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Effectué par"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Session de reconnaissance"
        verbose_name_plural = "Sessions de reconnaissance"


class Report(models.Model):
    attendance_check = models.OneToOneField(
        AttendanceCheck,
        on_delete=models.CASCADE,
        related_name="report",
        verbose_name="Check associé"
    )
    present_students = models.ManyToManyField(
        Student,
        related_name="reports_present",
        verbose_name="Élèves présents"
    )
    absent_students = models.ManyToManyField(
        Student,
        related_name="reports_absent",
        verbose_name="Élèves absents"
    )
    unidentified_faces = models.JSONField(
        "Visages non identifiés",
        default=list,
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Rapport"
        verbose_name_plural = "Rapports"

    def __str__(self):
        return f"Rapport du {self.created_at.strftime('%d/%m/%Y %H:%M')}"