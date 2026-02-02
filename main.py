import requests
import json
import os

# --- KULLANICI BİLGİLERİ ---
# Not: E-postanı ekledim, şifreni güvenlik nedeniyle "..." olarak bıraktım.
# Aşağıdaki tırnak içine kendi şifreni yazmalısın.
EMAIL = "Mr.aykutsen@gmail.com"
PASSWORD = "Aykut01081993.."  # <-- Şifreni buraya yapıştır

# --- AYARLAR ---
BASE_URL = "https://eu1.tabii.com/apigateway"
# Tabii Login Endpoint (Genellikle bu yapıdadır, çalışmazsa network izlenip güncellenmeli)
LOGIN_URL = "https://eu1.tabii.com/auth/v1/login" 
# Alternatif login endpoint'leri: /auth/login, /pbr/v1/auth/login olabilir. 
# Tabii'nin tam API dokümanı olmadığı için standart auth yapısını kullanıyoruz.

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json"
}

def login_and_get_token():
    """Kullanıcı adı ve şifre ile giriş yapıp Bearer Token alır."""
    print("Giriş yapılıyor...")
    
    payload = {
        "email": EMAIL,
        "password": PASSWORD
    }
    
    try:
        # Login isteği atıyoruz
        # Not: Tabii API yapısına göre payload 'username' yerine 'email' istiyor olabilir.
        response = requests.post(LOGIN_URL, json=payload, headers=HEADERS)
        
        if response.status_code == 200:
            data = response.json()
            # Token genellikle 'token', 'access_token' veya 'auth' altında döner.
            # Gelen yanıta göre burayı düzenlemek gerekebilir.
            token = data.get("token") or data.get("access_token") or data.get("session", {}).get("token")
            
            if token:
                print("Giriş başarılı! Yeni Token alındı.")
                return token
            else:
                print("Giriş başarılı ama Token bulunamadı. Yanıt:", data)
                return None
        else:
            print(f"Giriş başarısız! Hata Kodu: {response.status_code}")
            print("Cevap:", response.text)
            return None
            
    except Exception as e:
        print(f"Login sırasında hata: {e}")
        return None

def get_contents(auth_token):
    """Alınan token ile içerik listesini çeker."""
    print("İçerikler çekiliyor...")
    
    # Header'a token ekle
    auth_headers = HEADERS.copy()
    auth_headers["Authorization"] = f"Bearer {auth_token}"
    
    # HTML'den aldığımız ID'ye göre içerik listesi (Örnek ID)
    target_id = "149106_149112" 
    api_endpoint = f"{BASE_URL}/pbr/v1/pages/browse/{target_id}"
    
    try:
        response = requests.get(api_endpoint, headers=auth_headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Veri çekilemedi. Kod: {response.status_code}")
            return None
    except Exception as e:
        print(f"Veri çekme hatası: {e}")
        return None

def generate_files(data, auth_token):
    """M3U ve JSON dosyalarını oluşturur."""
    if not data:
        return

    m3u_content = "#EXTM3U\n"
    json_list = []
    
    # API yapısını düzleştirme (Component -> Element -> Media)
    items = []
    if "components" in data:
        for comp in data["components"]:
             if "elements" in comp:
                 items.extend(comp["elements"])

    print(f"Toplam {len(items)} içerik bulundu. Dosyalar hazırlanıyor...")

    for item in items:
        try:
            media_id = item.get("id")
            title = item.get("title", "Bilinmeyen Başlık")
            
            # Görseli bul
            image_url = ""
            if "images" in item and item["images"]:
                image_url = item["images"][0].get("url", "")
                if image_url and not image_url.startswith("http"):
                    image_url = f"https://cms-tabii-assets.tabii.com{image_url}"

            # Stream Linki Oluşturma (Tabii Standart Yapısı)
            # Bu link Token olmadan 403 hatası verir.
            stream_url = f"{BASE_URL}/pbr/v1/media/{media_id}/master.mpd"

            # 1. M3U Formatı
            # Player'ın Header desteği varsa çalışması için token bilgisini yoruma ekliyoruz.
            m3u_content += f'#EXTINF:-1 tvg-id="{media_id}" tvg-logo="{image_url}", {title}\n'
            m3u_content += f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}\n'
            m3u_content += f'#EXTVLCOPT:http-header-authorization=Bearer {auth_token}\n'
            m3u_content += f'{stream_url}\n'

            # 2. JSON Formatı
            json_list.append({
                "id": media_id,
                "title": title,
                "thumbnail": image_url,
                "stream_url": stream_url,
                "drm": "widevine",
                "headers": {
                    "Authorization": f"Bearer {auth_token}",
                    "User-Agent": HEADERS["User-Agent"]
                }
            })

        except Exception as e:
            continue

    # Dosyaları Kaydet
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    
    with open("tabii_data.json", "w", encoding="utf-8") as f:
        json.dump(json_list, f, ensure_ascii=False, indent=4)

    print("✅ İşlem tamamlandı! 'playlist.m3u' ve 'tabii_data.json' oluşturuldu.")

if __name__ == "__main__":
    # 1. Adım: Giriş Yap
    token = login_and_get_token()
    
    # Eğer giriş başarısız olursa manuel token (yedek) kullanabiliriz ama
    # amacımız otomasyon olduğu için burada duruyoruz.
    if token:
        # 2. Adım: Veriyi Çek
        content_data = get_contents(token)
        
        # 3. Adım: Dosyaları Yaz
        generate_files(content_data, token)
    else:
        print("❌ Token alınamadığı için işlem durduruldu.")
