# Import statements (sama seperti sebelumnya)
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin, urlparse
import time
import re
import hashlib
import random
from datetime import datetime, date, timedelta
import io
import logging
from contextlib import contextmanager
from typing import List, Dict, Optional, Set, Tuple
import dateparser
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    WebDriverException, 
    NoSuchElementException
)

# ============================================================================
# KONFIGURASI & KONSTANTA
# ============================================================================

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

# Konfigurasi scraping - OPTIMIZED
SCRAPER_CONFIG = {
    'max_articles_per_domain': 1000,
    'max_pages_to_process': 2000,
    'max_crawl_depth': 10,
    'page_timeout': 30,
    'request_timeout': 25,
    'min_content_length': 100,
    'retry_attempts': 2,
    'delay_between_requests': (0.5, 1),
    'selenium_wait_timeout': 10,
    'selenium_page_load_timeout': 40,
    'use_sitemap': True,  # NEW: Enable sitemap parsing
    'sitemap_priority': True  # NEW: Prioritize sitemap URLs
}

# Konfigurasi subdomain discovery
SUBDOMAIN_CONFIG = {
    'use_crtsh': True,
    'use_bruteforce': True,
    'use_search': False,
    'validate_http': True,
    'max_workers': 20,
    'dns_timeout': 5,
    'http_timeout': 10,
}

# Subdomain yang harus di-EXCLUDE
EXCLUDED_SUBDOMAINS = {
    'mail', 'webmail', 'smtp', 'pop', 'imap', 'email', 'mx', 'mx1', 'mx2',
    'cpanel', 'whm', 'plesk', 'panel', 'admin', 'administrator',
    'dev', 'test', 'staging', 'beta', 'demo', 'sandbox', 'qa',
    'ftp', 'sftp', 'ssh', 'vpn', 'proxy', 'cdn', 'cache',
    'db', 'mysql', 'postgres', 'postgresql', 'mongodb', 'database',
    'status', 'monitor', 'analytics', 'stats', 'grafana', 'prometheus',
    'ns', 'ns1', 'ns2', 'dns', 'nameserver', 'server', 'host',
    'git', 'gitlab', 'jenkins', 'ci', 'api-old', 'old', 'backup',
    'autodiscover', 'autoconfig', 'wpad', 'remote', 'relay'
}

EXCLUDED_PATTERNS = [
    r'^cpanel\.', r'^webmail\.', r'^mail\.', r'^smtp\.', r'^pop\.', r'^imap\.',
    r'^ftp\.', r'^admin\.', r'-dev\.', r'-test\.', r'-staging\.',
    r'^dev-', r'^test-', r'^old\.', r'^backup\.'
]

# Subdomain akademik untuk brute force
ACADEMIC_SUBDOMAIN_PREFIXES = [
    'www', 'portal', 'akademik', 'academic', 'siakad', 'simpeg',
    'pmb', 'penerimaan', 'admission', 'berita', 'news', 'info',
    'pengumuman', 'announcement', 'perpustakaan', 'library', 'lib',
    'repository', 'repo', 'journal', 'jurnal', 'ejournal', 'e-journal',
    'penelitian', 'research', 'lppm', 'p3m', 'pkm',
    'fakultas', 'faculty', 'fti', 'ft', 'feb', 'fh', 'fik', 'fkip',
    'pascasarjana', 'graduate', 'postgraduate', 'magister', 'doktor',
    'mahasiswa', 'student', 'students', 'kemahasiswaan', 'ormawa',
    'bem', 'senat', 'hima', 'ukm', 'alumni',
    'elearning', 'e-learning', 'lms', 'kuliah', 'lecture', 'moodle',
    'keuangan', 'finance', 'bau', 'bak', 'baak', 'kepegawaian',
    'sdm', 'hr', 'hrm', 'surat', 'correspondence',
    'ppm', 'layanan', 'service', 'pub', 'public', 'umum',
    'career', 'karir', 'cdc', 'tracer', 'tracerstudy',
    'press', 'media', 'publikasi', 'publication', 'humas', 'pr',
    'magazine', 'majalah', 'radio', 'tv', 'streaming'
]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# NEW: SITEMAP PARSER
# ============================================================================

def parse_sitemap_automatic(domain: str) -> Set[str]:
    """
    Automatically parse sitemap dari domain untuk dapat semua URL artikel.
    
    AUTO-DETECT common sitemap locations tanpa perlu input manual.
    """
    all_urls = set()
    
    # Common sitemap locations untuk WordPress, Joomla, custom CMS
    sitemap_candidates = [
        f"https://{domain}/sitemap.xml",
        f"https://{domain}/sitemap_index.xml",
        f"https://{domain}/post-sitemap.xml",
        f"https://{domain}/page-sitemap.xml",
        f"https://{domain}/sitemap-posts.xml",
        f"https://{domain}/news-sitemap.xml",
        f"https://{domain}/article-sitemap.xml",
        f"https://{domain}/wp-sitemap.xml",
        f"https://{domain}/wp-sitemap-posts-post-1.xml",
        f"https://{domain}/sitemap/sitemap.xml",
        f"https://{domain}/sitemaps/sitemap.xml",
        # Joomla
        f"https://{domain}/index.php?option=com_xmap&view=xml",
        # Blogger
        f"https://{domain}/sitemap.xml",
        f"https://{domain}/atom.xml?redirect=false&start-index=1&max-results=500",
        # Custom
        f"https://{domain}/rss",
        f"https://{domain}/feed",
    ]
    
    logger.info(f"🗺️ Parsing sitemaps for {domain}...")
    
    found_sitemaps = 0
    
    for sitemap_url in sitemap_candidates:
        try:
            response = requests.get(
                sitemap_url, 
                timeout=10, 
                headers=HEADERS,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                # Check if valid XML
                content_type = response.headers.get('content-type', '').lower()
                if 'xml' in content_type or 'rss' in content_type or 'atom' in content_type:
                    found_sitemaps += 1
                    logger.info(f"✓ Found sitemap: {sitemap_url}")
                    
                    # Parse XML
                    try:
                        soup = BeautifulSoup(response.text, 'xml')
                        
                        # Check for sitemap index (nested sitemaps)
                        sitemap_tags = soup.find_all('sitemap')
                        if sitemap_tags:
                            # This is a sitemap index, recurse into child sitemaps
                            for sitemap_tag in sitemap_tags:
                                loc = sitemap_tag.find('loc')
                                if loc:
                                    child_url = loc.text.strip()
                                    logger.info(f"  → Following nested sitemap: {child_url}")
                                    try:
                                        child_response = requests.get(child_url, timeout=10, headers=HEADERS)
                                        if child_response.status_code == 200:
                                            child_soup = BeautifulSoup(child_response.text, 'xml')
                                            child_locs = child_soup.find_all('loc')
                                            for loc_tag in child_locs:
                                                url = loc_tag.text.strip()
                                                if url and url.startswith('http'):
                                                    all_urls.add(url)
                                    except:
                                        continue
                        else:
                            # Regular sitemap, extract all URLs
                            locs = soup.find_all('loc')
                            for loc in locs:
                                url = loc.text.strip()
                                if url and url.startswith('http'):
                                    all_urls.add(url)
                            
                            # Also check for RSS/Atom feed links
                            links = soup.find_all('link')
                            for link in links:
                                if link.get('href'):
                                    url = link['href']
                                    if url.startswith('http'):
                                        all_urls.add(url)
                        
                    except Exception as e:
                        logger.debug(f"Error parsing XML from {sitemap_url}: {e}")
                        continue
                        
        except requests.RequestException as e:
            logger.debug(f"Failed to fetch {sitemap_url}: {e}")
            continue
        except Exception as e:
            logger.debug(f"Unexpected error with {sitemap_url}: {e}")
            continue
    
    if found_sitemaps > 0:
        logger.info(f"✓ Sitemap parsing complete: Found {found_sitemaps} sitemaps with {len(all_urls)} URLs")
    else:
        logger.info(f"ℹ️ No sitemaps found for {domain}, will use regular crawling")
    
    return all_urls

# ============================================================================
# SUBDOMAIN DISCOVERY (sama seperti sebelumnya)
# ============================================================================

def discover_via_crtsh(domain: str) -> Set[str]:
    """Discover subdomains via crt.sh."""
    subdomains = set()
    
    try:
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        response = requests.get(url, timeout=30, headers=HEADERS)
        
        if response.status_code == 200:
            try:
                data = response.json()
                for entry in data:
                    name_value = entry.get('name_value', '')
                    for subdomain in name_value.split('\n'):
                        subdomain = subdomain.strip().lower()
                        if subdomain.endswith(domain) and '*' not in subdomain:
                            subdomains.add(subdomain)
                logger.info(f"crt.sh (JSON): Found {len(subdomains)} subdomains")
                return subdomains
            except ValueError:
                logger.warning("crt.sh JSON parsing failed, trying HTML")
        
        url = f"https://crt.sh/?q=%.{domain}"
        response = requests.get(url, timeout=30, headers=HEADERS)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')
            if len(tables) > 1:
                rows = tables[1].find_all('tr')[1:]
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) > 4:
                        subdomain = cells[4].text.strip().lower()
                        if subdomain.endswith(domain) and '*' not in subdomain:
                            subdomains.add(subdomain)
            logger.info(f"crt.sh (HTML): Found {len(subdomains)} subdomains")
        
    except requests.RequestException as e:
        logger.warning(f"crt.sh request failed: {e}")
    except Exception as e:
        logger.error(f"crt.sh unexpected error: {e}")
    
    return subdomains

def discover_via_bruteforce(domain: str, max_workers: int = 20) -> Set[str]:
    """Brute force common academic subdomains."""
    subdomains = set()
    candidates = [f"{prefix}.{domain}" for prefix in ACADEMIC_SUBDOMAIN_PREFIXES]
    
    def check_subdomain(subdomain: str) -> Tuple[str, bool]:
        try:
            socket.gethostbyname(subdomain)
            try:
                response = requests.head(
                    f"https://{subdomain}", 
                    timeout=5, 
                    allow_redirects=True,
                    headers=HEADERS
                )
                if response.status_code < 500:
                    return subdomain, True
            except:
                return subdomain, True
        except (socket.gaierror, socket.timeout):
            return subdomain, False
        except Exception:
            return subdomain, False
        
        return subdomain, False
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_subdomain, sub): sub for sub in candidates}
        
        for future in as_completed(futures):
            subdomain, exists = future.result()
            if exists:
                subdomains.add(subdomain)
                logger.debug(f"Brute force found: {subdomain}")
    
    logger.info(f"Brute force: Found {len(subdomains)} valid subdomains")
    return subdomains

def should_exclude_subdomain(subdomain: str, base_domain: str) -> bool:
    """Check if subdomain should be excluded."""
    if not subdomain.endswith(base_domain):
        return True
    
    prefix = subdomain.replace(f".{base_domain}", "").replace(base_domain, "")
    
    if prefix in EXCLUDED_SUBDOMAINS:
        logger.debug(f"Excluding subdomain (exact match): {subdomain}")
        return True
    
    for pattern in EXCLUDED_PATTERNS:
        if re.search(pattern, subdomain):
            logger.debug(f"Excluding subdomain (pattern match): {subdomain}")
            return True
    
    parts = subdomain.replace(base_domain, "").strip('.').split('.')
    if len(parts) > 3:
        logger.debug(f"Excluding subdomain (too many levels): {subdomain}")
        return True
    
    return False

def validate_subdomain_for_scraping(subdomain: str) -> bool:
    """Validate if subdomain is scrapable."""
    try:
        response = requests.head(
            f"https://{subdomain}",
            timeout=10,
            allow_redirects=True,
            headers=HEADERS
        )
        
        final_domain = urlparse(response.url).netloc
        base_parts = subdomain.split('.')[-2:]
        if not final_domain.endswith('.'.join(base_parts)):
            logger.debug(f"Subdomain redirects externally: {subdomain}")
            return False
        
        if response.status_code < 400:
            content_type = response.headers.get('content-type', '')
            if 'html' in content_type.lower():
                return True
        
    except requests.RequestException:
        try:
            response = requests.head(
                f"http://{subdomain}",
                timeout=10,
                allow_redirects=True,
                headers=HEADERS
            )
            
            if response.status_code < 400:
                content_type = response.headers.get('content-type', '')
                if 'html' in content_type.lower():
                    return True
        except:
            pass
    
    logger.debug(f"Subdomain not scrapable: {subdomain}")
    return False

def find_subdomains_multi_method(domain: str) -> Tuple[List[str], dict]:
    """Discover subdomains using multiple methods with filtering."""
    start_time = time.time()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    all_subdomains: Set[str] = set()
    stats = {
        'crtsh': 0,
        'bruteforce': 0,
        'total_raw': 0,
        'excluded': 0,
        'invalid_http': 0,
        'final_valid': 0
    }
    
    all_subdomains.add(domain)
    
    # METHOD 1: crt.sh
    if SUBDOMAIN_CONFIG['use_crtsh']:
        status_text.text("🔍 Method 1/2: Certificate Transparency (crt.sh)...")
        progress_bar.progress(10)
        
        crtsh_subs = discover_via_crtsh(domain)
        stats['crtsh'] = len(crtsh_subs)
        all_subdomains.update(crtsh_subs)
        
        progress_bar.progress(40)
    
    # METHOD 2: Brute Force
    if SUBDOMAIN_CONFIG['use_bruteforce']:
        status_text.text("🔍 Method 2/2: DNS Brute Force (Academic subdomains)...")
        progress_bar.progress(50)
        
        brute_subs = discover_via_bruteforce(domain, max_workers=SUBDOMAIN_CONFIG['max_workers'])
        stats['bruteforce'] = len(brute_subs)
        all_subdomains.update(brute_subs)
        
        progress_bar.progress(70)
    
    stats['total_raw'] = len(all_subdomains)
    
    # FILTERING
    status_text.text("🔧 Filtering excluded subdomains (cpanel, mail, etc.)...")
    progress_bar.progress(75)
    
    filtered_subdomains = set()
    for subdomain in all_subdomains:
        if not should_exclude_subdomain(subdomain, domain):
            filtered_subdomains.add(subdomain)
        else:
            stats['excluded'] += 1
    
    progress_bar.progress(80)
    
    # VALIDATION
    if SUBDOMAIN_CONFIG['validate_http'] and len(filtered_subdomains) > 1:
        status_text.text("✅ Validating HTTP accessibility...")
        
        valid_subdomains = set()
        valid_subdomains.add(domain)
        
        other_subs = [s for s in filtered_subdomains if s != domain]
        
        def validate_wrapper(subdomain):
            is_valid = validate_subdomain_for_scraping(subdomain)
            return subdomain, is_valid
        
        with ThreadPoolExecutor(max_workers=SUBDOMAIN_CONFIG['max_workers']) as executor:
            futures = {executor.submit(validate_wrapper, sub): sub for sub in other_subs}
            
            completed = 0
            for future in as_completed(futures):
                subdomain, is_valid = future.result()
                if is_valid:
                    valid_subdomains.add(subdomain)
                else:
                    stats['invalid_http'] += 1
                
                completed += 1
                validation_progress = 80 + int(19 * (completed / len(other_subs)))
                progress_bar.progress(min(validation_progress, 99))
        
        filtered_subdomains = valid_subdomains
    
    stats['final_valid'] = len(filtered_subdomains)
    
    final_subdomains = sorted(list(filtered_subdomains))
    
    progress_bar.progress(100)
    time.sleep(0.5)
    progress_bar.empty()
    status_text.empty()
    
    duration = time.time() - start_time
    stats['duration'] = duration
    
    logger.info(f"Subdomain Discovery: crt.sh={stats['crtsh']}, brute={stats['bruteforce']}, " + 
                f"excluded={stats['excluded']}, valid={stats['final_valid']}, time={duration:.2f}s")
    
    return final_subdomains, stats

# ============================================================================
# SELENIUM DRIVER (sama seperti sebelumnya)
# ============================================================================

@contextmanager
def get_selenium_driver():
    """Context manager untuk Selenium driver."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-agent={HEADERS['User-Agent']}")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-images")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(SCRAPER_CONFIG['selenium_page_load_timeout'])
        
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": HEADERS['User-Agent']
        })
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.info("Selenium driver initialized successfully")
        yield driver
    except Exception as e:
        logger.error(f"Failed to initialize Selenium driver: {e}")
        raise
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Selenium driver closed successfully")
            except Exception as e:
                logger.error(f"Error closing Selenium driver: {e}")

# ============================================================================
# UTILITY FUNCTIONS (sama seperti sebelumnya)
# ============================================================================

def format_duration(seconds: float) -> str:
    """Format durasi dalam format yang readable."""
    if seconds < 60:
        return f"{seconds:.1f} detik"
    mins, secs = divmod(seconds, 60)
    if mins < 60:
        return f"{int(mins)} menit {secs:.1f} detik"
    hours, mins = divmod(mins, 60)
    return f"{int(hours)} jam {int(mins)} menit {secs:.1f} detik"

def normalize_url(url: str) -> str:
    """Normalize URL untuk menghindari duplikasi."""
    parsed = urlparse(url)
    query_params = parsed.query
    tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'fbclid', 'gclid']
    if query_params:
        params = [p for p in query_params.split('&') if not any(tp in p for tp in tracking_params)]
        query_params = '&'.join(params)
    
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
    if query_params:
        normalized += f"?{query_params}"
    
    return normalized.lower()

def is_valid_article_url(url: str, base_domain: str) -> bool:
    """Validasi apakah URL kemungkinan artikel."""
    parsed = urlparse(url)
    
    if parsed.netloc != base_domain:
        return False
    
    exclude_patterns = [
        r'/tag/', r'/category/', r'/author/', r'/page/',
        r'/wp-content/', r'/wp-includes/', r'/wp-admin/',
        r'/feed/', r'/rss/', r'/sitemap',
        r'\.(jpg|jpeg|png|gif|pdf|zip|rar|doc|docx|xls|xlsx)$',
        r'/login', r'/register', r'/cart', r'/checkout'
    ]
    
    path = parsed.path.lower()
    for pattern in exclude_patterns:
        if re.search(pattern, path):
            return False
    
    return True

def create_content_hash(title: str, content: str, date_str: str) -> str:
    """Buat hash unik untuk deteksi duplikasi."""
    combined = f"{title.lower().strip()}|{content[:200].lower().strip()}|{date_str}"
    return hashlib.sha256(combined.encode()).hexdigest()

def parse_date_advanced(text: str, page_html: str = None) -> Optional[date]:
    """Parse tanggal dengan multiple strategies."""
    if not text:
        return None
    
    try:
        parsed = dateparser.parse(
            text, 
            languages=['id', 'en'],
            settings={
                'STRICT_PARSING': False,
                'PREFER_DAY_OF_MONTH': 'first',
                'RETURN_AS_TIMEZONE_AWARE': False
            }
        )
        if parsed:
            return parsed.date()
    except Exception as e:
        logger.debug(f"Dateparser failed: {e}")
    
    text_clean = text.strip().lower()
    month_map = {
        'januari': '01', 'februari': '02', 'maret': '03', 'april': '04',
        'mei': '05', 'juni': '06', 'juli': '07', 'agustus': '08',
        'september': '09', 'oktober': '10', 'november': '11', 'desember': '12',
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'mei': '05', 'jun': '06', 'jul': '07', 'agu': '08', 'agust': '08',
        'sep': '09', 'okt': '10', 'nov': '11', 'des': '12'
    }
    
    pattern = r'(\d{1,2})\s+(' + '|'.join(month_map.keys()) + r')\s+(\d{4})'
    match = re.search(pattern, text_clean)
    if match:
        day, month, year = match.groups()
        month_num = month_map[month]
        try:
            return date(int(year), int(month_num), int(day))
        except ValueError:
            pass
    
    iso_pattern = r'(\d{4})-(\d{2})-(\d{2})'
    match = re.search(iso_pattern, text_clean)
    if match:
        year, month, day = match.groups()
        try:
            return date(int(year), int(month), int(day))
        except ValueError:
            pass
    
    if page_html:
        meta_patterns = [
            r'<meta[^>]+property="article:published_time"[^>]+content="([^"]+)"',
            r'<meta[^>]+name="date"[^>]+content="([^"]+)"',
            r'<time[^>]+datetime="([^"]+)"'
        ]
        for pattern in meta_patterns:
            match = re.search(pattern, page_html, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                parsed = dateparser.parse(date_str)
                if parsed:
                    return parsed.date()
    
    logger.debug(f"Failed to parse date: {text}")
    return None

# ============================================================================
# ARTICLE EXTRACTION (sama seperti sebelumnya, tapi tambah logging)
# ============================================================================

def extract_article_selenium_enhanced(
    driver: webdriver.Chrome, 
    url: str, 
    max_retries: int = 2
) -> Optional[Dict[str, str]]:
    """Enhanced article extraction dengan Selenium."""
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Extracting article from {url} (attempt {attempt + 1}/{max_retries + 1})")
            
            driver.get(url)
            wait = WebDriverWait(driver, SCRAPER_CONFIG['selenium_wait_timeout'])
            
            article_selectors = ["article", ".post-content", ".entry-content", ".article-content", "main"]
            
            article_loaded = False
            for selector in article_selectors:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    article_loaded = True
                    break
                except TimeoutException:
                    continue
            
            if not article_loaded:
                try:
                    wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
                except TimeoutException:
                    logger.warning(f"Page structure not recognized: {url}")
                    if attempt < max_retries:
                        time.sleep(3)
                        continue
                    return None
            
            title = ""
            title_selectors = [
                ("TAG_NAME", "h1"),
                ("CSS_SELECTOR", ".entry-title"),
                ("CSS_SELECTOR", ".post-title"),
                ("CSS_SELECTOR", "article h1")
            ]
            
            for by_type, selector in title_selectors:
                try:
                    if by_type == "TAG_NAME":
                        title = driver.find_element(By.TAG_NAME, selector).text.strip()
                    else:
                        title = driver.find_element(By.CSS_SELECTOR, selector).text.strip()
                    if title:
                        break
                except NoSuchElementException:
                    continue
            
            if not title:
                title = driver.title.strip() or "Tanpa Judul"
            
            content = ""
            content_selectors = [
                ".entry-content p", ".post-content p", ".article-content p",
                "article p", "main p"
            ]
            
            for selector in content_selectors:
                try:
                    paragraphs = driver.find_elements(By.CSS_SELECTOR, selector)
                    content = ' '.join(p.text.strip() for p in paragraphs if p.text.strip())
                    if len(content) >= SCRAPER_CONFIG['min_content_length']:
                        break
                except NoSuchElementException:
                    continue
            
            if len(content) < SCRAPER_CONFIG['min_content_length']:
                try:
                    all_paragraphs = driver.find_elements(By.TAG_NAME, "p")
                    content = ' '.join(p.text.strip() for p in all_paragraphs if p.text.strip())
                except Exception:
                    pass
            
            if len(content) < SCRAPER_CONFIG['min_content_length']:
                logger.debug(f"Content too short ({len(content)} chars): {url}")
                return None
            
            page_source = driver.page_source
            date_obj = None
            
            try:
                time_elements = driver.find_elements(By.TAG_NAME, "time")
                for elem in time_elements:
                    datetime_attr = elem.get_attribute("datetime")
                    if datetime_attr:
                        date_obj = parse_date_advanced(datetime_attr, page_source)
                        if date_obj:
                            break
                    text_content = elem.text
                    if text_content:
                        date_obj = parse_date_advanced(text_content, page_source)
                        if date_obj:
                            break
            except Exception as e:
                logger.debug(f"Time tag extraction failed: {e}")
            
            if not date_obj:
                meta_patterns = [
                    r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']',
                    r'<meta[^>]+name=["\']date["\'][^>]+content=["\']([^"\']+)["\']',
                    r'<meta[^>]+property=["\']og:published_time["\'][^>]+content=["\']([^"\']+)["\']'
                ]
                for pattern in meta_patterns:
                    match = re.search(pattern, page_source, re.IGNORECASE)
                    if match:
                        date_str = match.group(1)
                        date_obj = parse_date_advanced(date_str, page_source)
                        if date_obj:
                            break
            
            if not date_obj:
                date_patterns = [
                    r'\b(\d{1,2}\s+(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+\d{4})\b',
                    r'\b(\d{4}-\d{2}-\d{2})\b',
                    r'\b(\d{1,2}/\d{1,2}/\d{4})\b'
                ]
                for pattern in date_patterns:
                    match = re.search(pattern, page_source, re.IGNORECASE)
                    if match:
                        date_str = match.group(1)
                        date_obj = parse_date_advanced(date_str, page_source)
                        if date_obj:
                            break
            
            if not date_obj:
                logger.debug(f"No date found for: {url}, using today's date")
                date_obj = date.today()
            
            today = date.today()
            min_reasonable_date = date(2000, 1, 1)
            max_reasonable_date = today + timedelta(days=365)
            
            if not (min_reasonable_date <= date_obj <= max_reasonable_date):
                logger.warning(
                    f"⚠️ Unreasonable date {date_obj} for article at {url}, skipping "
                    f"(Expected between {min_reasonable_date} and {max_reasonable_date})"
                )
                return None
            
            image_url = ""
            image_selectors = [
                "meta[property='og:image']",
                "meta[name='twitter:image']",
                ".wp-post-image",
                ".featured-image img",
                "article img",
                ".entry-content img",
                ".post-thumbnail img"
            ]
            
            for selector in image_selectors:
                try:
                    if selector.startswith("meta"):
                        elem = driver.find_element(By.CSS_SELECTOR, selector)
                        image_url = elem.get_attribute("content")
                    else:
                        elem = driver.find_element(By.CSS_SELECTOR, selector)
                        image_url = elem.get_attribute("src")
                    
                    if image_url and image_url.startswith('http'):
                        break
                except NoSuchElementException:
                    continue
            
            article = {
                'Judul': title,
                'Isi': content,
                'Tanggal Publish': date_obj.strftime('%Y-%m-%d'),
                'Tanggal Scraper': datetime.now().strftime('%Y-%m-%d'),
                'URL': url,
                'Gambar': image_url or ''
            }
            
            logger.info(f"✓ Successfully extracted: {title[:50]}...")
            return article
            
        except TimeoutException:
            logger.warning(f"Timeout loading {url} (attempt {attempt + 1})")
            if attempt < max_retries:
                time.sleep(3)
                continue
            return None
            
        except WebDriverException as e:
            logger.error(f"WebDriver error on {url}: {e}")
            if attempt < max_retries:
                time.sleep(3)
                continue
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error extracting {url}: {e}")
            return None
    
    return None

# ============================================================================
# CRAWLING LOGIC WITH SITEMAP INTEGRATION
# ============================================================================

def crawl_domain_enhanced(
    driver: webdriver.Chrome,
    base_url: str, 
    start_date: date, 
    end_date: date,
    progress_callback=None
) -> List[Dict[str, str]]:
    """Enhanced crawling dengan sitemap integration."""
    articles = []
    duplicate_hashes: Set[str] = set()
    visited_urls: Set[str] = set()
    
    base_domain = urlparse(base_url).netloc
    
    # NEW: Parse sitemap OTOMATIS
    sitemap_urls = set()
    if SCRAPER_CONFIG['use_sitemap']:
        status_msg = st.empty()
        status_msg.info(f"🗺️ Parsing sitemaps untuk {base_domain}...")
        sitemap_urls = parse_sitemap_automatic(base_domain)
        if sitemap_urls:
            status_msg.success(f"✓ Found {len(sitemap_urls)} URLs dari sitemap!")
            time.sleep(1)
        status_msg.empty()
    
    # Initialize queue
    queue = [(0, base_url, 0)]
    
    # Add sitemap URLs to queue dengan PRIORITY TINGGI
    if sitemap_urls and SCRAPER_CONFIG['sitemap_priority']:
        logger.info(f"Adding {len(sitemap_urls)} URLs from sitemap to queue with high priority")
        for url in sitemap_urls:
            if is_valid_article_url(url, base_domain):
                queue.append((-1, url, 0))  # Priority -1 = highest
    
    processed_count = 0
    max_process = SCRAPER_CONFIG['max_pages_to_process']
    max_articles = SCRAPER_CONFIG['max_articles_per_domain']
    max_depth = SCRAPER_CONFIG['max_crawl_depth']
    
    logger.info(f"Starting crawl of {base_url}")
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    while queue and processed_count < max_process and len(articles) < max_articles:
        # Check if user requested stop
        if hasattr(st.session_state, 'stop_scraping') and st.session_state.stop_scraping:
            logger.info(f"Crawl stopped by user at {processed_count} pages, {len(articles)} articles")
            break
        
        queue.sort()
        priority, url, depth = queue.pop(0)
        
        url = normalize_url(url)
        
        if url in visited_urls or depth > max_depth:
            continue
        
        visited_urls.add(url)
        processed_count += 1
        
        if progress_callback:
            progress_callback(processed_count, max_process, len(articles))
        
        logger.info(f"Processing [{processed_count}/{max_process}] depth={depth}: {url}")
        
        try:
            response = session.get(
                url, 
                timeout=SCRAPER_CONFIG['request_timeout'],
                allow_redirects=True
            )
            
            if response.status_code != 200:
                logger.debug(f"Non-200 status ({response.status_code}): {url}")
                continue
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            is_article = False
            if soup.find('h1') and len(soup.get_text()) > 800:
                is_article = True
            
            if is_article:
                article = extract_article_selenium_enhanced(driver, url)
                
                if article:
                    try:
                        article_date = date.fromisoformat(article['Tanggal Publish'])
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"⚠️ Invalid date format '{article['Tanggal Publish']}', using today's date"
                        )
                        article_date = date.today()
                        article['Tanggal Publish'] = article_date.strftime('%Y-%m-%d')
                    
                    if start_date <= article_date <= end_date:
                        content_hash = create_content_hash(
                            article['Judul'], 
                            article['Isi'], 
                            article['Tanggal Publish']
                        )
                        
                        if content_hash not in duplicate_hashes:
                            duplicate_hashes.add(content_hash)
                            articles.append(article)
                            logger.info(
                                f"✓ Article added ({len(articles)}/{max_articles}): "
                                f"{article['Judul'][:50]}... [Date: {article_date}]"
                            )
                        else:
                            logger.debug(f"Duplicate article skipped: {article['Judul'][:50]}...")
                    else:
                        logger.info(
                            f"⏭️ Article SKIPPED (outside date range): {article['Judul'][:50]}... "
                            f"[Article date: {article_date}, Filter: {start_date} to {end_date}]"
                        )
            
            # Crawl links (jika belum cukup dari sitemap)
            links_found = 0
            for link_tag in soup.find_all('a', href=True, limit=200):
                href = link_tag['href']
                full_url = urljoin(url, href)
                full_url = normalize_url(full_url)
                
                if not is_valid_article_url(full_url, base_domain):
                    continue
                
                if full_url not in visited_urls:
                    link_priority = depth + 1
                    # Prioritize article-like URLs
                    if '/artikel/' in full_url or '/berita/' in full_url or re.search(r'/\d{4}/', full_url):
                        link_priority = depth  # Same level priority
                    
                    queue.append((link_priority, full_url, depth + 1))
                    links_found += 1
            
            logger.debug(f"Found {links_found} new links from {url}")
            
            delay = random.uniform(*SCRAPER_CONFIG['delay_between_requests'])
            time.sleep(delay)
            
        except requests.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error processing {url}: {e}")
            continue
    
    logger.info(f"Crawl completed: {len(articles)} articles found, {processed_count} pages processed")
    return articles

# ============================================================================
# STREAMLIT UI
# ============================================================================

def display_subdomain_discovery_results(subdomains: List[str], stats: dict, domain: str = ""):
    """Display subdomain discovery results."""
    
    st.success(f"✅ Subdomain scan selesai: **{len(subdomains)} subdomain valid** ditemukan dalam {format_duration(stats['duration'])}")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🔍 crt.sh", stats['crtsh'])
    col2.metric("💪 Brute Force", stats['bruteforce'])
    col3.metric("🚫 Excluded", stats['excluded'])
    col4.metric("✅ Valid", stats['final_valid'])
    
    with st.expander("📊 Detail Discovery Process", expanded=False):
        st.markdown(f"""
        **Discovery Methods Summary:**
        
        **1. Raw Discovery:**
        - Certificate Transparency (crt.sh): **{stats['crtsh']}** subdomains
        - DNS Brute Force (Academic): **{stats['bruteforce']}** subdomains
        - **Total Raw Discovered:** {stats['total_raw']} unique subdomains
        
        **2. Smart Filtering:**
        - Excluded (cpanel, mail, webmail, dev, test, etc.): **{stats['excluded']}** subdomains
        - Invalid HTTP (offline, error, non-HTML): **{stats['invalid_http']}** subdomains
        
        **3. Final Result:**
        - **Valid & Scrapable Subdomains:** {stats['final_valid']}
        - **Success Rate:** {(stats['final_valid'] / stats['total_raw'] * 100) if stats['total_raw'] > 0 else 0:.1f}%
        - **Processing Time:** {format_duration(stats['duration'])}
        """)
    
    with st.expander("📋 Lihat Daftar Subdomain yang Akan Di-scrape", expanded=True):
        subdomain_data = []
        for subdomain in subdomains:
            if subdomain == domain or 'www' in subdomain:
                sub_type = "🌐 Main/Portal"
            elif any(kw in subdomain for kw in ['akademik', 'siakad', 'academic', 'pmb', 'penerimaan']):
                sub_type = "🎓 Academic"
            elif any(kw in subdomain for kw in ['berita', 'news', 'info', 'pengumuman']):
                sub_type = "📰 News/Info"
            elif any(kw in subdomain for kw in ['library', 'perpustakaan', 'repository', 'jurnal', 'journal']):
                sub_type = "📚 Library/Repository"
            elif any(kw in subdomain for kw in ['fakultas', 'faculty', 'fti', 'ft', 'feb']):
                sub_type = "🏛️ Faculty"
            elif any(kw in subdomain for kw in ['mahasiswa', 'student', 'alumni']):
                sub_type = "👨‍🎓 Student Services"
            elif any(kw in subdomain for kw in ['elearning', 'lms', 'kuliah', 'moodle']):
                sub_type = "💻 E-Learning"
            elif any(kw in subdomain for kw in ['research', 'penelitian', 'lppm']):
                sub_type = "🔬 Research"
            else:
                sub_type = "📄 Other"
            
            subdomain_data.append({
                'Subdomain': subdomain,
                'Type': sub_type,
                'URL': f'https://{subdomain}'
            })
        
        df = pd.DataFrame(subdomain_data)
        st.dataframe(df, use_container_width=True, height=400)

def display_results(all_articles, scraping_stats):
    """Display scraping results."""
    stopped = scraping_stats.get('stopped_by_user', False)
    
    if stopped:
        st.markdown("## 📊 Hasil Scraping (Dihentikan)")
        st.info("ℹ️ Scraping dihentikan oleh user, tapi hasil yang sudah diambil tetap tersimpan.")
    else:
        st.markdown("## 📊 Hasil Scraping")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📰 Total Artikel", len(all_articles))
    col2.metric("⏱️ Waktu Scraping", format_duration(scraping_stats.get('scrape_duration', 0)))
    col3.metric("🌐 Subdomains", scraping_stats.get('subdomains_count', 0))
    
    if all_articles:
        tab1, tab2 = st.tabs(["📊 Preview Data", "💾 Download"])
        
        with tab1:
            df = pd.DataFrame(all_articles)
            df['Tanggal Publish'] = pd.to_datetime(df['Tanggal Publish'])
            df = df.sort_values('Tanggal Publish', ascending=False)
            df['Tanggal Publish'] = df['Tanggal Publish'].dt.strftime('%Y-%m-%d')
            
            display_df = df.copy()
            display_df['Isi (Preview)'] = display_df['Isi'].apply(
                lambda x: (x[:200] + "...") if len(x) > 200 else x
            )
            
            display_df = display_df.rename(columns={
                'Tanggal Scraper': '📅 Tanggal Ambil Data',
                'Tanggal Publish': '📰 Tanggal Rilis Artikel'
            })
            
            st.dataframe(
                display_df[['Judul', '📅 Tanggal Ambil Data', '📰 Tanggal Rilis Artikel', 'Isi (Preview)', 'URL', 'Gambar']],
                use_container_width=True,
                height=400
            )
        
        with tab2:
            st.markdown("#### 💾 Download Hasil Scraping")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            domain = scraping_stats.get('domain', 'unknown')
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                csv_data = df[['Judul', 'Tanggal Scraper', 'Tanggal Publish', 'Isi', 'URL', 'Gambar']].to_csv(index=False).encode('utf-8')
                st.download_button(
                    "⬇️ Download CSV",
                    csv_data,
                    f"{domain}_{timestamp}.csv",
                    "text/csv",
                    use_container_width=True
                )
            
            with col2:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df[['Judul', 'Tanggal Scraper', 'Tanggal Publish', 'Isi', 'URL', 'Gambar']].to_excel(
                        writer, index=False, sheet_name='Artefak_Digital'
                    )
                output.seek(0)
                st.download_button(
                    "⬇️ Download Excel",
                    output.getvalue(),
                    f"{domain}_{timestamp}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            with col3:
                json_data = df.to_json(orient='records', force_ascii=False, indent=2).encode('utf-8')
                st.download_button(
                    "⬇️ Download JSON",
                    json_data,
                    f"{domain}_{timestamp}.json",
                    "application/json",
                    use_container_width=True
                )

def main():
    """Main Streamlit application."""
    
    st.set_page_config(
        page_title="Scraper Artefak Digital PTI v2.5",
        page_icon="📰",
        layout="wide"
    )
    
    # Initialize session state
    if 'scraping_complete' not in st.session_state:
        st.session_state.scraping_complete = False
    if 'scraped_articles' not in st.session_state:
        st.session_state.scraped_articles = []
    if 'scraping_stats' not in st.session_state:
        st.session_state.scraping_stats = {}
    if 'stop_scraping' not in st.session_state:
        st.session_state.stop_scraping = False
    
    # Display results if complete
    if st.session_state.scraping_complete:
        st.markdown("---")
        
        # Show results with download options
        display_results(st.session_state.scraped_articles, st.session_state.scraping_stats)
        
        st.markdown("---")
        
        # Reset button AFTER download section
        st.info("💡 Setelah download, klik tombol di bawah untuk scraping lagi dengan konfigurasi baru")
        if st.button("🔄 Scrape Lagi", type="primary", use_container_width=True):
            st.session_state.scraping_complete = False
            st.session_state.scraped_articles = []
            st.session_state.scraping_stats = {}
            st.session_state.stop_scraping = False
            st.rerun()
        return
    
    st.title("📰 Scraper Artefak Digital Pendidikan Tinggi Indonesia")
    st.markdown("**Versi 2.5 - Automatic Sitemap Parsing + Enhanced Coverage**")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Konfigurasi")
        
        domain = st.text_input(
            "🌐 Domain Universitas", 
            value="itpln.ac.id",
            help="Masukkan domain universitas tanpa https://"
        )
        
        st.subheader("📅 Rentang Tanggal")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Dari",
                value=date(2024, 1, 1),
                max_value=date.today()
            )
        with col2:
            end_date = st.date_input(
                "Sampai",
                value=date.today(),
                max_value=date.today()
            )
        
        if start_date > end_date:
            st.error("⚠️ Tanggal awal tidak boleh lebih besar dari tanggal akhir!")
        
        st.markdown("---")
        st.subheader("🔧 Advanced Options")
        
        st.markdown("**Subdomain Discovery:**")
        SUBDOMAIN_CONFIG['use_crtsh'] = st.checkbox(
            "Enable crt.sh", 
            value=True,
            help="Certificate Transparency lookup"
        )
        SUBDOMAIN_CONFIG['use_bruteforce'] = st.checkbox(
            "Enable DNS Brute Force", 
            value=True,
            help="Test common academic subdomains"
        )
        SUBDOMAIN_CONFIG['validate_http'] = st.checkbox(
            "Validate HTTP", 
            value=True,
            help="Only keep HTTP-accessible subdomains"
        )
        
        st.markdown("**Scraping Options:**")
        
        SCRAPER_CONFIG['use_sitemap'] = st.checkbox(
            "🗺️ Auto-Parse Sitemaps",
            value=True,
            help="Automatically find and parse sitemaps (XML, RSS, Atom)"
        )
        
        max_articles = st.slider(
            "Max Artikel per Domain",
            min_value=100,
            max_value=2000,
            value=1000,
            step=100
        )
        SCRAPER_CONFIG['max_articles_per_domain'] = max_articles
        
        max_pages = st.slider(
            "Max Pages per Domain",
            min_value=500,
            max_value=5000,
            value=2000,
            step=500
        )
        SCRAPER_CONFIG['max_pages_to_process'] = max_pages
        
        st.info(f"""
        **📊 Estimasi:**
        - Subdomain discovery: ~60-90 detik
        - Sitemap parsing: ~10-30 detik (jika ada)
        - Scraping: ~3-5 detik/artikel
        - **Total:** ~{(60 + max_articles * 4) / 60:.0f}-{(90 + max_articles * 5) / 60:.0f} menit
        
        **⚙️ Settings:**
        - Max Artikel: {max_articles}
        - Max Pages: {max_pages}
        - Sitemap: {'Enabled ✅' if SCRAPER_CONFIG['use_sitemap'] else 'Disabled ❌'}
        """)
    
    # Main content
    st.markdown("""
    ### ✨ NEW in v2.5: Automatic Sitemap Parsing!
    
    🗺️ **Smart Sitemap Detection:**
    - Automatically finds and parses XML sitemaps
    - Supports WordPress, Joomla, Blogger, custom CMS
    - Detects nested sitemaps (sitemap index)
    - Prioritizes sitemap URLs for faster article discovery
    
    ✅ **All Previous Features:**
    - Multi-method subdomain discovery
    - Smart filtering & validation
    - Dual date columns (publish + scraper)
    - Stop button with session state
    - Enhanced download menu
    
    ### 🚀 Cara Penggunaan:
    1. Masukkan domain universitas
    2. Pilih rentang tanggal
    3. Klik "🚀 Mulai Scraping"
    4. Stop kapan saja jika perlu
    5. Download hasil dalam 3 format
    
    ---
    """)
    
    if st.button("🚀 Mulai Scraping", type="primary", use_container_width=True):
        
        if start_date > end_date:
            st.error("❌ Tanggal awal tidak boleh lebih besar dari tanggal akhir!")
            return
        
        total_start = time.time()
        
        # Phase 1: Subdomain Discovery
        st.markdown("## 🔍 Phase 1: Subdomain Discovery")
        st.info("Menggunakan multi-method: crt.sh + DNS Brute Force + Smart Filtering")
        
        with st.spinner("Discovering subdomains..."):
            subdomains, stats = find_subdomains_multi_method(domain)
        
        display_subdomain_discovery_results(subdomains, stats, domain)
        
        st.markdown("---")
        
        # Phase 2: Article Scraping
        st.markdown("## 📰 Phase 2: Article Scraping")
        
        all_articles = []
        scrape_start = time.time()
        
        progress_bar = st.progress(0)
        status_container = st.empty()
        metrics_container = st.container()
        
        with metrics_container:
            col1, col2, col3, col4 = st.columns(4)
            metric_domain = col1.empty()
            metric_pages = col2.empty()
            metric_articles = col3.empty()
            metric_time = col4.empty()
        
        # Stop button
        control_col1, control_col2 = st.columns([1, 4])
        with control_col1:
            if st.button("🛑 Stop Scraping", type="secondary", use_container_width=True):
                st.session_state.stop_scraping = True
        
        results_container = st.container()
        stopped_by_user = False
        
        with get_selenium_driver() as driver:
            for idx, subdomain in enumerate(subdomains):
                if st.session_state.stop_scraping:
                    stopped_by_user = True
                    st.warning(f"⚠️ Scraping dihentikan pada subdomain {idx+1}/{len(subdomains)}")
                    break
                
                base_url = f"https://{subdomain}"
                
                status_container.info(f"🔄 Scraping {idx+1}/{len(subdomains)}: **{subdomain}**")
                metric_domain.metric("Current Domain", subdomain)
                
                def progress_callback(pages, max_pages, articles_count):
                    progress = (idx / len(subdomains)) + (pages / max_pages / len(subdomains))
                    progress_bar.progress(min(progress, 1.0))
                    metric_pages.metric("Pages", f"{pages}/{max_pages}")
                    metric_articles.metric("Articles", len(all_articles) + articles_count)
                    elapsed = time.time() - scrape_start
                    metric_time.metric("Time", format_duration(elapsed))
                
                domain_articles = crawl_domain_enhanced(
                    driver, base_url, start_date, end_date, progress_callback
                )
                
                all_articles.extend(domain_articles)
                metric_articles.metric("Articles Found", len(all_articles))
                
                with results_container:
                    if domain_articles:
                        st.success(f"✓ **{subdomain}**: {len(domain_articles)} artikel (Total: **{len(all_articles)}**)")
                    else:
                        st.info(f"ℹ️ **{subdomain}**: Tidak ada artikel")
        
        scrape_duration = time.time() - scrape_start
        progress_bar.empty()
        status_container.empty()
        
        st.session_state.stop_scraping = False
        st.session_state.scraped_articles = all_articles
        st.session_state.scraping_complete = True
        st.session_state.scraping_stats = {
            'scrape_duration': scrape_duration,
            'subdomains_count': len(subdomains),
            'start_date': start_date,
            'end_date': end_date,
            'domain': domain,
            'stopped_by_user': stopped_by_user
        }
        
        if stopped_by_user:
            st.success(f"✅ Scraping dihentikan. **{len(all_articles)} artikel** tersimpan!")
        else:
            st.success(f"✅ Scraping selesai! **{len(all_articles)} artikel** berhasil diambil!")
        
        # Results will be displayed outside button block (don't call display_results here)
        # Just save to session state, then rerun
        st.rerun()
    
    st.markdown("---")
    st.caption("""
    **Scraper Artefak Digital PTI v2.5 - Automatic Sitemap Parsing**  
    
    **NEW in v2.5:**
    - 🗺️ Automatic sitemap parsing (no manual input needed!)
    - 📈 Better coverage dengan sitemap + crawling
    - ⚡ Faster article discovery
    
    © 2025 | Rakhmadi Irfansyah Putra | Educational Use Only
    """)

if __name__ == "__main__":
    main()
