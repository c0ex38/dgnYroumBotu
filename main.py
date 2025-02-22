import time
from trendyol_reviews import trendyol_yorumlari_cek
from trendyol_all_products import trendyol_products
from product_ids import products_ids
from post_reviews import post_all_reviews

urun_url = "https://www.trendyol.com/magaza/profil/dgn-m-107703"

def main_loop():
    while True:
        print("\n🚀 Yeni veri çekme işlemi başlatılıyor...")

        try:
            trendyol_yorumlari_cek(urun_url)
            trendyol_products()
            products_ids()
            post_all_reviews()
            print("✅ Tüm işlemler başarıyla tamamlandı.")
        except Exception as e:
            print(f"❌ Hata oluştu: {e}")

        print("⏳ 10 dakika bekleniyor...")
        time.sleep(600)  # 10 dakika bekler

if __name__ == "__main__":
    main_loop()