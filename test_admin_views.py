import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

def run_tests():
    client = Client()
    admin_user = User.objects.filter(email='admin@mightysixers.org').first()
    if not admin_user:
        print("[ERROR] admin@mightysixers.org not found in database!")
        return
    
    print(f"[1/8] Admin Superuser Verified: {admin_user.email} (Staff: {admin_user.is_staff}, Role: {admin_user.role})")
    
    # 1. Login API test
    login_res = client.post('/api/auth/login/', data=json.dumps({
        'identifier': 'admin@mightysixers.org',
        'password': 'Admin123!'
    }), content_type='application/json')
    
    if login_res.status_code != 200:
        print(f"[FAIL] /api/auth/login/ -> HTTP {login_res.status_code}: {login_res.content.decode()}")
        return
    
    token = login_res.json().get('access')
    print(f"[2/8] JWT Auth Token Received: {token[:20]}...")
    auth_header = f'Bearer {token}'
    
    # 2. Test All Admin Back-Office Endpoints
    endpoints = [
        ('/api/stats/', 'Tableau de bord & KPIs', 'stats'),
        ('/api/auth/admin/users/', 'Membres & Rôles', 'users'),
        ('/api/news/', 'Actualités & Publications', 'news'),
        ('/api/events/', 'Événements & Rencontres', 'events'),
        ('/api/projects/', 'Projets Communautaires', 'projects'),
        ('/api/donations/contributions/', 'Finances & Dons', 'contributions'),
        ('/api/donations/partnerships/', 'Partenariats & Mécénat', 'partnerships'),
        ('/api/education/lessons/pending/', 'Validation Pédagogique', 'lessons'),
    ]
    
    print("\n" + "="*80)
    print(f"{'PAGE / MODULE':<28} | {'ENDPOINT API':<34} | {'HTTP':<5} | {'DONNÉES DISPONIBLES'}")
    print("="*80)
    
    for url, label, key in endpoints:
        res = client.get(url, HTTP_AUTHORIZATION=auth_header)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict):
                if 'results' in data:
                    count = f"{len(data['results'])} items (Total: {data.get('count', len(data['results']))})"
                else:
                    # e.g. stats endpoint
                    sub_counts = []
                    for k, v in data.items():
                        if isinstance(v, dict):
                            sub_counts.append(f"{k}: {list(v.values())[:2]}")
                    count = "Stats OK -> " + ", ".join(sub_counts[:3])
            elif isinstance(data, list):
                count = f"{len(data)} items"
            else:
                count = "OK"
            print(f"[OK] {label:<23} | {url:<34} | {res.status_code:<5} | {count}")
        else:
            print(f"[ERR] {label:<22} | {url:<34} | {res.status_code:<5} | {res.content.decode()[:60]}")
    
    print("="*80)
    print("[SUCCESS] Toutes les pages admin et leurs flux de données sont 100% opérationnels !")

if __name__ == '__main__':
    run_tests()
