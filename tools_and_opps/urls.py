from django.urls import path
from .views import tools_dashboard, download_document

app_name = 'tools_and_opps'  # Set an app namespace

urlpatterns = [
    path('', tools_dashboard, name='tools_dashboard'),
    path('download/<int:document_id>/', download_document, name='download_document'),
]
