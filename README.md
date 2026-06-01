# Gym Management System - Karekod (QR) Destekli Akıllı Otomasyon Sistemi

Bu proje; modern spor salonlarının üye kayıt, üyelik süresi takibi ve turnike geçiş kontrol süreçlerini dijitalleştirmek amacıyla geliştirilmiş, bulut entegrasyonlu ve bilgisayarlı görü (Computer Vision) tabanlı bir yönetim yazılımıdır[cite: 11, 13].

### 🛠️ Teknolojik Altyapı & Kullanılan Kütüphaneler
- **Programlama Dili:** Python 3.12+[cite: 11, 13]
- **Bulut Veri Tabanı Mimarisi (Cloud Database):** Google **Firebase Cloud Firestore (NoSQL)**[cite: 11, 13]. Tüm üye kayıtları, bakiye bilgileri ve turnike giriş logları bulut ortamında gerçek zamanlı (real-time) olarak senkronize edilmektedir[cite: 11, 13].
- **Görüntü İşleme & Bilgisayarlı Görü (Computer Vision):** **OpenCV (`cv2`)** ve **PyZbar**[cite: 11, 13]. Turnike kontrol noktalarında webcam/kamera üzerinden gerçek zamanlı dinamik QR Kod tarama ve anlık üyelik geçerlilik doğrulaması yapılmaktadır[cite: 11, 13].
- **Ağ Programlama & Çoklu İş Parçacığı (Multi-threading):** Python `http.server`, `socket` ve `threading` kütüphaneleri[cite: 11]. Üyelerin kendi özel QR erişim kartlarını yerel ağ (WiFi) üzerinden akıllı telefonlarına indirebilmeleri için arka planda asenkron çalışan hafif bir HTTP Web Sunucusu mimarisi barındırır[cite: 11, 13].
- **Kriptografi & Veri Güvenliği:** Kullanıcı şifreleri veri tabanında asla yalın metin (plain text) olarak tutulmaz; **SHA-256 tek yönlü hashing** algoritması ile kriptolanarak maksimum güvenlik sağlanır[cite: 11, 13].

### ⚙️ Sistem Özellikleri & Operasyonel Modüller

1. **Gelişmiş Yönetici Konsolu (Admin Panel):**
   - Yeni üye kaydı, otomatik benzersiz ID üretimi ve esnek üyelik paketleri (1/3/6/12 Aylık veya Özel Tarihli) yönetimi[cite: 11].
   - Üye profilleri üzerinde tam CRUD yetkisi (Arama, Bilgi Düzenleme, Profil Silme)[cite: 11].
   - Firebase tabanlı turnike geçiş loglarının kronolojik olarak anlık izlenmesi[cite: 11].
   - Turnike entegrasyonu için canlı QR kamera tarama modu[cite: 11].

2. **Üye Arayüzü (Member Dashboard):**
   - Kalan üyelik süresinin saniye hassasiyetinde canlı geri sayım (live countdown) takibi[cite: 11, 13].
   - "Transfer My QR Code to Phone" özelliği ile yerel ağ üzerinden mobil cihazlara kablosuz QR kart teslimatı[cite: 11, 13].

### 🔒 Güvenlik Notu
Sistem güvenliği prensipleri gereğince, Firebase yönetim şifrelerini barındıran `serviceAccountKey.json` dosyası bu depoya (repository) dahil edilmemiştir[cite: 11, 12]. Projeyi yerelde test etmek isteyen geliştiriciler, kendi Firebase konsollarından üretecekleri servis anahtarını ana dizine ekleyerek sistemi çalıştırabilirler[cite: 11].

### 🚀 Kurulum ve Çalıştırma

1. Gerekli kütüphaneleri terminale yapıştırarak yükleyin:
```bash
   pip install firebase-admin qrcode[pil] pillow opencv-python pyzbar
   ```[cite: 11]

2. Projeyi başlatın:
```bash
   python main.py
   ```[cite: 11]
