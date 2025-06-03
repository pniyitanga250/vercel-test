from django.contrib import admin
from .models import SocialPlatform, TrainingDocument, VideoMaterial, AdvertisementMaterial, YouTubeLink

@admin.register(SocialPlatform)
class SocialPlatformAdmin(admin.ModelAdmin):
    list_display = ('name', 'url')

@admin.register(TrainingDocument)
class TrainingDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'uploaded_at')

@admin.register(VideoMaterial)
class VideoMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'video_url', 'uploaded_at')

@admin.register(AdvertisementMaterial)
class AdvertisementMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'uploaded_at')

@admin.register(YouTubeLink)
class YouTubeLinkAdmin(admin.ModelAdmin):
    list_display = ('title', 'url')
