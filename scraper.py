import requests
from bs4 import BeautifulSoup
import json
import os

# URL Target
HOME_URL = "https://aniwatchtv.to/home"

# Header untuk menyamar sebagai browser agar tidak diblokir
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/'
}

def get_soup(url):
    """Fungsi untuk mengambil dan mem-parsing halaman web."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup
    except requests.exceptions.RequestException as e:
        print(f"Error saat mengambil URL {url}: {e}")
        return None

def scrape_spotlight(soup):
    """Fungsi untuk scrape data dari slider spotlight."""
    spotlight_animes = []
    slider = soup.find('div', id='slider')
    if not slider:
        return spotlight_animes

    for item in slider.find_all('div', class_='deslide-item'):
        title_element = item.find('div', class_='desi-head-title')
        description_element = item.find('div', class_='desi-description')
        watch_now_element = item.find('a', class_='btn-primary')
        image_element = item.find('img', class_='film-poster-img')

        if not title_element or not watch_now_element:
            continue

        anime_data = {
            'title': title_element.text.strip(),
            'description': description_element.text.strip() if description_element else 'No description available.',
            'watch_url': f"https://aniwatchtv.to{watch_now_element['href']}",
            'image_url': image_element.get('data-src') or image_element.get('src'),
            'stream_url': None
        }
        spotlight_animes.append(anime_data)
    return spotlight_animes

def scrape_latest_episodes(soup):
    """Fungsi spesifik untuk scrape section 'Latest Episode'."""
    animes = []
    section = soup.find('section', class_='block_area_home')
    if not section:
        return animes

    for item in section.find_all('div', class_='flw-item'):
        title_element = item.find('h3', class_='film-name').find('a')
        image_element = item.find('img', class_='film-poster-img')
        
        if not title_element:
            continue
            
        watch_url = title_element['href']

        anime_data = {
            'title': title_element.get('title', '').strip(),
            'watch_url': f"https://aniwatchtv.to{watch_url}",
            'image_url': image_element.get('data-src') or image_element.get('src'),
            'stream_url': None
        }
        animes.append(anime_data)
    return animes

def get_stream_url(watch_page_url):
    """Fungsi untuk mengambil URL streaming dari halaman tontonan."""
    if not watch_page_url:
        return None
        
    print(f"Mengambil stream dari: {watch_page_url}")
    soup = get_soup(watch_page_url)
    if not soup:
        return None

    iframe = soup.find('iframe', id='iframe-embed')
    if iframe and 'src' in iframe.attrs:
        stream_src = iframe['src']
        print(f"  -> Ditemukan iframe source: {stream_src}")
        return stream_src

    print(f"  -> Gagal menemukan iframe untuk {watch_page_url}")
    return None

def main():
    """Fungsi utama untuk menjalankan scraper."""
    print("Memulai proses scraping dari aniwatchtv.to...")
    
    home_soup = get_soup(HOME_URL)
    if not home_soup:
        print("Gagal memuat halaman utama. Proses dihentikan.")
        return

    spotlight_data = scrape_spotlight(home_soup)
    latest_episodes = scrape_latest_episodes(home_soup)
    
    all_data = {
        'spotlight': spotlight_data,
        'latest_episodes': latest_episodes
    }

    print("Scraping data dasar selesai. Memulai pengambilan URL stream...")

    for section_name, animes in all_data.items():
        print(f"\nMemproses section: '{section_name}'")
        for anime in animes:
            if anime.get('watch_url'):
                stream_url = get_stream_url(anime['watch_url'])
                anime['stream_url'] = stream_url

    print("\nProses scraping selesai.")

    output_path = 'anime_data.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"Data berhasil disimpan di '{output_path}'")

if __name__ == "__main__":
    main()
