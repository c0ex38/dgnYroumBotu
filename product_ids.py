import sqlite3
import requests
import json
from login import login


def process_product_barcode(cursor, barcode, token):
    """Barkod bilgisini API'ye gönder, MainProductCode al ve kaydet."""
    try:
        print(f"🔄 İşleniyor: {barcode}")

        url = f"https://dgnonline.com/rest1/subProduct/getSubProductByCode/{barcode}"
        payload = {"token": token}

        response = requests.post(url, data=payload, timeout=10)

        if response.status_code == 200:
            response_data = json.loads(response.text)

            if response_data.get("success") and response_data.get("data"):
                product_data = response_data["data"][0]
                product_code = product_data.get("MainProductCode", "MainProductCode bulunamadı")

                base_product_code = product_code.rsplit("-", 1)[0] if "-" in product_code else product_code

                print(f"✅ {barcode} için MainProductCode bulundu: {product_code}")
                print(f"➡ BaseProductCode: {base_product_code}")

                cursor.execute(
                    "INSERT INTO processed_barcodes (barcode, product_code, base_product_code) VALUES (?, ?, ?)",
                    (barcode, product_code, base_product_code)
                )

            else:
                print(f"⚠ API yanıtında MainProductCode bulunamadı: {response_data}")

        else:
            print(f"❌ API hatası: {response.status_code} - {response.text}")

    except requests.RequestException as e:
        print(f"❌ API isteğinde hata oluştu ({barcode}): {e}")


def get_product_ids(cursor, token):
    """Base Product Code'ları kullanarak API'den ProductId'leri alır ve kaydeder."""
    try:
        print("📌 Base Product Code'lara API isteği gönderiliyor...")

        cursor.execute(
            "SELECT DISTINCT base_product_code FROM processed_barcodes WHERE base_product_code NOT IN (SELECT base_product_code FROM processed_product_ids)"
        )
        rows = cursor.fetchall()

        if not rows:
            print("⚠ İşlenmemiş Base Product Code bulunamadı.")
            return

        for row in rows:
            base_product_code = row[0]
            print(f"🔍 Base Product Code işleniyor: {base_product_code}")

            productcode_url = "https://dgnonline.com/rest1/product/get"
            productcode_params = {'token': token, 'f': f'ProductCode|{base_product_code}|contain'}

            response = requests.post(productcode_url, data=productcode_params, timeout=10)

            if response.status_code == 200:
                productcode_response_json = json.loads(response.text)

                if productcode_response_json.get("success") and productcode_response_json.get("data"):
                    for prod in productcode_response_json["data"]:
                        product_id = prod.get("ProductId")
                        if product_id:
                            cursor.execute(
                                "INSERT INTO processed_product_ids (base_product_code, product_id) VALUES (?, ?)",
                                (base_product_code, product_id)
                            )

                    print(f"✅ {base_product_code} için ProductId'ler kaydedildi.")

    except requests.RequestException as e:
        print(f"❌ API isteğinde hata oluştu: {e}")


def products_ids():
    """Products tablosundaki barcode'leri işler, API'den MainProductCode alır ve ardından ProductId'leri alır."""
    try:
        token = login()
        print(f"✅ Alınan Token: {token}")

        # Veritabanına bağlan
        conn = sqlite3.connect("yorumlar.db", timeout=10)
        cursor = conn.cursor()

        # processed_barcodes tablosunu güncelle (yeni kolonları ekleyelim)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_barcodes (
                barcode TEXT PRIMARY KEY,
                product_code TEXT,
                base_product_code TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_product_ids (
                base_product_code TEXT,
                product_id TEXT
            )
        """)
        conn.commit()

        # İşlenmemiş barcode'leri al
        cursor.execute(
            "SELECT DISTINCT barcode FROM products WHERE barcode NOT IN (SELECT barcode FROM processed_barcodes)"
        )
        rows = cursor.fetchall()  # Tüm sonuçları al

        for row in rows:
            process_product_barcode(cursor, row[0], token)  # Aynı cursor'ü kullanarak işleyelim

        conn.commit()  # 🔹 Tek seferde commit yapılıyor (daha hızlı)

        # Base Product Code'lardan ProductId'leri al
        get_product_ids(cursor, token)

        conn.commit()  # 🔹 Tek seferde commit yapılıyor (daha hızlı)
        conn.close()  # 🔹 Bağlantıyı en son kapatıyoruz.

        print("🚀 Tüm yeni barcode'ler işlendi, MainProductCode ve ProductId'ler alındı.")

    except sqlite3.Error as e:
        print(f"❌ Hata oluştu: {e}")


