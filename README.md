# 🚀 HyperOS-GlobalConvert - Automated APK International Patcher

[![CI Test Suite](https://github.com/mertcqnkld/HyperOS-GlobalConvert/actions/workflows/ci.yml/badge.svg)](https://github.com/mertcqnkld/HyperOS-GlobalConvert/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

> **Genel Amaçlı & Otomatik Android APK Patcher**  
> Kullanıcının girdiği APK linkindeki sistem uygulamasını otomatik olarak indirir, `classes*.dex` dosyalarını ayrıştırır ve yalnızca **method gövdesi içindeki çalıştırılabilir `IS_INTERNATIONAL_BUILD` kullanımlarını** `0x1` (true) yapacak şekilde güvenle patchler.

---

## 🌟 Özellikler (Key Features)

- 🎯 **Sıfır Teknik Detay Girişi**: Kullanıcı arayüzünde sadece **APK URL'si** girmek yeterlidir.
- 🔍 **Hassas Smali Parser**:
  - Yalnızca method gövdesi (`.method ... .end method`) içindeki gerçek field okuma (`sget-boolean`, `sget-boolean/jumbo`, `iget-boolean`) komutlarını yakalar.
  - Field tanımlarına (`.field`), sabitlere, string'lere, yorum satırlarına ve method dışı kodlara **asla dokunmaz**.
  - İlgili opcode'un kullandığı hedef register'ı tespit eder ve hemen altına `const/4 <aynı_register>, 0x1` ekler.
- 🛡️ **Katı Öncesi/Sonrası Diff Denetimi (Verifier)**:
  - Kod tabanında yetkisiz hiçbir satır silinmesine, değiştirilmesine veya alakasız dosya modifikasyonuna izin vermez.
  - Herhangi bir uyumsuzluk durumunda bozuk APK üretmek yerine **işlemi iptal eder ve detaylı hata raporu sunar**.
- 📦 **Kayıpsız APK Yeniden Paketleme (Lossless Repackaging)**:
  - Kaynak dosyaları (`resources.arsc`, `AndroidManifest.xml`, 9patch, assets, native libs) ayrıştırıp bozmaz; yalnızca güncellenen `classes*.dex` dosyalarını orijinal zip konteynerinde değiştirir.
- ✍️ **Otomatik ZipAlign & V1/V2 İmzalama**: Çıktı APK'sı doğrudan cihaza kurulabilir (ready-to-install) şekilde imzalanır.
- 🌐 **Modern Web Arayüzü & Güçlü CLI**: Gerçek zamanlı SSE log akışı, görsel diff inceleyicisi ve tek tıkla indirme.
- ☁️ **GitHub Actions Desteği**: İsterseniz GitHub Actions üzerinden URL girerek bulutta APK derleyebilirsiniz.

---

## 🏗️ Çalışma Mantığı (How It Works)

```
[ APK URL ] ──► [ Downloader ] ──► [ classes*.dex Extractor ]
                                            │
                                            ▼
[ Ready APK ] ◄── [ Signer & Align ] ◄── [ Baksmali Disassembler ]
      ▲                                     │
      │                                     ▼
[ Repackager ] ◄── [ Reassembler ] ◄── [ Strict Patcher & Verifier ]
```

### Örnek Smali Dönüşümü (Before & After)

**Orijinal Smali Kodu:**
```smali
.method public static isInternational()Z
    .registers 2
    .prologue
    sget-boolean v0, Lcom/miui/gallery/util/BuildUtil;->IS_INTERNATIONAL_BUILD:Z

    return v0
.end method
```

**Patchlenmiş Smali Kodu:**
```smali
.method public static isInternational()Z
    .registers 2
    .prologue
    sget-boolean v0, Lcom/miui/gallery/util/BuildUtil;->IS_INTERNATIONAL_BUILD:Z
    const/4 v0, 0x1

    return v0
.end method
```

---

## 🚀 Hızlı Başlangıç (Quick Start)

### Gereksinimler
- **Python 3.9+**
- **Java JRE / JDK 8+** (Sistem PATH'inde `java` komutu tanımlı olmalıdır)

### 1. Kurulum

```bash
# Depoyu klonlayın
git clone https://github.com/mertcqnkld/HyperOS-GlobalConvert.git
cd HyperOS-GlobalConvert

# Bağımlılıkları yükleyin
pip install -r requirements.txt
```

---

### 2. Web Arayüzünü Başlatma (Önerilen)

#### Windows'ta Tek Tıkla:
Doğrudan `run.bat` dosyasına çift tıklayın. Tarayıcınız otomatik olarak `http://localhost:8080` adresinde açılacaktır.

#### Terminalden:
```bash
python app.py
```
veya
```bash
python web/app.py
```

Tarayıcınızda [http://localhost:8080](http://localhost:8080) adresine gidin.
1. APK URL'sini (veya yerel dosya yolunu) yapıştırın.
2. **"Patch Uygula & Global APK Oluştur"** butonuna tıklayın.
3. Canlı işlem konsolunu ve yama sonuçlarını takip edin.
4. Tamamlandığında **İmzalı APK**, **Magisk Modülü (ZIP)** ve **Denetim Raporu**'nu tek tıkla indirin.

---

### 3. Komut Satırı (CLI) Kullanımı

#### İnteraktif Mod:
```bash
python main.py
```
*(Sizden APK URL'si veya yerel dosya yolu isteyecektir)*

#### Doğrudan Parametre ile:
```bash
python main.py https://example.com/downloads/MiuiGallery.apk
```

#### Yerel Dosya ile:
```bash
python main.py C:\path\to\MiuiSettings.apk -o output/
```

---

### 4. GitHub Actions ile Bulutta Çalıştırma (Cloud Runner)

Deponuzu GitHub'a pushladıktan sonra:
1. GitHub reponuzda **Actions** sekmesine gidin.
2. Sol menüden **"Patch APK Online (Cloud Runner)"** workflow'unu seçin.
3. **Run workflow** butonuna basarak doğrudan **APK URL'sini** girin.
4. Workflow tamamlandığında üretilen patchli APK'yı Artifacts bölümünden indirin.

---

## 🧪 Testleri Çalıştırma (Running Tests)

Tüm strict parser kurallarını, diff doğrulayıcıyı ve DEX paketleme mantığını test etmek için:

```bash
python -m unittest discover -s tests -v
```

---

## 📁 Proje Yapısı (Project Structure)

```
HyperOS-GlobalConvert/
├── core/
│   ├── downloader.py       # Akışlı APK indirme ve ZIP başlığı doğrulama
│   ├── dex_extractor.py    # classes*.dex ayıklama ve kayıpsız zip paketleme
│   ├── smali_tools.py      # Baksmali/Smali yönetim ve jar çalıştırma motoru
│   ├── patcher.py          # Katı Smali parser ve register enjeksiyon motoru
│   ├── verifier.py         # Satır satır diff audit ve güvenlik kontrolcüsü
│   ├── signer.py           # V1/V2 APK imzalama ve 4-byte zipalign
│   ├── magisk_generator.py # Magisk/KernelSU flashlanabilir modül üreticisi
│   ├── pipeline.py         # Uçtan uca otomasyon orkestratörü
│   └── models.py           # Veri modelleri ve tip tanımları
├── web/
│   ├── templates/
│   │   └── index.html      # Modern koyu tema Web UI arayüzü
│   ├── static/
│   │   ├── style.css       # Glassmorphism ve animasyonlu tema
│   │   └── app.js          # Canlı konsol ve yama işleyici
│   └── app.py              # Sıfır bağımlılıklı gömülü web sunucusu (port 8080)
├── scripts/
│   └── github_push.py      # Otomatik GitHub push betiği
├── tests/
│   ├── test_patcher.py     # Smali kuralları ve edge-case testleri
│   ├── test_verifier.py    # Diff denetleyici hata yakalama testleri
│   └── test_pipeline.py    # DEX ayıklama, paketleme ve Magisk testleri
├── .github/workflows/
│   ├── ci.yml              # Otomatik test iş akışı
│   └── patch_apk.yml       # Cloud APK derleme iş akışı
├── app.py                  # Web sunucu başlatıcısı
├── main.py                 # CLI arayüzü
├── run.bat                 # Windows çift tıkla başlatıcı menüsü
├── run.sh                  # Linux / macOS başlatıcı scripti
├── requirements.txt        # Opsiyonel bağımlılıklar
├── .gitignore
├── LICENSE                 # MIT Lisansı
└── README.md
```

---

## 📄 Lisans (License)

Bu proje [MIT](LICENSE) lisansı altında sunulmaktadır.
