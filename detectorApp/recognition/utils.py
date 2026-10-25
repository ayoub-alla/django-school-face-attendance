from PIL import Image
import io


def resize_image(image_file, max_size=1024):
    """Redimensionne une image si elle dépasse max_size (côté le plus long)."""
    img = Image.open(image_file)
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)
    return buffer