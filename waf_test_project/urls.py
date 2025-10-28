"""
URL configuration for waf_test_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def root_view(request):
    """Root endpoint with API information"""
    return JsonResponse({
        'service': 'WAF Test Backend',
        'version': '1.0.0',
        'endpoints': {
            'api': '/api/',
            'test_suite': '/api/test-suite/',
            'health': '/api/health/',
            'admin': '/admin/'
        },
        'note': 'Visit /api/test-suite/ for all available test endpoints'
    })

urlpatterns = [
    path('', root_view, name='root'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]
