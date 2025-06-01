from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import random

# Kullanıcıdan giriş al
tarih = input("Tarih (YYYY-MM-DD): ").strip()
hipodrom = input("Hipodrom (Örn: BURSA): ").strip().upper()
start_kosu = int(input("Başlangıç Koşu No: "))
end_kosu = int(input("Bitiş Koşu No: "))

# Veri tipleri
veri_tipleri = {
    "": "Program",
    "performans": "Performans",
    "galop": "Galop",
    "sprintler": "Sprint",
    "orijin": "Orijin",
    "kim-kimi-gecti": "Kim Kimi Geçti",
    "galop-bulten": "Galop Bülteni",
    "jokey": "Jokey",
    "birincilikler": "Birincilikler"
}

# Sabit istatistik sayfaları
sabit_sayfalar = {
    "Jokey İstatistikleri": "https://liderform.com.tr/istatistik/jokey",
    "At İstatistikleri": "https://liderform.com.tr/istatistik/at"
}

# Selenium ayarları
options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument("--window-size=1920,1080")
options.add_argument('--no-sandbox')
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.execute_cdp_cmd("Network.setUserAgentOverride", {
    "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36"
})

html_icerik = f"Yarış Verileri – {tarih} / {hipodrom}\n"
veri_raporu = []

def veri_sayfa_getir(url, beklenen_adet=None, sinif_adi=None, retry=3):
    for attempt in range(retry):
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            if beklenen_adet and sinif_adi:
                WebDriverWait(driver, 15).until(
                    lambda d: len(d.find_elements(By.CLASS_NAME, sinif_adi)) >= beklenen_adet or attempt == retry - 1
                )
            time.sleep(random.uniform(1.5, 3.5))
            return driver.page_source
        except Exception as e:
            if attempt == retry - 1:
                return f"Sayfa alınamadı ({url}): {e}"
            time.sleep(2)
    return "Sayfa alınamadı (retry başarısız)"

def at_sayisi_bul(starter_html):
    soup = BeautifulSoup(starter_html, "html.parser")
    return len(soup.find_all("div", class_="at-kosu-blok"))

def kontrol_et(veri_tipi, html_soup, beklenen_adet):
    if veri_tipi not in ["Performans", "Galop"]:
        return ""
    sinif_adi = "performans-blok" if veri_tipi == "Performans" else "galop-blok"
    at_bloklari = html_soup.find_all("div", class_=sinif_adi)
    uyarilar = []
    if len(at_bloklari) < beklenen_adet:
        uyarilar.append(f"UYARI: {veri_tipi} sayfasında beklenen {beklenen_adet} atın verisi, yalnızca {len(at_bloklari)} blokta bulundu.")
    for blok in at_bloklari:
        satirlar = blok.find_all("tr")
        if len(satirlar) == 0:
            at_ismi = blok.find("span", class_="at-adi")
            at_adi = at_ismi.text.strip() if at_ismi else "(At ismi alınamadı)"
            uyarilar.append(f"UYARI: {at_adi} için hiç koşu verisi yok.")
    return "\n".join(uyarilar)

kosu_at_sayilari = {}
for kosu_no in range(start_kosu, end_kosu + 1):
    starter_url = f"https://liderform.com.tr/program/{tarih}/{hipodrom}/{kosu_no}"
    starter_html = veri_sayfa_getir(starter_url)
    at_sayisi = at_sayisi_bul(starter_html)
    kosu_at_sayilari[kosu_no] = at_sayisi

for kosu_no in range(start_kosu, end_kosu + 1):
    for veri_link, veri_baslik in veri_tipleri.items():
        if veri_link == "":
            url = f"https://liderform.com.tr/program/{tarih}/{hipodrom}/{kosu_no}"
        else:
            url = f"https://liderform.com.tr/program/{veri_link}/{tarih}/{hipodrom}/{kosu_no}"

        print(f"{kosu_no}. Koşu – {veri_baslik} çekiliyor...")

        beklenen = kosu_at_sayilari.get(kosu_no, 0)
        sinif = "performans-blok" if veri_baslik == "Performans" else "galop-blok" if veri_baslik == "Galop" else None
        kaynak = veri_sayfa_getir(url, beklenen_adet=beklenen if sinif else None, sinif_adi=sinif)

        soup = BeautifulSoup(kaynak, "html.parser")
        metin = soup.get_text(separator="\n").strip()

        uyarilar = ""
        if veri_baslik in ["Performans", "Galop"]:
            kontrol = kontrol_et(veri_baslik, soup, beklenen)
            if kontrol:
                uyarilar = kontrol + "\n"
                veri_raporu.append((kosu_no, veri_baslik, "Eksik Veri"))
            else:
                veri_raporu.append((kosu_no, veri_baslik, "OK"))
        else:
            veri_raporu.append((kosu_no, veri_baslik, "OK"))

        html_icerik += f"\n### KOŞU: {kosu_no}, VERİ: {veri_baslik}\n"
        html_icerik += f"--- {veri_baslik.upper()} BAŞLANGIÇ ---\n"
        html_icerik += uyarilar + metin + "\n"
        html_icerik += f"--- {veri_baslik.upper()} BİTİŞ ---\n"
        html_icerik += f"### KOŞU: {kosu_no}, VERİ: {veri_baslik}"

for baslik, url in sabit_sayfalar.items():
    print(f"{baslik} çekiliyor...")
    kaynak = veri_sayfa_getir(url)
    soup = BeautifulSoup(kaynak, "html.parser")
    metin = soup.get_text(separator="\n").strip()
    metin += "\nNot: Sayfa çok sayfalıdır. Yalnızca ilk sayfa alınmıştır."
    html_icerik += f"\n--- {baslik.upper()} BAŞLANGIÇ ---\n{metin}\n--- {baslik.upper()} BİTİŞ ---"

try:
    with open("yaris_raporu.txt", "w", encoding="utf-8") as f:
        f.write(html_icerik)
    print("✅ TXT çıktısı başarıyla oluşturuldu: yaris_raporu.txt")
except Exception as e:
    print(f"❌ TXT dosyası yazılırken hata oluştu: {e}")

driver.quit()
