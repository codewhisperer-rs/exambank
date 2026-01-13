from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from courses.views import register_view, about_me_view
from django.contrib.auth import views as auth_views 
from django.shortcuts import redirect
def ai_exercises_redirect(request):
    return redirect('courses:my_ai_exercises')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', about_me_view, name='home'), 
    path(
        'accounts/login/',
        auth_views.LoginView.as_view(
            template_name='registration/login.html', 
            redirect_authenticated_user=True
        ),
        name='login'
    ),
    path('accounts/', include('django.contrib.auth.urls')),

    path('register/', register_view, name='register'),
    path('courses/', include('courses.urls')), 
    path('ai-exercises/', ai_exercises_redirect, name='ai_exercises_redirect'), 
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
