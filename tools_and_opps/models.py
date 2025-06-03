from django.db import models

class SocialPlatform(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField()
    icon = models.ImageField(upload_to='social_icons/', blank=True, null=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class TrainingDocument(models.Model):
    title = models.CharField(max_length=200)
    document = models.FileField(upload_to='training_documents/')
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class VideoMaterial(models.Model):
    title = models.CharField(max_length=200)
    video_url = models.URLField()  # e.g., a YouTube link or hosted video URL
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class AdvertisementMaterial(models.Model):
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='advertisement_materials/')
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class YouTubeLink(models.Model):
    title = models.CharField(max_length=200)
    url = models.URLField()
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title
