import sqlite3
import hashlib
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from datetime import datetime, timedelta
import locale

locale.setlocale(locale.LC_TIME, "tr_TR.UTF-8")

def init_db():
    conn = sqlite3.connect("yorumlar.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS yorumlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        yorum TEXT,
        tarih INTEGER,
        product_url TEXT,
        yildiz INTEGER,
        hash TEXT UNIQUE,
        is_sent INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    conn.close()

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")

    # Tarayıcı servis ayarlarını belirle
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver

def clean_url(url):
    return re.sub(r"\?.*$", "", url)  # '?' işaretinden sonrasını kaldır

def parse_star_rating(text):
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else None  # Sayıyı al, yoksa None dön

def convert_to_timestamp(tarih_str):
    try:
        # Yorum tarihini datetime formatına çevir
        tarih_obj = datetime.strptime(tarih_str, "%d %B %Y")

        # Şu anki tarih ve 1 gün öncesini hesapla
        bugun = datetime.now()
        yedi_gun_once = bugun - timedelta(days=1)

        # Eğer yorum tarihi son 1 gün içinde değilse, None dön (kaydedilmesin)
        if tarih_obj < yedi_gun_once:
            print(f"⚠️ {tarih_str} - Bu yorum 1 günden eski, kaydedilmeyecek.")
            return None

        # Yorum tarihini timestamp'e çevir ve döndür
        return int(tarih_obj.timestamp())

    except Exception as e:
        print(f"⚠️ Tarih hatası: {e}")
        return None

def get_yorumlar(driver, url):
    driver.get(url)
    time.sleep(5)
    try:
        yorum_kutusu = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "product-review-section-wrapper__wrapper__comment"))
        )

        for _ in range(5):
            prev_height = driver.execute_script("return arguments[0].scrollHeight", yorum_kutusu)
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", yorum_kutusu)
            time.sleep(3)
            new_height = driver.execute_script("return arguments[0].scrollHeight", yorum_kutusu)
            if prev_height == new_height:
                break
    except:
        print("⚠️ Yorum bölümü yüklenemedi!")
        return []

    return driver.find_elements(By.CLASS_NAME, "product-review-container")

def save_yorumlar(yorum_kutulari):
    conn = sqlite3.connect("yorumlar.db")
    cursor = conn.cursor()

    for index, yorum_kutusu in enumerate(yorum_kutulari, start=1):
        try:
            yorum = yorum_kutusu.find_element(By.CLASS_NAME,
                                              "product-review-container__comment-container__rating-review__comment").text.strip()

            tarih_elementleri = yorum_kutusu.find_elements(By.CLASS_NAME,
                                                           "product-review-container__comment-container__comment-info__user-fullname")
            tarih_timestamp = None
            if len(tarih_elementleri) > 1:
                tarih_str = tarih_elementleri[-1].text.strip()
                tarih_timestamp = convert_to_timestamp(tarih_str)

            # Eğer tarih None ise (1 günden eskiyse), bu yorumu kaydetme
            if tarih_timestamp is None:
                print(f"{index}. ⚠️ Yorum tarihi uygun değil, kaydedilmeyecek: {yorum}")
                continue

            urun_link = yorum_kutusu.find_element(By.CLASS_NAME, "product-review-container__redirect").get_attribute("href")
            urun_link = clean_url(urun_link)  # URL'yi temizle

            yildiz_puani = None
            try:
                yildiz_text = yorum_kutusu.find_element(By.CLASS_NAME, "star-ratings").get_attribute("title")
                yildiz_puani = parse_star_rating(yildiz_text)
            except:
                pass

            yorum_hash = hashlib.sha256(
                (yorum + str(tarih_timestamp) + urun_link + str(yildiz_puani)).encode()).hexdigest()

            # 🚀 Daha hızlı kontrol için EXISTS kullan
            cursor.execute("SELECT EXISTS(SELECT 1 FROM yorumlar WHERE hash=?)", (yorum_hash,))
            exists = cursor.fetchone()[0]

            if exists:
                print(f"{index}. ⚠️ Yorum zaten veritabanında, eklenmedi: {yorum}")
            else:
                cursor.execute("""
                    INSERT INTO yorumlar (yorum, tarih, product_url, yildiz, hash, is_sent) 
                    VALUES (?, ?, ?, ?, ?, 0)""",
                               (yorum, tarih_timestamp, urun_link, yildiz_puani, yorum_hash))
                conn.commit()
                print(f"{index}. ✅ Yorum eklendi (is_sent=0): {yorum}")

        except Exception as e:
            print(f"{index}. ❌ Yorum çekilemedi. Hata: {e}")

    conn.close()

def trendyol_yorumlari_cek(url):
    init_db()
    driver = get_driver()

    print("📡 Yorumlar çekiliyor...")
    yorum_kutulari = get_yorumlar(driver, url)

    if yorum_kutulari:
        print(f"📌 {len(yorum_kutulari)} yorum bulundu, kaydediliyor...")
        save_yorumlar(yorum_kutulari)
    else:
        print("❌ Hiç yorum bulunamadı!")

    driver.quit()
    print("🚀 İşlem tamamlandı!")