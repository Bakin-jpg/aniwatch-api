import requests
from bs4 import BeautifulSoup
import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- KONFIGURASI DASAR ---
BASE_URL = "https://aniwatchtv.to"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://aniwatchtv.to/'
}

# --- FUNGSI SELENIUM ---
def setup_selenium_driver():
    """Menyiapkan driver Selenium Chrome untuk mode headless."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"user-agent={HEADERS['User-Agent']}")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- FUNGSI REQUESTS & SOUP ---
def get_soup(url):
    """Mengambil dan mem-parsing halaman web menggunakan Requests."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"Error (requests) saat mengambil URL {url}: {e}")
        return None

def get_stream_url(driver, watch_page_url):
    """Mengambil URL streaming dari halaman tontonan menggunakan Selenium."""
    if not watch_page_url: return None
    print(f"  -> Mengambil stream dari: {watch_page_url}")
    try:
        driver.get(watch_page_url)
        wait = WebDriverWait(driver, 25)
        iframe = wait.until(EC.presence_of_element_located((By.ID, "iframe-embed")))
        time.sleep(2)
        stream_src = iframe.get_attribute('src')
        if stream_src and 'megacloud' in stream_src:
            print(f"    -> Ditemukan: {stream_src[:50]}...")
            return stream_src
        return None
    except Exception:
        print(f"    -> Gagal mendapatkan iframe untuk {watch_page_url}")
        return None

# --- FUNGSI SCRAPING ---

def scrape_homepage_sections(soup):
    """Mengambil data dari Spotlight dan Latest Episodes di halaman utama."""
    data = {'spotlight': [], 'latest_episodes': []}

    # Spotlight
    slider = soup.find('div', id='slider')
    if slider:
        for item in slider.find_all('div', class_='deslide-item'):
            title_el = item.find('div', class_='desi-head-title')
            watch_now_el = item.find('a', class_='btn-primary')
            if not title_el or not watch_now_el: continue
            data['spotlight'].append({
                'title': title_el.text.strip(),
                'watch_url': f"{BASE_URL}{watch_now_el['href']}",
                'image_url': item.find('img', class_='film-poster-img').get('data-src'),
            })

    # Latest Episodes
    section = soup.find('section', class_='block_area_home')
    if section:
        for item in section.find_all('div', class_='flw-item'):
            title_el = item.find('h3', class_='film-name').find('a')
            if not title_el or not title_el.has_attr('href'): continue
            detail_slug = title_el['href']
            data['latest_episodes'].append({
                'title': title_el.get('title', '').strip(),
                'watch_url': f"{BASE_URL}/watch{detail_slug}",
                'image_url': item.find('img', class_='film-poster-img').get('data-src'),
            })
    return data

def scrape_full_catalog():
    """
    FUNGSI BARU: Mengambil seluruh katalog anime dari halaman A-Z.
    Ini akan memakan waktu paling lama.
    """
    print("\nMemulai scraping seluruh katalog anime (A-Z)...")
    catalog = []
    az_list_url = f"{BASE_URL}/az-list"
    
    soup = get_soup(az_list_url)
    if not soup:
        print("  -> Gagal membuka halaman A-Z list utama.")
        return []

    # Mengambil semua link huruf dari 'A' sampai 'Z'
    az_links = soup.select('.az-list a[href*="/az-list/"]')
    
    for link in az_links:
        char_page_url = f"{BASE_URL}{link['href']}"
        char = link.text.strip()
        if len(char) > 1: continue # Lewati link 'All', '#', '0-9'

        print(f"\nScraping untuk huruf: {char}")
        
        page_num = 1
        while True:
            paginated_url = f"{char_page_url}?page={page_num}"
            print(f"  -> Mengambil halaman: {paginated_url}")
            
            page_soup = get_soup(paginated_url)
            if not page_soup:
                print(f"    -> Gagal memuat halaman {page_num} untuk huruf {char}.")
                break
                
            anime_items = page_soup.select('.film_list-wrap .flw-item')
            if not anime_items:
                print(f"  -> Tidak ada lagi anime ditemukan untuk huruf {char}. Selesai.")
                break # Berhenti jika tidak ada anime lagi di halaman ini

            for item in anime_items:
                title_el = item.find('h3', class_='film-name').find('a')
                if not title_el: continue
                
                catalog.append({
                    'title': title_el.get('title', '').strip(),
                    'detail_url': f"{BASE_URL}{title_el['href']}",
                    'image_url': item.find('img', class_='film-poster-img').get('data-src')
                })

            page_num += 1
            time.sleep(1) # Beri jeda 1 detik antar halaman untuk tidak overload

    return catalog

# --- FUNGSI UTAMA (MAIN) ---

def main():
    print("Memulai scraper...")
    
    # 1. Scrape Halaman Utama (Cepat)
    home_soup = get_soup(f"{BASE_URL}/home")
    if not home_soup:
        print("Kritis: Gagal memuat halaman utama. Proses dihentikan.")
        return

    homepage_data = scrape_homepage_sections(home_soup)
    
    # 2. Scrape Seluruh Katalog (Lama)
    full_catalog = scrape_full_catalog()

    # Simpan katalog ke file terpisah
    with open('anime_catalog.json', 'w', encoding='utf-8') as f:
        json.dump(full_catalog, f, ensure_ascii=False, indent=2)
    print(f"\n{len(full_catalog)} anime dari katalog berhasil disimpan di 'anime_catalog.json'")

    # 3. Ambil URL Stream HANYA untuk anime di halaman utama (agar tidak terlalu lama)
    print("\nMengambil URL stream untuk anime di Halaman Utama...")
    driver = setup_selenium_driver()
    for section in ['spotlight', 'latest_episodes']:
        for anime in homepage_data[section]:
            anime['stream_url'] = get_stream_url(driver, anime['watch_url'])
    driver.quit()

    # Simpan data halaman utama (dengan stream url) ke file terpisah
    with open('anime_homepage.json', 'w', encoding='utf-8') as f:
        json.dump(homepage_data, f, ensure_ascii=False, indent=2)
    print("\nData halaman utama berhasil disimpan di 'anime_homepage.json'")

if __name__ == "__main__":
    main()
