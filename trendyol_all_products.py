import sqlite3
import requests
import time
from urllib.parse import urlparse, urlunparse

# 🌟 Trendyol API Bilgileri
supplier_id = "107703"
username = "QlREbm5HcWtVdmVIOHRTbEdGQzQ6d3dEd2M0cFhmNEo1NjNOMXBKd3c="
base_url = f"https://api.trendyol.com/sapigw/suppliers/{supplier_id}/products"

# 🔹 Trendyol'un İstediği Cookie
cookies = {
    "FirstSession": "0",
    "VisitCount": "1",
    "platform": "web"
}

# 🔌 SQLite Veritabanına Bağlan
conn = sqlite3.connect("yorumlar.db")
cursor = conn.cursor()

# 🛍️ Ürünler Tablosunu Oluştur (Eğer Yoksa)
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    barcode TEXT PRIMARY KEY,
    product_url TEXT NOT NULL
)
""")
conn.commit()


def clean_product_url(product_url):
    """Ürünün URL'sinden tüm query parametrelerini temizler ve ana URL'yi döndürür."""
    parsed_url = urlparse(product_url)

    # Sadece ana domain + path kısmını alıyoruz (Query parametrelerini kaldırıyoruz)
    clean_url = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))

    print(f"🔍 Temizlenen URL: {clean_url}")  # Hata ayıklama için çıktıyı gör

    return clean_url


def get_yorumlar_urls():
    """Yorumlar tablosundaki eşleşecek product_url değerlerini alır."""
    cursor.execute("SELECT DISTINCT product_url FROM yorumlar")
    urls = cursor.fetchall()
    return {row[0] for row in urls}  # Set olarak döndür (hızlı arama için)


def get_existing_product_urls():
    """Products tablosunda kayıtlı olan tüm product_url değerlerini al."""
    cursor.execute("SELECT DISTINCT product_url FROM products")
    urls = cursor.fetchall()
    return {row[0] for row in urls}


def get_all_products():
    headers = {
        "Authorization": f"Basic {username}",
        "User-Agent": f"{supplier_id} - SelfIntegration"
    }

    print("📡 API'ye istek gönderiliyor...")

    response = requests.get(f"{base_url}?page=0&size=2500&approved=true", headers=headers, cookies=cookies)

    if response.status_code != 200:
        print(f"❌ API isteği başarısız! Status Code: {response.status_code}")
        print(f"Yanıt: {response.text}")  # Yanıt içeriğini yazdır
        return []

    data = response.json()

    if "totalPages" not in data:
        print("❌ HATA: 'totalPages' bulunamadı. API yanıtını kontrol et!")
        return []

    total_pages = data["totalPages"]
    all_products = []

    # 🔄 Tüm sayfalardaki ürünleri al
    for page in range(total_pages):
        print(f"📡 Sayfa {page + 1}/{total_pages} çekiliyor...")
        response = requests.get(f"{base_url}?page={page}&size=2500&approved=true", headers=headers, cookies=cookies)

        if response.status_code == 200:
            page_data = response.json()
            products = page_data.get("content", [])  # `content` varsa al, yoksa boş liste döndür
            all_products.extend(products)
            time.sleep(1)  # API rate limit için bekleme
        else:
            print(f"❌ Sayfa {page} yüklenirken hata oluştu: {response.status_code}")
            break

    return all_products


def save_products(products):
    yorumlar_urls = get_yorumlar_urls()  # Yorumlardaki ürün URL'lerini al
    existing_product_urls = get_existing_product_urls()  # Zaten kaydedilmiş ürün URL'lerini al

    for product in products:
        barcode = product["barcode"]
        raw_product_url = product["productUrl"]
        clean_url = clean_product_url(raw_product_url)

        # 🔥 SADECE `product_url` ÜZERİNDEN EŞLEŞME KONTROLÜ
        if clean_url in existing_product_urls:
            print(f"⚠️ Ürün zaten kayıtlı, atlanıyor: {clean_url}")
            continue

        # Eğer bu ürün yorumlar tablosundaki ürünlerle eşleşmiyorsa, ekleme
        if clean_url not in yorumlar_urls:
            print(f"⚠️ Yorumlar tablosunda bulunmayan ürün, eklenmedi: {barcode}")
            continue

        # 🔥 Veritabanına ekleme (barcode kontrolü olmadan)
        cursor.execute("INSERT INTO products (barcode, product_url) VALUES (?, ?)", (barcode, clean_url))
        conn.commit()
        print(f"✅ Ürün eklendi: {barcode} - {clean_url}")


def trendyol_products():
    print("📡 API'den Ürünler Alınıyor...")
    products = get_all_products()

    if not products:
        print("❌ Hiç ürün çekilemedi, işlem iptal edildi.")
        return

    print(f"🎉 Toplam {len(products)} ürün çekildi!")

    print("📂 Veritabanına Kaydediliyor...")
    save_products(products)

    # Veritabanı bağlantısını kapat
    conn.close()
    print("🚀 İşlem tamamlandı!")