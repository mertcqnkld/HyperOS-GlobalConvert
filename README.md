# 🚀 GlobalConvertApps - Automated APK International Patcher

[![CI Test Suite](https://github.com/your-username/GlobalConvertApps/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/GlobalConvertApps/actions/workflows/ci.yml)
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
git clone https://github.com/your-username/GlobalConvertApps.git
cd GlobalConvertApps

# Bağımlılıkları yükleyin
pip install -r requirements.txt
```

---

### 2. Web Arayüzünü Başlatma (Önerilen)

```bash
python app.py
```

Tarayıcınızda [http://127.0.0.1:8000](http://127.0.0.1:8000) adresine gidin.
1. APK URL'sini yapıştırın.
2. **"Patch & Build Global APK"** butonuna tıklayın.
3. Canlı logları ve diff inceleyicisini takip edin.
4. Tamamlandığında **"Download APK"** butonuyla imzalı APK'nızı indirin.

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
GlobalConvertApps/
├── core/
│   ├── downloader.py       # Akışlı APK indirme ve ZIP başlığı doğrulama
│   ├── dex_extractor.py    # classes*.dex ayıklama ve kayıpsız zip paketleme
│   ├── smali_tools.py      # Baksmali/Smali yönetim ve jar çalıştırma motoru
│   ├── patcher.py          # Katı Smali parser ve register enjeksiyon motoru
│   ├── verifier.py         # Satır satır diff audit ve güvenlik kontrolcüsü
│   ├── signer.py           # V1/V2 APK imzalama ve 4-byte zipalign
│   ├── pipeline.py         # Uçtan uca otomasyon orkestratörü
│   └── models.py           # Veri modelleri ve tip tanımları
├── web/
│   └── static/
│       └── index.html      # Modern koyu tema Web UI & SSE istemcisi
├── tests/
│   ├── test_patcher.py     # Smali kuralları ve edge-case testleri
│   ├── test_verifier.py    # Diff denetleyici hata yakalama testleri
│   └── test_pipeline.py    # DEX ayıklama ve paketleme testleri
├── .github/workflows/
│   ├── ci.yml              # Otomatik test iş akışı
│   └── patch_apk.yml       # Cloud APK derleme iş akışı
├── app.py                  # FastAPI Web sunucusu
├── main.py                 # Rich destekli CLI arayüzü
├── requirements.txt        # Python bağımlılıkları
├── .gitignore
├── LICENSE                 # MIT Lisansı
└── README.md
```

---

## 📄 Lisans (License)

Bu proje [MIT](LICENSE) lisansı altında sunulmaktadır.
