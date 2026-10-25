from django.shortcuts import render , redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import User, ClassRoom, PendingFace, Student, AttendanceCheck, Report

from .recognition.face_engine import detect_faces, compare_encoding
from django.db import models


import json
import os
import uuid , shutil
from datetime import datetime
from django.conf import settings

import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image






@login_required
def dashboard(request):
    user = request.user
    
    if user.is_super_manager:
        total_classes = ClassRoom.objects.count()
        total_students = Student.objects.count()
        total_checks = AttendanceCheck.objects.count()
        total_reports = Report.objects.count()
        
        # Statistiques globales
        total_present = sum(r.present_students.count() for r in Report.objects.all())
        total_absent = sum(r.absent_students.count() for r in Report.objects.all())
        total_unidentified = sum(len(r.unidentified_faces or []) for r in Report.objects.all())
        
        # Derniers rapports
        recent_reports = Report.objects.select_related(
            'attendance_check__performed_by'
        ).prefetch_related(
            'present_students', 'absent_students'
        ).order_by('-created_at')[:5]
        
        # Classes avec le plus d'élèves
        top_classes = ClassRoom.objects.annotate(
            student_count= models.Count('students')
        ).order_by('-student_count')[:5]
        
    else:
        accessible_classes = user.accessible_classes.all()
        total_classes = accessible_classes.count()
        total_students = Student.objects.filter(classroom__in=accessible_classes).count()
        total_checks = AttendanceCheck.objects.filter(classrooms__in=accessible_classes).count()
        total_reports = Report.objects.filter(
            attendance_check__classrooms__in=accessible_classes
        ).count()
        
        # Statistiques limitées à ses classes
        user_reports = Report.objects.filter(
            attendance_check__classrooms__in=accessible_classes
        )
        total_present = sum(r.present_students.count() for r in user_reports)
        total_absent = sum(r.absent_students.count() for r in user_reports)
        total_unidentified = sum(len(r.unidentified_faces or []) for r in user_reports)
        
        recent_reports = user_reports.select_related(
            'attendance_check__performed_by'
        ).prefetch_related(
            'present_students', 'absent_students'
        ).order_by('-created_at')[:5]
        
        top_classes = accessible_classes.annotate(
            student_count=models.Count('students')
        ).order_by('-student_count')[:5]

    return render(request, 'detectorApp/dashboard.html', {
        'total_classes': total_classes,
        'total_students': total_students,
        'total_checks': total_checks,
        'total_reports': total_reports,
        'total_present': total_present,
        'total_absent': total_absent,
        'total_unidentified': total_unidentified,
        'recent_reports': recent_reports,
        'top_classes': top_classes,
    })

@login_required
def users(request):
    return render(request, 'detectorApp/users.html')

@login_required
def classrooms(request):
    return render(request, 'detectorApp/classrooms.html')

@login_required
def enroll(request):
    return render(request, 'detectorApp/students/enroll.html')

@login_required
def check(request):
    if request.user.is_super_manager:
        classrooms = ClassRoom.objects.all()
    else:
        classrooms = request.user.accessible_classes.all()
    return render(request, 'detectorApp/attendance/check.html', {
        'classrooms': classrooms,
    })

@login_required
def reports_list(request):
    return render(request, 'detectorApp/reports/list.html')

def is_super_manager(user):
    return user.is_super_manager

@login_required
@user_passes_test(is_super_manager)
def users(request):
    users_list = User.objects.all()
    classrooms = ClassRoom.objects.all()
    return render(request, 'detectorApp/users.html', {
        'users': users_list,
        'classrooms': classrooms,
    })

@login_required
@user_passes_test(is_super_manager)
def user_create(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email', '')
        password = request.POST.get('password')
        class_ids = request.POST.getlist('classes')
        user = User.objects.create_user(username=username, email=email, password=password)
        user.accessible_classes.set(class_ids)
        messages.success(request, "Utilisateur créé avec succès.")
    return redirect('users')

@login_required
@user_passes_test(is_super_manager)
def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.username = request.POST.get('username')
        user.email = request.POST.get('email', '')
        password = request.POST.get('password')
        if password:
            user.set_password(password)
        user.save()
        class_ids = request.POST.getlist('classes')
        user.accessible_classes.set(class_ids)
        messages.success(request, "Utilisateur modifié.")
    return redirect('users')

@login_required
@user_passes_test(is_super_manager)
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user.is_super_manager:
        messages.error(request, "Impossible de supprimer le Super Manager.")
    else:
        user.delete()
        messages.success(request, "Utilisateur supprimé.")
    return redirect('users')

@login_required
def classrooms(request):
    if request.user.is_super_manager:
        classes = ClassRoom.objects.all()
    else:
        classes = request.user.accessible_classes.all()
    return render(request, 'detectorApp/classrooms.html', {'classes': classes})

@login_required
def classroom_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        ClassRoom.objects.create(name=name, description=description)
        messages.success(request, "Classe créée.")
    return redirect('classrooms')

@login_required
def classroom_edit(request, pk):
    classroom = get_object_or_404(ClassRoom, pk=pk)
    if request.method == 'POST':
        classroom.name = request.POST.get('name')
        classroom.description = request.POST.get('description', '')
        classroom.save()
        messages.success(request, "Classe modifiée.")
    return redirect('classrooms')

@login_required
def classroom_delete(request, pk):
    classroom = get_object_or_404(ClassRoom, pk=pk)
    classroom.delete()
    messages.success(request, "Classe supprimée.")
    return redirect('classrooms')


@login_required
def enroll(request):
    if request.user.is_super_manager:
        pending_faces = PendingFace.objects.all()
        classrooms = ClassRoom.objects.all()
    else:
        pending_faces = PendingFace.objects.filter(created_by=request.user)
        classrooms = request.user.accessible_classes.all()
    return render(request, 'detectorApp/students/enroll.html', {
        'pending_faces': pending_faces,
        'classrooms': classrooms,
    })

@require_POST
@login_required
def enroll_upload(request):
    image = request.FILES.get('image')
    classroom_id = request.POST.get('classroom')
    
    if not image:
        return JsonResponse({'success': False, 'error': 'Aucune image fournie.'})

    try:
        faces = detect_faces(image)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Erreur de détection : {str(e)}'})

    if not faces:
        return JsonResponse({'success': False, 'error': 'Aucun visage détecté.'})

    classroom = None
    if classroom_id:
        try:
            classroom = ClassRoom.objects.get(pk=classroom_id)
        except ClassRoom.DoesNotExist:
            pass

    created = []
    for face in faces:
        pending = PendingFace.objects.create(
            face_image=face['face_image'],
            face_encoding=face['encoding'],
            classroom=classroom,
            created_by=request.user,
        )
        created.append({
            'id': pending.id,
            'image_url': pending.face_image.url,
            'classroom_name': classroom.name if classroom else None,
            'classroom_id': classroom.id if classroom else None,
        })

    return JsonResponse({'success': True, 'faces': created, 'count': len(created)})

@require_POST
@login_required
def enroll_validate(request):
    data = json.loads(request.body)
    pending_id = data.get('id')
    name = data.get('name')
    classroom_id = data.get('classroom')

    try:
        pending = PendingFace.objects.get(pk=pending_id)
    except PendingFace.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Visage introuvable.'})

    if not name:
        return JsonResponse({'success': False, 'error': 'Nom requis.'})

    try:
        classroom = ClassRoom.objects.get(pk=classroom_id) if classroom_id else pending.classroom
    except ClassRoom.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Classe introuvable.'})

    student = Student.objects.create(
        name=name,
        classroom=classroom,
        face_image=pending.face_image,
        face_encoding=pending.face_encoding,
        created_by=request.user,
    )
    pending.delete()

    return JsonResponse({'success': True, 'student_name': name, 'classroom_name': classroom.name})

@require_POST
@login_required
def enroll_reject(request):
    data = json.loads(request.body)
    pending_id = data.get('id')
    try:
        pending = PendingFace.objects.get(pk=pending_id)
        pending.delete()
        return JsonResponse({'success': True})
    except PendingFace.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Visage introuvable.'})

@login_required
def enroll_api(request):
    if request.user.is_super_manager:
        pending_faces = PendingFace.objects.all()
    else:
        pending_faces = PendingFace.objects.filter(created_by=request.user)
    
    faces_data = []
    for face in pending_faces:
        faces_data.append({
            'id': face.id,
            'image_url': face.face_image.url,
            'classroom': face.classroom.id if face.classroom else None,
            'classroom_name': face.classroom.name if face.classroom else 'Non assignée',
            'showForm': False,
            'name': '',
            'saving': False,
        })
    return JsonResponse({'faces': faces_data})

@login_required
def students_list(request):
    if request.user.is_super_manager:
        students = Student.objects.select_related('classroom', 'created_by').all()
    else:
        students = Student.objects.filter(
            classroom__in=request.user.accessible_classes.all()
        ).select_related('classroom', 'created_by')
    return render(request, 'detectorApp/students/list.html', {
        'students': students,
    })

@login_required
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    # Check permission: only super_manager or if user has access to the student's classroom
    if not request.user.is_super_manager and student.classroom not in request.user.accessible_classes.all():
        messages.error(request, "Vous n'avez pas la permission de supprimer cet élève.")
        return redirect('students_list')
    student.delete()
    messages.success(request, f"Élève '{student.name}' supprimé.")
    return redirect('students_list')

def draw_annotations(image_path, face_data, output_path):
    """
    Draw rectangles and labels on the source image.
    face_data: list of dicts with 'location', 'name', 'confidence', 'status'
    """
    img = cv2.imread(image_path)
    if img is None:
        return False

    font = cv2.FONT_HERSHEY_SIMPLEX
    for face in face_data:
        top, right, bottom, left = face['location']
        color = (21, 128, 61) if face['status'] == 'present' else (180, 28, 28) if face['status'] == 'absent' else (180, 83, 9)
        
        # Draw rectangle
        cv2.rectangle(img, (left, top), (right, bottom), color, 2)
        
        # Prepare label
        if face['name']:
            label = f"{face['name']} ({face['confidence']:.0f}%)"
            if face.get('classroom_name'):
                label += f" | {face['classroom_name']}"
        else:
            label = "Non identifié"
        
        # Text background
        (text_w, text_h), _ = cv2.getTextSize(label, font, 0.5, 1)
        cv2.rectangle(img, (left, top - text_h - 8), (left + text_w + 8, top), color, -1)
        
        # Text
        cv2.putText(img, label, (left + 4, top - 4), font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    
    cv2.imwrite(output_path, img)
    return True

@require_POST
@login_required
def check_run(request):
    import json, os, uuid, shutil
    from datetime import datetime
    from django.conf import settings

    image = request.FILES.get('image')
    classrooms_data = request.POST.get('classrooms', '[]')
    
    try:
        classroom_ids = json.loads(classrooms_data)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Données de classes invalides.'})

    if not image:
        return JsonResponse({'success': False, 'error': 'Aucune image fournie.'})
    if not classroom_ids:
        return JsonResponse({'success': False, 'error': 'Sélectionnez au moins une classe.'})

    session_id = str(uuid.uuid4())[:8]
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'attendance_photos', 'temp', session_id)
    os.makedirs(temp_dir, exist_ok=True)

    # Save raw source image temporarily
    source_raw_path = os.path.join(temp_dir, "source_raw.jpg")
    with open(source_raw_path, 'wb+') as dest:
        for chunk in image.chunks():
            dest.write(chunk)

    # Detect faces
    image.seek(0)
    try:
        detected_faces = detect_faces(image)
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JsonResponse({'success': False, 'error': f'Erreur de détection : {str(e)}'})

    if not detected_faces:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JsonResponse({'success': False, 'error': 'Aucun visage détecté.'})

    # Get enrolled students
    classrooms = ClassRoom.objects.filter(id__in=classroom_ids)
    enrolled_students = Student.objects.filter(
        classroom__in=classrooms,
        face_encoding__isnull=False
    ).select_related('classroom')

    known_encodings = [s.face_encoding for s in enrolled_students]
    known_students = list(enrolled_students)
    matched_student_ids = set()

    present_faces = []
    unidentified_faces = []
    annotation_data = []  # For drawing on source image

    for idx, face in enumerate(detected_faces):
        # Save cropped face
        face_filename = f"face_{idx}.jpg"
        face_path = os.path.join(temp_dir, face_filename)
        with open(face_path, 'wb+') as dest:
            for chunk in face['face_image'].chunks():
                dest.write(chunk)

        face_url = settings.MEDIA_URL + f"attendance_photos/temp/{session_id}/{face_filename}"

        # Compare
        match_idx, distance = compare_encoding(face['encoding'], known_encodings)
        if match_idx is not None:
            student = known_students[match_idx]
            matched_student_ids.add(student.id)
            confidence = max(0, min(100, (1 - distance) * 100))
            present_faces.append({
                'id': student.id,
                'face_image': face_url,
                'name': student.name,
                'student_photo': student.face_image.url if student.face_image else None,
                'confidence': round(confidence, 1),
                'classroom_name': student.classroom.name,
            })
            annotation_data.append({
                'location': face['location'],
                'name': student.name,
                'confidence': confidence,
                'status': 'present',
                'classroom_name': student.classroom.name,
            })
        else:
            unidentified_faces.append({
                'id': idx,
                'face_image': face_url,
                'confidence': 0,
                'classroom_name': '',
            })
            annotation_data.append({
                'location': face['location'],
                'name': None,
                'confidence': 0,
                'status': 'unidentified',
            })

    # Absent students
    absent_students = []
    for s in enrolled_students:
        if s.id not in matched_student_ids:
            absent_students.append({
                'id': s.id,
                'name': s.name,
                'classroom': s.classroom.name,
                'face_image': s.face_image.url if s.face_image else None,
            })

    # Draw annotations on source image
    annotated_filename = f"annotated_{session_id}.jpg"
    annotated_path = os.path.join(temp_dir, annotated_filename)
    draw_annotations(source_raw_path, annotation_data, annotated_path)

    annotated_url = settings.MEDIA_URL + f"attendance_photos/temp/{session_id}/{annotated_filename}"

    return JsonResponse({
        'success': True,
        'session_id': session_id,
        'source_image_url': annotated_url,  # <-- Annotated image URL
        'present_faces': present_faces,
        'unidentified_faces': unidentified_faces,
        'absent_students': absent_students,
        'present_count': len(present_faces),
        'absent_count': len(absent_students),
        'unidentified_count': len(unidentified_faces),
    })

@require_POST
@login_required
def check_confirm(request):
    import json, os, shutil
    from datetime import datetime
    from django.conf import settings

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Données invalides.'})

    session_id = data.get('session_id')
    present_ids = data.get('present_ids', [])
    absent_ids = data.get('absent_ids', [])
    unidentified_ids = data.get('unidentified_ids', [])

    if not session_id:
        return JsonResponse({'success': False, 'error': 'Session invalide.'})

    temp_dir = os.path.join(settings.MEDIA_ROOT, 'attendance_photos', 'temp', session_id)
    if not os.path.exists(temp_dir):
        return JsonResponse({'success': False, 'error': 'Session expirée. Veuillez refaire l\'analyse.'})

    try:
        # === SAUVEGARDE DE L'IMAGE ANNOTÉE ===
        annotated_temp = os.path.join(temp_dir, f"annotated_{session_id}.jpg")
        if not os.path.exists(annotated_temp):
            annotated_temp = os.path.join(temp_dir, f"source_raw.jpg")
            
        if not os.path.exists(annotated_temp):
            shutil.rmtree(temp_dir, ignore_errors=True)
            return JsonResponse({'success': False, 'error': 'Image source introuvable.'})

        annotated_filename = f"annotated_{request.user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{session_id}.jpg"
        annotated_path = os.path.join(settings.MEDIA_ROOT, 'attendance_photos', annotated_filename)
        os.makedirs(os.path.dirname(annotated_path), exist_ok=True)
        shutil.copy(annotated_temp, annotated_path)

        # === SAUVEGARDE DE L'IMAGE ORIGINALE ===
        source_raw_temp = os.path.join(temp_dir, "source_raw.jpg")
        original_filename = f"original_{request.user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{session_id}.jpg"
        original_path = os.path.join(settings.MEDIA_ROOT, 'attendance_photos', original_filename)
        
        if os.path.exists(source_raw_temp):
            shutil.copy(source_raw_temp, original_path)
        else:
            shutil.copy(annotated_temp, original_path)

        # === CRÉATION DE L'AttendanceCheck AVEC LES DEUX IMAGES ===
        check_obj = AttendanceCheck.objects.create(
            source_image=f"attendance_photos/{annotated_filename}",
            original_image=f"attendance_photos/{original_filename}",
            performed_by=request.user,
        )

        # === AJOUT DES CLASSES ===
        present_students = Student.objects.filter(id__in=present_ids)
        absent_students = Student.objects.filter(id__in=absent_ids)

        classrooms = set()
        for s in list(present_students) + list(absent_students):
            classrooms.add(s.classroom)
        check_obj.classrooms.set(classrooms)

        # === SAUVEGARDE DES VISAGES NON IDENTIFIÉS ===
        unidentified_urls = []
        for uid in unidentified_ids:
            crop_temp = os.path.join(temp_dir, f"face_{uid}.jpg")
            if os.path.exists(crop_temp):
                crop_final_name = f"unidentified_{session_id}_{uid}.jpg"
                crop_final_path = os.path.join(settings.MEDIA_ROOT, 'reports', 'unidentified', crop_final_name)
                os.makedirs(os.path.dirname(crop_final_path), exist_ok=True)
                shutil.move(crop_temp, crop_final_path)
                unidentified_urls.append(settings.MEDIA_URL + f"reports/unidentified/{crop_final_name}")

        # === CRÉATION DU RAPPORT ===
        report = Report.objects.create(
            attendance_check=check_obj,
            unidentified_faces=unidentified_urls,
        )
        report.present_students.set(present_students)
        report.absent_students.set(absent_students)

        # === NETTOYAGE ===
        shutil.rmtree(temp_dir, ignore_errors=True)

        return JsonResponse({
            'success': True,
            'check_id': check_obj.id,
            'report_id': report.id,
            'message': f'{present_students.count()} présent(s), {absent_students.count()} absent(s), {len(unidentified_urls)} non identifié(s)',
        })

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JsonResponse({'success': False, 'error': f'Erreur lors de la sauvegarde : {str(e)}'})
    
@login_required
def reports_list(request):
    if request.user.is_super_manager:
        reports = Report.objects.select_related(
            'attendance_check__performed_by'
        ).prefetch_related(
            'present_students', 'absent_students'
        ).all().order_by('-created_at')
    else:
        reports = Report.objects.filter(
            attendance_check__performed_by=request.user
        ).select_related(
            'attendance_check__performed_by'
        ).prefetch_related(
            'present_students', 'absent_students'
        ).all().order_by('-created_at')

    # Statistiques totales pour l'en-tête
    total_present = sum(r.present_students.count() for r in reports)
    total_absent = sum(r.absent_students.count() for r in reports)
    total_unidentified = sum(len(r.unidentified_faces or []) for r in reports)

    return render(request, 'detectorApp/reports/list.html', {
        'reports': reports,
        'total_present': total_present,
        'total_absent': total_absent,
        'total_unidentified': total_unidentified,
    })


@login_required
def report_detail(request, pk):
    report = get_object_or_404(
        Report.objects.select_related(
            'attendance_check__performed_by'
        ).prefetch_related(
            'present_students', 'absent_students'
        ),
        pk=pk
    )
    check = report.attendance_check
    classrooms = check.classrooms.all()

    # Préparer les données pour le template
    present_data = []
    for student in report.present_students.all():
        present_data.append({
            'name': student.name,
            'face_image': student.face_image.url if student.face_image else None,
            'classroom': student.classroom.name,
            'status': 'present',
        })

    absent_data = []
    for student in report.absent_students.all():
        absent_data.append({
            'name': student.name,
            'face_image': student.face_image.url if student.face_image else None,
            'classroom': student.classroom.name,
            'status': 'absent',
        })

    # Visages non identifiés depuis le JSON
    unidentified_data = report.unidentified_faces if report.unidentified_faces else []

    return render(request, 'detectorApp/reports/detail.html', {
        'report': report,
        'check': check,
        'classrooms': classrooms,
        'present_data': present_data,
        'absent_data': absent_data,
        'unidentified_data': unidentified_data,
        'present_count': len(present_data),
        'absent_count': len(absent_data),
        'unidentified_count': len(unidentified_data),
    })

@login_required
def report_delete(request, pk):
    report = get_object_or_404(Report, pk=pk)
    report.delete()
    messages.success(request, "Raport supprimée.")
    return redirect('reports_list')

@login_required
def report_pdf(request, pk):
    from django.http import HttpResponse
    from .reports.pdf_export import generate_pdf
    from io import BytesIO

    report = get_object_or_404(
        Report.objects.select_related(
            'attendance_check__performed_by'
        ).prefetch_related(
            'present_students', 'absent_students'
        ),
        pk=pk
    )

    buffer = BytesIO()
    generate_pdf(report, buffer)
    buffer.seek(0)

    filename = f"rapport_presence_{report.created_at.strftime('%Y%m%d_%H%M')}.pdf"

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
def report_excel(request, pk):
    from django.http import HttpResponse
    return HttpResponse("Excel export à venir", content_type='text/plain')



@login_required
def report_excel(request, pk):
    from django.http import HttpResponse
    from .reports.excel_export import generate_excel
    from io import BytesIO

    report = get_object_or_404(
        Report.objects.select_related(
            'attendance_check__performed_by'
        ).prefetch_related(
            'present_students', 'absent_students'
        ),
        pk=pk
    )

    buffer = BytesIO()
    generate_excel(report, buffer)
    buffer.seek(0)

    filename = f"rapport_presence_{report.created_at.strftime('%Y%m%d_%H%M')}.xlsx"

    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response