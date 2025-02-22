import sqlite3
import requests
import pandas as pd
import random  # Rastgele seçim için eklendi
from login import login

def post_all_reviews():
    try:
        print("📂 Excel'den CustomerId'ler alınıyor...")
        excel_path = "customer.xlsx"
        excel_data = pd.read_excel(excel_path)
        customer_ids = excel_data["Üye Id"].dropna().astype(int).tolist()
        print(f"✅ Alınan CustomerId'ler: {customer_ids}")

        if not customer_ids:
            print("⚠ Excel'den hiçbir CustomerId alınamadı.")
            return

        token = login()
        print(f"🔑 Alınan token: {token}")

        if not token:
            print("❌ Hata: Geçerli bir token alınamadı! API'ye istek gönderilemez.")
            return

        with sqlite3.connect("yorumlar.db") as conn:  # Veritabanı bağlantısını güvenli hale getir
            cursor = conn.cursor()

            print("🔍 Gönderilmemiş tüm yorumlar alınıyor...")
            cursor.execute("SELECT id, product_url, yorum, tarih, yildiz FROM yorumlar WHERE is_sent = 0")
            reviews = cursor.fetchall()

            if not reviews:
                print("⚠ Veritabanında gönderilmemiş yorum bulunamadı.")
                return

            print(f"📊 Toplam gönderilmemiş yorum: {len(reviews)}")

            api_url = "http://www.dgnonline.com/rest1/product/comment"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            success_count = 0

            for review in reviews:
                review_id, product_url, yorum, tarih, yildiz = review
                print(f"📝 İşleniyor: Yorum (ID: {review_id}, Yorum: {yorum}, Yıldız: {yildiz})")

                cursor.execute("""
                    SELECT DISTINCT processed_product_ids.product_id 
                    FROM yorumlar 
                    JOIN products ON yorumlar.product_url = products.product_url
                    JOIN processed_barcodes ON products.barcode = processed_barcodes.barcode
                    JOIN processed_product_ids ON processed_barcodes.base_product_code = processed_product_ids.base_product_code
                    WHERE yorumlar.id = ?
                """, (review_id,))

                product_ids = cursor.fetchall()

                if not product_ids:
                    print(f"⚠ Bu yorum için ProductID bulunamadı, devam ediliyor. (ID: {review_id})")
                    continue

                product_ids = [p[0] for p in product_ids]
                print(f"🔗 Yorum için bulunan ProductID'ler: {product_ids}")

                # 🚀 Bu yorum için rastgele bir müşteri seç
                random_customer_id = random.choice(customer_ids)
                print(f"👤 Seçilen rastgele müşteri: {random_customer_id}")

                # Yalnızca seçilen müşteri bu yorumu eşleşen ProductID'lere gönderecek
                for product_id in product_ids:
                    payload = {
                        "token": token,
                        "data": f'[{{ "CustomerId": "{random_customer_id}", "ProductId": "{product_id}", "Comment": "{yorum}", "Title": "", "Rate": "{yildiz}", "IsNameDisplayed": "true", "DateTimeStamp": "{tarih}" }}]'
                    }

                    print(f"📤 Yorum gönderiliyor: {payload}")
                    response = requests.post(api_url, data=payload, headers=headers, timeout=10)

                    if response.status_code == 200:
                        response_json = response.json()
                        print(f"📥 API Yanıtı: {response_json}")

                        if response_json.get("success"):
                            success_count += 1
                            print(f"✅ Yorum başarıyla gönderildi: {review_id}")

                # ✅ Yorum gönderildiği için işaretle
                cursor.execute("UPDATE yorumlar SET is_sent = 1 WHERE id = ?", (review_id,))
                conn.commit()
                print(f"🎯 Yorum başarıyla gönderildi ve işaretlendi. (ID: {review_id})")

        print(f"🚀 Tüm işlemler tamamlandı. Başarıyla gönderilen yorum sayısı: {success_count}")

    except Exception as e:
        print(f"❌ Hata oluştu: {str(e)}")