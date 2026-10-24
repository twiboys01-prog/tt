import os
import re
import threading
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import platform

KV = '''
<RootWidget>:
    orientation: 'vertical'
    canvas.before:
        Color:
            rgba: 0.07, 0.07, 0.09, 1
        Rectangle:
            pos: self.pos
            size: self.size

    # ===== HEADER =====
    BoxLayout:
        size_hint_y: None
        height: dp(64)
        padding: [dp(20), dp(16), dp(20), dp(8)]

        Label:
            text: "TikTok Downloader"
            font_size: "22sp"
            bold: True
            color: 1, 1, 1, 1
            halign: "left"
            valign: "middle"
            text_size: self.size

    # ===== INPUT & TOMBOL =====
    BoxLayout:
        orientation: 'vertical'
        padding: [dp(16), 0, dp(16), 0]
        spacing: dp(12)

        TextInput:
            id: url_input
            hint_text: "Paste link TikTok di sini...\\n(satu per baris untuk bulk)"
            multiline: True
            size_hint_y: None
            height: dp(140)
            background_normal: ''
            background_color: 0.12, 0.12, 0.15, 1
            foreground_color: 1, 1, 1, 1
            cursor_color: 0.95, 0.30, 0.45, 1
            hint_text_color: 0.45, 0.45, 0.45, 1
            font_size: "14sp"
            padding: [dp(12), dp(12)]

        BoxLayout:
            size_hint_y: None
            height: dp(50)
            spacing: dp(12)

            Button:
                text: "PASTE"
                on_release: app.paste_clipboard()
                background_normal: ''
                background_color: 0.18, 0.18, 0.22, 1
                color: 1, 1, 1, 1
                font_size: "13sp"
                bold: True

            Button:
                text: "DOWNLOAD"
                on_release: app.start_download()
                background_normal: ''
                background_color: 0.95, 0.30, 0.45, 1
                color: 1, 1, 1, 1
                font_size: "13sp"
                bold: True

        Label:
            id: status_label
            text: "Siap menerima link"
            size_hint_y: None
            height: dp(24)
            font_size: "12sp"
            color: 0.55, 0.55, 0.55, 1
            halign: "left"
            text_size: self.size

    # ===== HASIL =====
    ScrollView:
        id: scroll_view
        BoxLayout:
            id: results_box
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            padding: [dp(16), dp(8)]
            spacing: dp(6)
'''


class RootWidget(BoxLayout):
    pass


class TikTokDownloaderApp(App):
    def build(self):
        self.title = "TikTok Downloader"
        self._last_clip = ""
        self._app_start_time = time.time()
        self._download_dir = None
        root = Builder.load_string(KV)
        return root

    def on_start(self):
        self._setup_clipboard_listener()

    # ================= STORAGE =================
    def get_download_dir(self):
        if self._download_dir:
            return self._download_dir
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            files_dir = PythonActivity.mActivity.getExternalFilesDir(None)
            path = os.path.join(str(files_dir), "TikTokDL")
        except Exception:
            path = os.path.join(self.user_data_dir, "TikTokDL")
        os.makedirs(path, exist_ok=True)
        self._download_dir = path
        return path

    # ================= CLIPBOARD AUTO-DETECT =================
    def _setup_clipboard_listener(self):
        if platform != "android":
            return
        try:
            from jnius import autoclass, PythonJavaClass, java_method
            from android import mActivity

            Context = autoclass("android.content.Context")
            clipboard = mActivity.getSystemService(Context.CLIPBOARD_SERVICE)
            app = self

            class Listener(PythonJavaClass):
                __javainterfaces__ = [
                    "android/content/ClipboardManager$OnPrimaryClipChangedListener"
                ]
                __javacontext__ = "app"

                @java_method("()V")
                def onPrimaryClipChanged(self):
                    try:
                        clip = clipboard.getPrimaryClip()
                        if not clip or clip.getItemCount() == 0:
                            return
                        text = clip.getItemAt(0).getText()
                        if not text:
                            return
                        text = str(text)
                        if "tiktok.com" in text or "douyin.com" in text:
                            Clock.schedule_once(
                                lambda dt: app._on_clipboard_text(text), 0.3
                            )
                    except Exception:
                        pass

            self._clipboard_listener = Listener()
            clipboard.addPrimaryClipChangedListener(self._clipboard_listener)
        except Exception as e:
            print(f"[clipboard] listener tidak tersedia: {e}")

    def _on_clipboard_text(self, text):
        text = text.strip()
        if not text or text == self._last_clip:
            return
        if time.time() - self._app_start_time < 3:
            return  # abaikan clipboard lama saat app baru dibuka
        self._last_clip = text

        current = self.root.ids.url_input.text.strip()
        if not current:
            # Input kosong -> isi & langsung download (fitur "copy -> download")
            self.root.ids.url_input.text = text
            self.start_download()
        elif text not in current:
            self.root.ids.url_input.text = current + "\n" + text
            self.set_status("Link ditambahkan ke antrian")

    # ================= UI HELPERS =================
    def set_status(self, msg):
        Clock.schedule_once(lambda dt: setattr(self.root.ids.status_label, "text", msg))

    def add_result(self, text, ok=True):
        from kivy.uix.label import Label

        def _add(dt):
            color = (0.55, 0.90, 0.55, 1) if ok else (0.95, 0.45, 0.45, 1)
            lbl = Label(
                text=text,
                size_hint_y=None,
                height=dp(34),
                font_size="12sp",
                color=color,
                halign="left",
                valign="middle",
                text_size=(self.root.width - dp(40), dp(34)),
            )
            self.root.ids.results_box.add_widget(lbl)
            Clock.schedule_once(lambda _: self._scroll_to_end(), 0.1)

        Clock.schedule_once(_add)

    def _scroll_to_end(self):
        try:
            self.root.ids.scroll_view.scroll_y = 0
        except Exception:
            pass

    def paste_clipboard(self):
        from kivy.core.clipboard import Clipboard
        try:
            text = Clipboard.paste()
            if text:
                self.root.ids.url_input.text = text
                self.set_status(f"Pasted ({len(text)} char)")
            else:
                self.set_status("Clipboard kosong")
        except Exception as e:
            self.set_status(f"Gagal paste: {e}")

    # ================= DOWNLOAD LOGIC =================
    def start_download(self):
        text = self.root.ids.url_input.text.strip()
        if not text:
            self.set_status("Masukkan link dulu")
            return

        links = []
        for line in text.splitlines():
            line = line.strip()
            if line and ("tiktok.com" in line or "douyin.com" in line):
                links.append(line)

        if not links:
            self.set_status("Tidak ada link TikTok/Douyin valid")
            return

        self.root.ids.url_input.text = ""
        self.root.ids.results_box.clear_widgets()
        self.set_status(f"Mengunduh {len(links)} link...")
        threading.Thread(target=self._worker, args=(links,), daemon=True).start()

    def _worker(self, links):
        ok_count = 0
        for i, url in enumerate(links, 1):
            self.set_status(f"[{i}/{len(links)}] Memproses...")
            try:
                ok, msg = self.download_video(url)
                if ok:
                    ok_count += 1
                    self.add_result(f"✓ {msg}", True)
                else:
                    self.add_result(f"✗ {msg}", False)
            except Exception as e:
                self.add_result(f"✗ Error: {str(e)[:80]}", False)
        self.set_status(f"Selesai: {ok_count}/{len(links)} berhasil")

    def _progress_hook(self, d):
        if d.get("status") == "downloading":
            pct = d.get("_percent_str", "").strip()
            speed = d.get("_speed_str", "").strip()
            self.set_status(f"Download... {pct} {speed}")
        elif d.get("status") == "finished":
            self.set_status("Memproses file...")

    def download_video(self, url, attempt=1, max_attempts=3):
        import yt_dlp

        out_dir = self.get_download_dir()
        # Selang-seling strategi TikTok untuk error rehydration yang transien
        variant = (attempt - 1) % 2
        webpage_download = "false" if variant else "true"

        opts = {
            "outtmpl": os.path.join(out_dir, "%(uploader,uploader|video).30s_%(id)s.%(ext)s"),
            "format": "b",  # best single file — tidak butuh ffmpeg
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "socket_timeout": 30,
            "retries": 3,
            "download_archive": os.path.join(out_dir, "archive.txt"),
            "extractor_args": {"tiktok": {"webpage_download": [webpage_download]}},
            "progress_hooks": [self._progress_hook],
        }

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info:
                    title = (info.get("title") or info.get("id") or "video")[:45]
                    return True, title
                return False, "Tidak ada info"
        except yt_dlp.utils.DownloadError as e:
            msg = str(e)
            if "has already been" in msg or "archive" in msg.lower():
                return True, "Sudah pernah didownload (dilewati)"
            if attempt < max_attempts and self._is_retryable(msg):
                time.sleep(4 * attempt)
                return self.download_video(url, attempt + 1, max_attempts)
            return False, self._clean_error(msg)
        except Exception as e:
            if attempt < max_attempts:
                time.sleep(4 * attempt)
                return self.download_video(url, attempt + 1, max_attempts)
            return False, self._clean_error(str(e))

    @staticmethod
    def _is_retryable(msg):
        for s in [
            "rehydration", "webpage video data", "find video in feed",
            "Unexpected response", "429", "502", "503", "Read timed out",
            "Connection reset", "Remote end closed",
        ]:
            if s in msg:
                return True
        return False

    @staticmethod
    def _clean_error(msg):
        if "IP address is blocked" in msg:
            return "IP diblokir sementara, coba lagi nanti"
        if "Fresh cookies" in msg:
            return "Butuh cookies, coba link lain"
        if "Unable to extract" in msg:
            return "Server TikTok menolak, coba lagi"
        return msg[:90]


if __name__ == "__main__":
    TikTokDownloaderApp().run()