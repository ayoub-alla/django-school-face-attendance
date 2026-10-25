import face_recognition
import numpy as np
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile


def detect_faces(image_file):
    """
    Détecte les visages dans une image et retourne une liste de dicts :
    [{ 'face_image': InMemoryUploadedFile (crop), 'encoding': list[float], 'location': (top, right, bottom, left) }, ...]
    """
    if isinstance(image_file, InMemoryUploadedFile):
        img = face_recognition.load_image_file(image_file)
    else:
        img = face_recognition.load_image_file(image_file.path)

    face_locations = face_recognition.face_locations(img, model='hog')

    if not face_locations:
        return []

    face_encodings = face_recognition.face_encodings(img, face_locations)

    results = []
    for (top, right, bottom, left), encoding in zip(face_locations, face_encodings):
        face_img = img[top:bottom, left:right]
        face_pil = Image.fromarray(face_img)

        buffer = BytesIO()
        face_pil.save(buffer, format='JPEG')
        buffer.seek(0)

        face_file = InMemoryUploadedFile(
            buffer, None, 'face.jpg', 'image/jpeg', buffer.tell(), None
        )

        results.append({
            'face_image': face_file,
            'encoding': encoding.tolist(),
            'location': (top, right, bottom, left),
        })

    return results


def compare_encoding(unknown_encoding, known_encodings, threshold=0.6):
    """
    Compare un encodage inconnu à une liste d'encodages connus.
    Retourne (index, distance) ou (None, None) si aucun match.
    """
    if not known_encodings:
        return None, None

    known_array = np.array(known_encodings)
    unknown_array = np.array(unknown_encoding)

    distances = face_recognition.face_distance(known_array, unknown_array)

    if len(distances) == 0:
        return None, None

    best_match_index = np.argmin(distances)
    best_distance = distances[best_match_index]

    if best_distance <= threshold:
        return int(best_match_index), float(best_distance)
    return None, None