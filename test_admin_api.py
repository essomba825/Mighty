import urllib.request
import json

def test_admin_api():
    login_url = "http://127.0.0.1:8000/api/auth/login/"
    login_data = json.dumps({"identifier": "admin@mightysixers.org", "password": "Admin123!"}).encode("utf-8")
    req = urllib.request.Request(login_url, data=login_data, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req) as res:
            auth_res = json.loads(res.read().decode("utf-8"))
            access_token = auth_res.get("access")
            user_data = auth_res.get("user", {})
            print(f"[AUTH] Login SUCCESS as {user_data.get('email')} (role: {user_data.get('role')}, is_staff: {user_data.get('is_staff')})")
            
            headers = {"Authorization": f"Bearer {access_token}"}
            
            endpoints = [
                ("/api/stats/", "Tableau de bord / KPIs"),
                ("/api/auth/admin/users/", "Membres & Rôles"),
                ("/api/news/", "Actualités & Publications"),
                ("/api/events/", "Événements & Rencontres"),
                ("/api/projects/", "Projets Communautaires"),
                ("/api/donations/contributions/", "Finances & Dons"),
                ("/api/donations/partnerships/", "Partenariats & Mécénat"),
                ("/api/education/lessons/pending/", "Validation Pédagogique"),
            ]
            
            for ep, label in endpoints:
                ep_req = urllib.request.Request(f"http://127.0.0.1:8000{ep}", headers=headers)
                with urllib.request.urlopen(ep_req) as ep_res:
                    data = json.loads(ep_res.read().decode("utf-8"))
                    if isinstance(data, dict):
                        if "results" in data:
                            total = data.get("count", len(data["results"]))
                            print(f"[OK] {label:28} | {ep:32} | Status: {ep_res.status} | {total} items")
                        else:
                            print(f"[OK] {label:28} | {ep:32} | Status: {ep_res.status} | Keys: {list(data.keys())}")
                    elif isinstance(data, list):
                        print(f"[OK] {label:28} | {ep:32} | Status: {ep_res.status} | {len(data)} items")
                        
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    test_admin_api()
