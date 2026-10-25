from django.contrib import admin
from .models import User, ClassRoom, Student, PendingFace, AttendanceCheck, Report

admin.site.register(User)
admin.site.register(ClassRoom)
admin.site.register(Student)
admin.site.register(PendingFace)
admin.site.register(AttendanceCheck)
admin.site.register(Report)