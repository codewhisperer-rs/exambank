"""
URL configuration for exambank project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static
from courses.views import register_view, about_me_view
from django.contrib.auth import views as auth_views # Import auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', about_me_view, name='home'), # 'about_me_view' is the homepage

    # Override the default login view to redirect authenticated users
    path(
        'accounts/login/',
        auth_views.LoginView.as_view(
            template_name='registration/login.html', # Explicitly point to your custom template
            redirect_authenticated_user=True
        ),
        name='login'
    ),
    # Include other default auth URLs (logout, password change, password reset, etc.)
    path('accounts/', include('django.contrib.auth.urls')),

    path('register/', register_view, name='register'),
    path('courses/', include('courses.urls')), # Main application content
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
