import os
import mimetypes
from django.shortcuts import render, get_object_or_404
from django.http import FileResponse, Http404
from .models import SocialPlatform, TrainingDocument, VideoMaterial, AdvertisementMaterial, YouTubeLink

def tools_dashboard(request):
    context = {
         'social_platforms': SocialPlatform.objects.all(),
         'training_documents': TrainingDocument.objects.all(),
         'video_materials': VideoMaterial.objects.all(),
         'advertisement_materials': AdvertisementMaterial.objects.all(),
         'youtube_links': YouTubeLink.objects.all(),
    }
    return render(request, 'tools_and_opps/dashboard.html', context)

def download_document(request, document_id):
    # Fetch the document or return 404 if not found
    document = get_object_or_404(TrainingDocument, id=document_id)
    file_path = document.document.path
    if not os.path.exists(file_path):
        raise Http404("File not found")
    
    # Determine the MIME type of the file
    content_type, encoding = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = "application/octet-stream"
    
    # Open the file and serve it as an attachment for download
    response = FileResponse(open(file_path, 'rb'), content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
    return response
