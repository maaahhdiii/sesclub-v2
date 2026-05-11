import os
from django.http import HttpResponse, Http404


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _serve_frontend_file(filename):
    path = os.path.join(BASE_DIR, 'frontend', filename)
    if not os.path.exists(path):
        raise Http404(f"{filename} not found")
    with open(path, 'rb') as f:
        content = f.read()
    return HttpResponse(content, content_type='text/html')


def student(request):
    return _serve_frontend_file('student.html')


def club(request):
    return _serve_frontend_file('club.html')


def admin_page(request):
    return _serve_frontend_file('admin.html')
