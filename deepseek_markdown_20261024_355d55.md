# TikTok Downloader APK

Aplikasi Android sederhana untuk download video TikTok tanpa watermark.

## Fitur
- Copy link TikTok → otomatis kedownload (saat app terbuka)
- Paste manual lewat tombol PASTE
- Bulk: tempel beberapa link (satu per baris)
- Modern, minimalis, dark mode

## Cara build APK
1. Push repo ini ke GitHub.
2. Buka tab **Actions** → workflow **Build APK** → tunggu selesai.
3. Download artifact **TikTokDownloader-APK** → extract → install `.apk` di HP.

Atau build lokal (butuh Linux/WSL):
```bash
pip install buildozer cython
buildozer -v android debug