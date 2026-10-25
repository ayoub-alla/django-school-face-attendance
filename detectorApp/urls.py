from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='detectorApp/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('', views.dashboard, name='dashboard'),

    path('users/', views.users, name='users'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),

    path('classrooms/', views.classrooms, name='classrooms'),
    path('classrooms/create/', views.classroom_create, name='classroom_create'),
    path('classrooms/<int:pk>/edit/', views.classroom_edit, name='classroom_edit'),
    path('classrooms/<int:pk>/delete/', views.classroom_delete, name='classroom_delete'),

    path('students/', views.students_list, name='students_list'),
    path('students/<int:pk>/delete/', views.student_delete, name='student_delete'),
    path('students/enroll/', views.enroll, name='enroll'),
    path('students/enroll/upload/', views.enroll_upload, name='enroll_upload'),
    path('students/enroll/validate/', views.enroll_validate, name='enroll_validate'),
    path('students/enroll/reject/', views.enroll_reject, name='enroll_reject'),
    path('students/enroll/api/', views.enroll_api, name='enroll_api'),

    path('check/', views.check, name='check'),
    path('check/run/', views.check_run, name='check_run'),
    path('check/confirm/', views.check_confirm, name='check_confirm'),

    path('reports/', views.reports_list, name='reports_list'),
    path('reports/<int:pk>/', views.report_detail, name='report_detail'),
    path('reports/<int:pk>/delete/', views.report_delete, name='report_delete'),
    path('reports/<int:pk>/pdf/', views.report_pdf, name='report_pdf'),
    path('reports/<int:pk>/excel/', views.report_excel, name='report_excel'),
]