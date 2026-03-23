from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class TypingResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    wpm = models.IntegerField()
    accuracy = models.FloatField()
    grammar_score = models.FloatField()

    test_time = models.IntegerField(default=60)  
    time_limit = models.IntegerField(default=60) 

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.wpm} WPM"



class ImageInfo(models.Model):
    image = models.ImageField(upload_to="typing/")
    time_limit = models.IntegerField(default=60)
    extracted_text = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
    # Check if this is a new record
     is_new = self.pk is None

    # Save the object first (so image file exists)
     super().save(*args, **kwargs)

    # Run OCR ONLY when a new image is uploaded
     if is_new and self.image:
        from PIL import Image
        import pytesseract

        img = Image.open(self.image.path)
        text = pytesseract.image_to_string(img)

        # Update extracted_text only once
        ImageInfo.objects.filter(pk=self.pk).update(extracted_text=text)

    # def __str__(self):
    #     return f"{self.image.name} - {self.time_limit}s"

    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)

    #     # path of uploaded image
    #     image_path = os.path.join(settings.MEDIA_ROOT, self.image.name)

    #     # Tesseract path (Windows)
    #     pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    #     # OCR extraction
    #     img = Image.open(image_path)
    #     text = pytesseract.image_to_string(img)

    #     self.extracted_text = text
    #     super().save(update_fields=["extracted_text"])
