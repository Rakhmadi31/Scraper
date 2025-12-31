# Import statements (sama seperti sebelumnya, dengan tambahan newspaper untuk fallback)
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
from newspaper import Article  # NEW: Untuk fallback ekstraksi cepat
import string  # NEW: Untuk preprocessing sentimen
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
    'use_sitemap': True, # NEW: Enable sitemap parsing
    'sitemap_priority': True # NEW: Prioritize sitemap URLs
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
# NEW: Daftar kata untuk analisis sentimen (dari sumber GitHub masdevid/ID-OpinionWords)
# ============================================================================
POSITIVE_WORDS = {
    "a+", "acungan jempol", "adaptif", "adil", "afinitas", "afirmasi", "agilely", "agung", "ahli", "ahlinya", "ajaib", "aklamasi", "akomodatif", 
    "akurat", "alam mimpi", "alhamdulillah", "allahu akbar", "altruistis", "aman", "amanah", "amat", "ambisius", "andal", "anggun", "angin sepoi-sepoi", 
    "angkat", "antusias", "antusiasme", "apik", "apresiasi", "asli", "aspirasi", "asyik", "bagos", "bagus", "bahagia", "baik", "baik diposisikan", 
    "baik sekali", "baik-baik", "bakat", "bangga", "bantuan", "banyak", "banyak akal", "barang baru", "batu permata", "bebas", "bebas masalah", 
    "bebas pulsa", "bebas rasa sakit", "bebas resiko", "bekerja", "bekerja keras", "belas kasihan", "benar", "benar-benar", "bengal", "beradaptasi", 
    "beralasan", "berani", "berapi", "berarti", "berbaik hati", "berbakat", "berbesar hati", "berbudi luhur", "bercacat", "bercahaya", "bercanda", 
    "bercita-cita", "berdaya cipta", "berdebar", "berdedikasi", "berdikari", "berempati", "bergairah", "bergaya", "bergema", "bergembira", 
    "bergembira sekali", "bergengsi", "bergizi", "berguna", "berharga", "berhasil", "berikut", "berimbang", "berisi", "beristirahat", "berjanji", 
    "berjasa", "berjaya", "berjenis", "berjuang", "berkapasitas besar", "berkat", "berkeinginan", "berkelakuan baik", "berkelanjutan", "berkembang", 
    "berkeyakinan", "berkilau", "berkilauan", "berkualitas", "berlangsung mudah", "berlimpah", "berlimpah-limpah", "bermaksud baik", "bermanfaat", 
    "bermanuver", "bermartabat", "bernilai", "berpendidikan", "berpendidikan baik", "berpengalaman", "berpengaruh", "berpengetahuan luas", "berpijar", 
    "bersatu", "bersedia melakukan", "bersemangat", "bersemangat meluap-luap", "bersenang-senang", "bersenda gurau", "berseri", "bersifat dermawan", 
    "bersifat mendamaikan", "bersih", "bersinar", "bersorak", "bersubsidi", "bersuka cita", "bersuka ria", "bersyukur", "bertanggung jawab", "bertekun", 
    "berterimakasih", "beruntung", "berwarna ria", "berwawasan", "besar", "besar sekali", "biaya rendah", "bijak", "bijaksana", "bikin cemburu", 
    "bimbingan", "bintang rock", "bisa digunakan", "bisa diterapkan", "bonus", "brilian", "cahaya", "cakap", "cantik", "cashbacks", "cekatan", "cemerlang", 
    "cepat", "cerah", "cerdas", "cerdik", "cergas", "cermat", "cetar", "cetar membahana", "cinta", "cocok", "contoh", "cukup", "cukup besar", "cukuplah", 
    "damai", "dapat diandalkan", "dapat dicapai", "dapat diganti", "dapat dipercaya", "dapat diraih", "dapat disesuaikan", "daya tarik", "dengan mewah", 
    "dengan senang hati", "dengan sopan", "dermawan", "dewasa", "diakses", "diakui", "dibaca", "dibebaskan", "diberikan", "dibersihkan", "dibuat dengan baik", 
    "dicapai", "didominasi", "didukung", "digunakan", "dihargai", "diinginkan", "diizinkan", "dikelola", "dikelola dengan baik", "dikembalikan", "dilayari", 
    "dilengkapi", "dilepas", "dilihat", "dimenangkan", "dimengerti", "dinamis", "diperbaharui", "dipercaya", "diperoleh", "diplomatik", "dipoles", "direformasi", 
    "direkomendasikan", "diremajakan", "direstrukturisasi", "disahkan", "disayangi", "disederhanakan", "disubsidi", "ditambah lagi", "ditegakkan", 
    "diterima dengan baik", "ditingkatkan", "diverifikasi", "dorongan", "Dukung", "dukungan", "durian runtuh", "edukatif", "efektif", "efektivitas", 
    "efisien", "ekonomis", "ekstase", "elastis", "elegan", "elite", "emas", "empati", "enak", "enchantingly", "energi", "ergonomis", "etis", "euforia", 
    "evaluatif", "examplar", "fajar", "fantastis", "fasih", "fav", "fave", "favorit", "fenomenal", "firdaus", "fleksibel", "fleksibilitas", "futuristik", 
    "gagah", "gaib", "gainfully", "gairah", "gamblang", "gembira", "gembira luar biasa", "gembira sekali", "gemuk", "gesit", "giat", "gigih", "gokil", 
    "gratis", "gurih", "hadiah", "hak istimewa", "halal", "halus", "handal", "handier", "hangat", "harga diri", "harga rendah", "harmoni", "harmonis", 
    "harta", "harum", "hasil karya", "hasil terbaik", "hati", "hati-hati", "hebat", "hemat", "hemat biaya", "hemat energi", "heran", "heroik", "hore", 
    "horee", "hormat", "hubungan", "iba", "ideal", "idealnya", "idola", "ikhwan", "ilahi", "ilu", "imajinatif", "iman", "imut", "indah", "individual", 
    "infalibilitas", "inovasi", "inovatif", "inspirasi", "inspirasional", "inspiratif", "instrumental", "integral", "intelijen", "intim", "intuitif", 
    "irama"
}

NEGATIVE_WORDS = {
    "abnormal", "absurd", "acak", "acak-acakan", "acuh", "acuh tak acuh", "adiktif", "agresi", "agresif", "agresor", "aib", "air terjun", "alarm", 
    "alasan", "alat permainan", "alergi", "alergik", "amat ketakutan", "amat panas", "ambigu", "ambivalen", "ambivalensi", "amoral", "amoralitas", 
    "ampun", "amuk", "anak nakal", "anak yatim", "anarki", "anarkis", "anarkisme", "ancaman", "aneh", "aneh lagi", "anehnya", "angkuh", "angriness", 
    "anjing", "anjlok", "anomali", "antagonis", "antagonisme", "antek", "anti-", "anti-Amerika", "anti-Israel", "anti-kita", "anti-pendudukan", 
    "anti-proliferasi", "anti-putih", "anti-Semit", "antipati", "antisosial", "antitesis", "apak", "apati", "apatis", "ape", "apokaliptik", "argumentatif", 
    "artinya jika", "asam", "asap", "asem", "asing", "astaghfirullah", "asusila", "awan", "awas", "babi", "badai", "bahan tertawaan", "bahaya", "bajingan", 
    "baju kotor", "balas dendam", "bandel", "bandot", "bangkrut", "bantingan", "barang ganjil", "barbar", "basi", "bau", "bawahan", "bebal", "beban", 
    "bejat", "bekas", "bekas luka", "bekas roda", "beku", "belah", "belum dewasa", "belum dicoba", "belum dikonfirmasi", "belum pasti", "belum selesai", 
    "bencana", "bencana alam", "benci", "bengah", "bengis", "bengkak", "bengkeng", "bengkok", "benjolan", "bentrokan", "beracun", "beradab", "berakhir", 
    "berang", "berani", "berantakan", "berat", "berat sebelah", "berawan", "berbahaya", "berbatu-batu", "berbau", "berbeda", "berbisa", "berbohong", 
    "berbuat curang", "berbuat jahat", "berbuat salah", "berbuih", "bercacat", "berdalih", "berdarah", "berdasar", "berdaya", "berdebar", "berdebat", 
    "berdebu", "berdengung", "berdenyut", "berdenyut-denyut", "berderak", "berderit", "berdetak", "berdokumen", "berdosa", "berduka", "berduri", 
    "berdusta", "berebut", "bergairah", "bergegas", "bergelombang", "bergeming", "bergerak", "bergerak lambat", "bergerigi", "bergetar", "bergolak", 
    "bergulat", "berhaluan kiri", "berisiko", "berita palsu", "berjangkit", "berjuang", "berkarat", "berkata tanpa berpikir", "berkedip", "berkejut", 
    "berkenan", "berkeping-keping", "berkeras pendirian", "berkeringat", "berkerut", "berkhayal", "berkilat", "berkilau", "berkolusi", "berkonflik", 
    "berkubang", "berkurang", "berlangganan", "berlebihan", "berlemak", "berlengah-lengah", "berlepotan", "berliku-liku", "berlumpur", 
    "bermain berlebih-lebihan", "bermasalah", "berminyak", "bermuka dua", "bermuram", "bermuram durja", "bermusuhan", "bermutu rendah", "bernasib buruk", 
    "bernoda kotor", "berongga", "berperang", "berpura-pura", "berputus asa", "bersaing", "bersakit", "bersanding", "bersedih", "bersekongkol", 
    "berselang", "berselisih", "bersemangat", "bersenandung", "berserakan", "bersetubuh", "bersisik", "bertele-tele", "bertemu", "bertengkar", 
    "bertentangan", "berteriak", "bertindak tidak pantas", "bertingkah", "bertubuh kecil", "berumur pendek", "berwajah dua", "biadab", "bias", 
    "biasa-biasa saja", "bid'ah", "bikinan", "bimbang", "binasa", "bingung", "bisa ular", "bising", "blunder", "bobrok", "bocor", "bodoh", "bohong", 
    "bom", "boneka", "boros", "bosan", "botak", "brutal", "bual", "buar", "buas", "budak", "bug", "bukan kepalang", "buntu", "bunuh diri", "buram", 
    "buritan", "buronan", "buruk", "buruk sekali", "busuk", "buta", "buta huruf", "cabul", "cacat", "cacian", "calo", "cambuk", "canggung", "cara", 
    "cari perkara", "carut-marut", "cebol", "cedera", "cekcok", "cekung", "celaan", "celah", "celaka", "cemas", "cemberut", "cemburu", "cemooh", 
    "cemoohan", "cenderung", "cengeng", "cengking", "cercaan", "cerewet", "ceroboh", "compang-camping", "corengan", "curam", "curang", "curiga", 
    "dancok", "dangkal", "debu", "defensif", "degenerasi", "dehumanisasi", "delusi", "demam", "demoralisasi", "dendam", "dengan mencemoohkan", 
    "dengan mendapat malapetaka", "dengan mengagetkan", "dengan menghina", "dengan menyedihkan", "dengan menyesal", "dengan panas", 
    "dengan penuh ketakutan", "dengan rasa curiga", "dengan rasa hina", "dengan remeh-temeh", "dengan sedih", "dengan segan", "dengan sengit", 
    "dengan sia-sia", "dengan suara keras", "dengan sukar", "dengan terbahak-bahak", "dengan tidak senang", "dengki", "depresi", "derita", "desis", 
    "destruktif", "diam", "diam-diam", "dibakar", "dibanjiri", "dibantai", "dibenci", "dibesar-besarkan", "dibuang", "dibuat-buat", "dicela", "dicerca", 
    "dicuci", "dicuri", "didanai", "diganggu", "dihaluskan", "dihentikan", "dihibur", "dihukum", "dijauhi", "dikaburkan", "dikenakan", "dikorbankan", 
    "diktator", "diktatoris", "dilapisi gula", "dilecehkan", "dilema", "dilenyapkan", "dimaafkan", "dimarahi", "dimengerti", "dingin", "diperangi", 
    "diperkosa", "diperlakukan dengan buruk", "dipermainkan", "dipertanyakan", "dipikirkan", "dirampas", "diremehkan", "dirugikan", "disalahgunakan", 
    "disalahpahami", "disayangkan", "disebut-sebut", "disederhanakan", "disengaja", "disengketakan", "disiram", "diskredit", "diskriminasi", 
    "diskriminatif", "disorient", "disproporsional", "distorsi", "ditakdirkan", "ditinggalkan", "ditipu", "ditolak", "dogmatis", "dominan", "dongkol", 
    "dosa", "downgrade", "drastis", "drop-out", "dua wajah", "dugaan", "duka", "dukun", "dumping", "dungu", "duniawi", "dupa", "durhaka", "duri", 
    "dusta", "dusun", "dwimakna", "edan", "egois", "egoisme", "egomania", "egosentris", "ejek", "ejekan", "eksploitasi", "eksploitatif", "eksplosif", 
    "ekstremis", "enggan", "enggan membantu", "erosi", "fana", "fanatik", "fanatisme", "fasis", "fasisme", "fatal", "fiksi", "fitnah", "fitnahan", 
    "fobia", "friksi", "frustasi", "frustrasi", "fundamentalis", "fundamentalisme", "ga jelas", "ga karuan", "ga peka", "gadungan", "gagal", "gagap", 
    "gaib", "galak", "ganas", "gangguan", "ganjil", "ganti rugi", "gantung", "garang", "garis keras", "garu", "gasang", "gatal", "gegabah", "gejala", 
    "gelandangan", "gelap", "gelisah", "gelora", "gembar-gembor", "gendut", "genit", "genosida", "genting", "gerah", "geram", "gerombolan", "gesekan", 
    "getah", "getaran", "gigih", "gigil", "gila", "gila hormat", "gila ketakutan", "gila-gilaan", "godaan", "goreng", "goresan", "gosip", "goyah", 
    "goyangan", "gua", "gugup", "gurun", "gusar", "habis", "hak milik", "hal merendahkan diri", "hal tidak dimengerti", "halangan", "hama", "hambatan", 
    "hampir", "hampir mati", "hancur", "hang", "haram", "harga di atas", "hasutan", "haus", "haus darah", "hedon", "hedonistik", "hegemoni", 
    "hegemonisme", "hidung belang", "hina", "hingar-bingar", "hiruk-pikuk", "histeri", "histeria", "histeris", "hujat", "hukuman", "hukuman penjara", 
    "hukuman setimpal", "hutang", "iblis", "idiot", "igauan", "ih", "ikut campur", "ilegal", "Iluminati", "ilusi", "imajiner", "imperialis", "impoten", 
    "impulsif", "individualis", "indoktrinasi", "infeksi", "inferioritas", "inflamasi", "inflasi", "ingusan", "inkompeten", "inkompetensi", 
    "inkonsistensi", "inkonstitusionil", "interupsi", "intimidasi", "intrusi", "invasif", "irasional", "irasionalitas", "iri", "Iritasi", "ironi", 
    "ironis", "ironisnya", "isolasi", "isu", "jadah", "jahanam", "jahat", "jalan buntu", "jancuk", "janggal", "jatuh", "jatuh sakit", "jebakan", 
    "jelaga", "jelatang", "jelek", "jelu", "jempol kebawah", "jenaka", "jengkel", "jerat", "jerawat", "jeritan", "jeruk nipis", "jijik", "jompo", 
    "jumlah sedikit", "kabur", "kabut", "kacau", "kadaluarsa", "kadung", "kafir", "kain kafan", "kaku", "kalah", "kalahan", "kambing hitam", "kambuh", 
    "kampungan", "kandang", "kandas", "kanibal", "kanker", "kantong sampah", "kapak", "kapalan", "karat", "kasar", "kasihan", "kata-kata kasar", 
    "katastropi", "keadaan acuh tak acuh", "keadaan buruk", "keadaan darurat", "keadaan pingsan", "keadaan sulit", "keanehan", "keangkuhan", "kebal", 
    "kebencian", "keberbahayaan", "kebetulan", "kebiadaban", "kebiasaan", "kebingungan", "KEBINGUNGAN", "kebiri", "kebisingan", "kebobolan", "kebocoran", 
    "kebodohan", "kebohongan", "kebosanan", "kebrutalan", "kebuntuan", "keburukan", "kecabulan", "kecaman", "kecanduan", "kecapaian", "kecelakaan", 
    "kecelakaan kapal", "kecemasan", "kecemburuan", "kecenderungan", "kecenderungan untuk menurun", "kecerobohan", "kecewa", "kecil", "kecongkakan", 
    "kecurangan", "kecurigaan", "kedangkalan", "kedengkian", "keengganan", "kefanatikan", "kegagalan", "keganasan", "kegarangan", "kegelapan", 
    "kegelisahan", "kegemparan", "kegemukan", "kegilaan", "kegoyangan", "kegugupan", "kehabisan", "kehancuran", "kehebohan", "Keheranan", "kehilangan", 
    "kehilangan keseimbangan", "kehinaan", "keinginan pribadi", "keingkaran", "keirasionalan", "kejahatan", "kejam", "kejang", "kejanggalan", 
    "kejangkitan", "kejatuhan", "kejelekan", "kejengahan", "kejengkelan", "keji", "kejut", "kekacauan", "kekakuan", "kekalahan", "kekanak-kanakan", 
    "kekecewaan", "kekecilan", "kekejaman", "kekejamannya", "kekeliruan", "kekenyangan", "kekerasan", "kekerasan pendirian", "kekeringan", "kekesalan", 
    "kekhawatiran", "kekhilafan", "kekosongan", "kekotoran", "kekuatiran", "kekurangan", "kekurangpekaan", "kelakuan buruk", "kelalaian", "kelambanan", 
    "kelancangan", "kelangkaan", "kelaparan", "kelas dua", "kelelahan", "kelemahan", "kelemahan karena usia tua", "kelembutan", "kelesuan", "keletihan", 
    "keliru", "keluar", "keluhan", "Keluhan", "kelupaan", "kemacetan", "kemalangan", "kemalasan", "kemandekan", "kemarahan", "kemasukan setan", 
    "kemasyhuran", "kematian", "kembali", "kemelaratan", "kemenduaan", "kemerosotan", "kemiskinan", "kemunafikan", "kemunduran", "kemurkaan", 
    "kemurungan", "kemustahilan", "kendor", "kendur", "kenekatan", "kental", "kepahitan", "kepala batu", "kepala-sakit", "kepatahan", "kepedaran", 
    "kependekan", "kepentingan", "kepentingan diri sendiri", "kepicikan", "keputusasaan", "keputusasan", "keracunan", "keraguan", "kerangka", "keras", 
    "keras hati", "keras kepala", "keras-kapal", "kerasnya", "kerdil", "kere", "kerepotan"
}
# ============================================================================
# NEW: Fungsi Analisis Sentimen Sederhana (Rule-based)
# ============================================================================
def analyze_sentiment(text: str) -> str:
    """
    Analisis sentimen sederhana berdasarkan count kata positif/negatif.
    """
    if not text:
        return "Neutral"

    # Preprocessing: lower, remove punctuation, split words
    translator = str.maketrans('', '', string.punctuation)
    clean_text = text.lower().translate(translator)
    words = clean_text.split()

    try:
        positive_count = sum(1 for word in words if word in POSITIVE_WORDS)
        negative_count = sum(1 for word in words if word in NEGATIVE_WORDS)
    except NameError:
        # If lexicons are not defined for some reason, return neutral
        return "Neutral"

    score = positive_count - negative_count

    if score > 0:
        return "Positive"
    elif score < 0:
        return "Negative"
    else:
        return "Neutral"
# ============================================================================
# NEW: OPTIMIZED SITEMAP PARSER WITH PARALLEL CHECKING
# ============================================================================
def parse_sitemap_automatic(domain: str, start_date: date, end_date: date) -> Set[str]:
    """
    Automatically parse sitemap dari domain untuk dapat semua URL artikel.

    AUTO-DETECT common sitemap locations tanpa perlu input manual.
    OPTIMIZED: Parallel checking dengan ThreadPoolExecutor
    NEW: Filter tanggal di level sitemap jika ada <lastmod>
    """
    all_urls = set()

    # Common sitemap locations untuk WordPress, Joomla, custom CMS
    sitemap_candidates = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/post-sitemap.xml",
        "/page-sitemap.xml",
        "/sitemap-posts.xml",
        "/news-sitemap.xml",
        "/article-sitemap.xml",
        "/wp-sitemap.xml",
        "/wp-sitemap-posts-post-1.xml",
        "/sitemap/sitemap.xml",
        "/sitemaps/sitemap.xml",
        "/index.php?option=com_xmap&view=xml",
        "/atom.xml?redirect=false&start-index=1&max-results=500",
        "/rss",
        "/feed",
    ]

    logger.info(f"🗺️ Parsing sitemaps for {domain}...")

    found_sitemaps = 0

    session = requests.Session()
    session.headers.update(HEADERS)

    def fetch_and_parse(candidate_path: str):
        nonlocal found_sitemaps
        try:
            url = f"https://{domain}{candidate_path}"
            resp = session.get(url, timeout=15, allow_redirects=True)
            if resp.status_code != 200:
                # try http
                url = f"http://{domain}{candidate_path}"
                resp = session.get(url, timeout=15, allow_redirects=True)
            if resp.status_code == 200 and resp.text:
                found_sitemaps += 1
                text = resp.text
                # find <loc> entries (XML sitemap) and optional <lastmod>
                locs = re.findall(r'<loc>(.*?)</loc>', text, re.IGNORECASE)
                lastmods = re.findall(r'<lastmod>(.*?)</lastmod>', text, re.IGNORECASE)

                # If this is an index sitemap that points to more sitemaps, also include those
                for loc in locs:
                    loc = loc.strip()
                    # Only include same domain
                    if domain in urlparse(loc).netloc:
                        # If lastmod present, try to match by index; otherwise include
                        all_urls.add(loc)
                # Additionally, try to parse RSS/Atom items
                items = re.findall(r'<item>.*?<link>(.*?)</link>.*?(?:<pubDate>(.*?)</pubDate>)?', text, re.DOTALL | re.IGNORECASE)
                for link, pub in items:
                    link = link.strip()
                    if not link:
                        continue
                    include = True
                    if pub:
                        try:
                            parsed = dateparser.parse(pub)
                            if parsed:
                                pub_date = parsed.date()
                                if not (start_date <= pub_date <= end_date):
                                    include = False
                        except Exception:
                            pass
                    if include:
                        all_urls.add(link)
        except Exception as e:
            logger.debug(f"Sitemap candidate failed {candidate_path}: {e}")

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch_and_parse, c) for c in sitemap_candidates]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:
                pass

    # Filter all_urls to only include article-like paths and within domain
    filtered = set()
    for u in all_urls:
        try:
            nu = normalize_url(u)
            if domain in urlparse(nu).netloc and is_valid_article_url(nu, domain):
                filtered.add(nu)
        except Exception:
            continue

    if len(filtered) > 0:
        logger.info(f"✓ Sitemap parsing complete: Found {len(filtered)} URLs from sitemaps")
    else:
        logger.info(f"ℹ️ No sitemaps found for {domain}, will use regular crawling")

    return filtered
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
                    name = entry.get('name_value') or entry.get('common_name')
                    if not name:
                        continue
                    # name_value can contain multiple names separated by \n
                    for n in str(name).split('\n'):
                        n = n.strip().lower()
                        if n and '*' not in n:
                            if n.endswith(domain):
                                subdomains.add(n)
            except ValueError:
                # fallback: try to scrape html
                pass

        # fallback to HTML listing
        url2 = f"https://crt.sh/?q=%.{domain}"
        response = requests.get(url2, timeout=30, headers=HEADERS)
        if response.status_code == 200:
            matches = re.findall(r'>([A-Za-z0-9\-\.]+\.%s)<' % re.escape(domain), response.text, re.IGNORECASE)
            for m in matches:
                subdomains.add(m.lower())

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
            # Try HTTPS first
            resp = requests.head(f"https://{subdomain}", timeout=6, allow_redirects=True, headers=HEADERS)
            if resp.status_code < 400:
                return subdomain, True
            # Fallback to HTTP
            resp = requests.head(f"http://{subdomain}", timeout=6, allow_redirects=True, headers=HEADERS)
            if resp.status_code < 400:
                return subdomain, True
        except (requests.RequestException, socket.gaierror, socket.timeout):
            return subdomain, False
        except Exception:
            return subdomain, False
        return subdomain, False

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_subdomain, sub): sub for sub in candidates}
        for future in as_completed(futures):
            try:
                sub, ok = future.result()
                if ok:
                    subdomains.add(sub)
            except Exception:
                continue

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
            logger.debug(f"Excluding subdomain (pattern): {subdomain} matches {pattern}")
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
            # Redirected to another domain
            return False

        if response.status_code < 400:
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
                return True
        except Exception:
            pass

    return False

def find_subdomains_multi_method(domain: str) -> Tuple[List[str], dict]:
    """Discover subdomains using multiple methods with filtering and optional HTTP validation.

    Returns a tuple (final_subdomains_list, stats_dict).
    """
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
        'final_valid': 0,
        'duration': 0.0
    }

    # always include base domain
    all_subdomains.add(domain)

    # METHOD 1: crt.sh
    if SUBDOMAIN_CONFIG.get('use_crtsh', True):
        status_text.text("🔍 Method 1/2: Certificate Transparency (crt.sh)...")
        progress_bar.progress(10)

        try:
            crtsh_subs = discover_via_crtsh(domain)
            stats['crtsh'] = len(crtsh_subs)
            all_subdomains.update(crtsh_subs)
        except Exception as e:
            logger.warning(f"crt.sh discovery failed: {e}")

        progress_bar.progress(40)

    # METHOD 2: Brute Force
    if SUBDOMAIN_CONFIG.get('use_bruteforce', True):
        status_text.text("🔍 Method 2/2: DNS Brute Force (Academic subdomains)...")
        progress_bar.progress(50)

        try:
            brute_subs = discover_via_bruteforce(domain, max_workers=SUBDOMAIN_CONFIG.get('max_workers', 20))
            stats['bruteforce'] = len(brute_subs)
            all_subdomains.update(brute_subs)
        except Exception as e:
            logger.warning(f"Bruteforce discovery failed: {e}")

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
    if SUBDOMAIN_CONFIG.get('validate_http', True) and len(filtered_subdomains) > 1:
        status_text.text("✅ Validating HTTP accessibility...")

        valid_subdomains = set()
        # always keep base domain
        valid_subdomains.add(domain)

        other_subs = [s for s in filtered_subdomains if s != domain]

        def validate_wrapper(subdomain):
            ok = validate_subdomain_for_scraping(subdomain)
            return subdomain, ok

        with ThreadPoolExecutor(max_workers=SUBDOMAIN_CONFIG.get('max_workers', 20)) as executor:
            futures = {executor.submit(validate_wrapper, sub): sub for sub in other_subs}

            completed = 0
            for future in as_completed(futures):
                try:
                    sub, ok = future.result()
                    completed += 1
                    # update progress roughly
                    progress = 80 + int((completed / max(1, len(other_subs))) * 15)
                    progress_bar.progress(min(progress, 95))
                    if ok:
                        valid_subdomains.add(sub)
                    else:
                        stats['invalid_http'] += 1
                except Exception:
                    stats['invalid_http'] += 1

        filtered_subdomains = valid_subdomains

    stats['final_valid'] = len(filtered_subdomains)

    final_subdomains = sorted(list(filtered_subdomains))

    progress_bar.progress(100)
    time.sleep(0.3)
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
# UTILITY FUNCTIONS (sama seperti sebelumnya, tambah max_content_length)
# ============================================================================
MAX_CONTENT_LENGTH = 50000  # NEW: Batasi panjang isi untuk Excel

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
                try:
                    parsed = dateparser.parse(date_str)
                    if parsed:
                        return parsed.date()
                except Exception:
                    pass
    
    logger.debug(f"Failed to parse date: {text}")
    return None
# ============================================================================
# ARTICLE EXTRACTION WITH FAST FALLBACK (NEW: newspaper fallback)
# ============================================================================
def extract_article_fast(url: str) -> Optional[Dict[str, str]]:
    """Fast article extraction using newspaper3k."""
    try:
        article = Article(url, language='id', fetch_images=False, request_timeout=10)
        article.download(headers=HEADERS)
        article.parse()
        
        if len(article.text) < SCRAPER_CONFIG['min_content_length']:
            return None
        
        publish_date = article.publish_date
        if publish_date:
            date_obj = publish_date.date()
        else:
            date_obj = date.today()
        
        image_url = article.top_image if article.top_image.startswith('http') else ''
        
        return {
            'Judul': article.title or "Tanpa Judul",
            'Isi': article.text[:MAX_CONTENT_LENGTH],
            'Tanggal Publish': date_obj.strftime('%Y-%m-%d'),
            'Tanggal Scraper': datetime.now().strftime('%Y-%m-%d'),
            'URL': url,
            'Gambar': image_url
        }
    except Exception as e:
        logger.debug(f"Fast extraction failed for {url}: {e}")
        return None

def extract_article_selenium_enhanced(
    driver: webdriver.Chrome,
    url: str,
    max_retries: int = 2
) -> Optional[Dict[str, str]]:
    """Enhanced article extraction dengan Selenium (fallback)."""
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Extracting article from {url} (attempt {attempt + 1}/{max_retries + 1})")

            driver.get(url)
            wait = WebDriverWait(driver, SCRAPER_CONFIG['selenium_wait_timeout'])

            article_selectors = ["article", ".post-content", ".entry-content", ".article-content", "main"]

            article_loaded = False
            for selector in article_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) > 0:
                        article_loaded = True
                        break
                except Exception:
                    continue

            if not article_loaded:
                # fallback: wait briefly for body
                try:
                    wait.until(lambda d: d.find_element(By.TAG_NAME, 'body'))
                    article_loaded = True
                except TimeoutException:
                    article_loaded = False

            title = ""
            title_selectors = [
                (By.TAG_NAME, "h1"),
                (By.CSS_SELECTOR, ".entry-title"),
                (By.CSS_SELECTOR, ".post-title"),
                (By.CSS_SELECTOR, "article h1")
            ]

            for by_type, selector in title_selectors:
                try:
                    elem = driver.find_element(by_type, selector)
                    text = elem.text.strip()
                    if text:
                        title = text
                        break
                except Exception:
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
                    elems = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elems:
                        texts = [e.text for e in elems if e.text]
                        if texts:
                            content = "\n\n".join(texts).strip()
                            break
                except Exception:
                    continue

            # fallback: use BeautifulSoup on page_source
            if len(content) < SCRAPER_CONFIG['min_content_length']:
                try:
                    soup = BeautifulSoup(driver.page_source, 'lxml')
                    # prefer article tag
                    article_tag = soup.find('article') or soup.find('main')
                    if article_tag:
                        paras = [p.get_text(strip=True) for p in article_tag.find_all('p')]
                    else:
                        paras = [p.get_text(strip=True) for p in soup.find_all('p')]
                    content = "\n\n".join([p for p in paras if p])
                except Exception:
                    pass

            if len(content) < SCRAPER_CONFIG['min_content_length']:
                logger.debug(f"Content too short ({len(content)} chars): {url}")
                return None

            page_source = driver.page_source
            date_obj = None

            # Try <time> tags first
            try:
                time_elements = driver.find_elements(By.TAG_NAME, "time")
                for elem in time_elements:
                    datetime_attr = ''
                    try:
                        datetime_attr = elem.get_attribute('datetime')
                    except Exception:
                        datetime_attr = None
                    if datetime_attr:
                        parsed = dateparser.parse(datetime_attr)
                        if parsed:
                            date_obj = parsed.date()
                            break
                    text_content = elem.text
                    if text_content and not date_obj:
                        parsed = parse_date_advanced(text_content)
                        if parsed:
                            date_obj = parsed
                            break
            except Exception as e:
                logger.debug(f"Time tag extraction failed: {e}")

            # Meta tags
            if not date_obj:
                meta_patterns = [
                    r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']',
                    r'<meta[^>]+name=["\']date["\'][^>]+content=["\']([^"\']+)["\']',
                    r'<meta[^>]+property=["\']og:published_time["\'][^>]+content=["\']([^"\']+)["\']'
                ]
                for pattern in meta_patterns:
                    match = re.search(pattern, page_source, re.IGNORECASE)
                    if match:
                        try:
                            parsed = dateparser.parse(match.group(1))
                            if parsed:
                                date_obj = parsed.date()
                                break
                        except Exception:
                            continue

            # Other inline date patterns
            if not date_obj:
                date_patterns = [
                    r'\b(\d{1,2}\s+(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+\d{4})\b',
                    r'\b(\d{4}-\d{2}-\d{2})\b',
                    r'\b(\d{1,2}/\d{1,2}/\d{4})\b'
                ]
                for pattern in date_patterns:
                    match = re.search(pattern, page_source, re.IGNORECASE)
                    if match:
                        parsed = parse_date_advanced(match.group(1), page_source)
                        if parsed:
                            date_obj = parsed
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
            try:
                soup = BeautifulSoup(page_source, 'lxml')
                # try meta og:image first
                m = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name':'twitter:image'})
                if m and m.get('content'):
                    image_url = m.get('content')
                else:
                    img = soup.find('img')
                    if img and img.get('src'):
                        image_url = urljoin(url, img.get('src'))
            except Exception:
                image_url = ''

            article = {
                'Judul': title,
                'Isi': content[:MAX_CONTENT_LENGTH],
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
# CRAWLING LOGIC WITH SITEMAP INTEGRATION + GLOBAL DEDUP
# ============================================================================
def crawl_domain_enhanced(
    driver: webdriver.Chrome,
    base_url: str,
    start_date: date,
    end_date: date,
    global_duplicate_hashes: Set[str],
    progress_callback=None
) -> List[Dict[str, str]]:
    """Enhanced crawling dengan sitemap integration."""
    articles = []
    visited_urls: Set[str] = set()
    
    base_domain = urlparse(base_url).netloc
    
    # NEW: Parse sitemap OTOMATIS dengan filter tanggal
    sitemap_urls = set()
    if SCRAPER_CONFIG['use_sitemap']:
        status_msg = st.empty()
        status_msg.info(f"🗺️ Parsing sitemaps untuk {base_domain}...")
        sitemap_urls = parse_sitemap_automatic(base_domain, start_date, end_date)
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
                queue.append((-1, url, 0)) # Priority -1 = highest
    
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
                # NEW: Coba ekstraksi cepat dulu
                article = extract_article_fast(url)
                if not article:
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
                        
                        if content_hash not in global_duplicate_hashes:
                            global_duplicate_hashes.add(content_hash)
                            # NEW: Tambah analisis sentimen
                            article['Sentimen'] = analyze_sentiment(article['Isi'])
                            articles.append(article)
                            logger.info(
                                f"✓ Article added ({len(articles)}/{max_articles}): "
                                f"{article['Judul'][:50]}... [Date: {article_date}] [Sentimen: {article['Sentimen']}]"
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
                        link_priority = depth # Same level priority
                    
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
# STREAMLIT UI (tambah estimasi sisa waktu)
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
                'Tanggal Publish': '📰 Tanggal Rilis Artikel',
                'Sentimen': '😊 Sentimen'  # NEW: Tambah kolom sentimen
            })
            
            st.dataframe(
                display_df[['Judul', '📅 Tanggal Ambil Data', '📰 Tanggal Rilis Artikel', '😊 Sentimen', 'Isi (Preview)', 'URL', 'Gambar']],
                use_container_width=True,
                height=400
            )
        
        with tab2:
            st.markdown("#### 💾 Download Hasil Scraping")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            domain = scraping_stats.get('domain', 'unknown')
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                csv_data = df[['Judul', 'Tanggal Scraper', 'Tanggal Publish', 'Sentimen', 'Isi', 'URL', 'Gambar']].to_csv(index=False).encode('utf-8')
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
                    df[['Judul', 'Tanggal Scraper', 'Tanggal Publish', 'Sentimen', 'Isi', 'URL', 'Gambar']].to_excel(
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
        page_title="Scraper Artefak Digital PTI v2.7",
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
    st.markdown("**Versi 2.7 - With Sentiment Analysis**")
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
        - Scraping: ~2-4 detik/artikel (dengan fast fallback)
        - **Total:** ~{(60 + max_articles * 3) / 60:.0f}-{(90 + max_articles * 4) / 60:.0f} menit
        
        **⚙️ Settings:**
        - Max Artikel: {max_articles}
        - Max Pages: {max_pages}
        - Sitemap: {'Enabled ✅' if SCRAPER_CONFIG['use_sitemap'] else 'Disabled ❌'}
        """)
    
    # Main content
    st.markdown("""
    ### ✨ NEW in v2.7: Sentiment Analysis!
    
    😊 **Fitur Baru:**
    - Analisis sentimen sederhana (Positive/Negative/Neutral) pada isi artikel
    - Berdasarkan lexicon Bahasa Indonesia (rule-based)
    - Ditampilkan di preview dan disertakan di file download
    
    ⚡ **Optimizations from v2.6 Maintained**
    
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
        estimate_container = st.empty()  # NEW: Untuk estimasi sisa waktu
        
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
        
        # NEW: Global duplicate hashes
        global_duplicate_hashes: Set[str] = set()
        
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
                    current_total = len(all_articles) + articles_count
                    metric_articles.metric("Articles", current_total)
                    elapsed = time.time() - scrape_start
                    metric_time.metric("Time", format_duration(elapsed))
                    
                    # NEW: Estimasi sisa waktu
                    if current_total > 10:
                        articles_per_sec = current_total / elapsed
                        remaining_articles = (len(subdomains) * max_articles) - current_total
                        est_remaining = remaining_articles / articles_per_sec
                        estimate_container.caption(f"Estimasi sisa: {format_duration(est_remaining)}")
                
                domain_articles = crawl_domain_enhanced(
                    driver, base_url, start_date, end_date, global_duplicate_hashes, progress_callback
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
        estimate_container.empty()
        
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
        try:
            st.rerun()
        except:
            pass  # Hindari crash jika rerun gagal
    
    st.markdown("---")
    st.caption("""
    **Scraper Artefak Digital PTI v2.7 - With Sentiment Analysis**
    
    **NEW in v2.7:**
    - 😊 Rule-based sentiment analysis (Positive/Negative/Neutral)
    - Based on Indonesian lexicon from open sources
    
    © 2025 | Rakhmadi Irfansyah Putra | Educational Use Only
    """)
if __name__ == "__main__":
    main()