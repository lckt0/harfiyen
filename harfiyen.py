#!/usr/bin/env python3
"""Harfiyen — terminalde kademeli on parmak klavye eğitimi.

Türkçe Q, Türkçe F ve İngilizce (ABD) düzenleri; ISO, ANSI ve 102 tuşlu ANSI;
numpad; JSON ile tanımlanan temalar ve ayarlar (TUI içinden de düzenlenir);
fare desteği; ders, zayıf noktalar, hız testi ve serbest metin modları;
günlük hedef, seri, seviye ve rozetler; tam ekranda parmakların fiziksel
hizasında göstergeler.

Kullanım:
    harfiyen.py                  # kaldığın yerden devam
    harfiyen.py --pencere 10     # bu oturum için ustalık penceresi
    harfiyen.py --sifirla        # ilerlemeyi sıfırla
    harfiyen.py --temalar        # temaları ve dosya yollarını listele

Yalnızca standart kütüphane kullanır. Klavye düzenini işletim sistemi belirler;
uygulama gelen karakteri hedef karakterle karşılaştırır.
"""

import argparse
import collections
import curses
import datetime
import functools
import json
import locale
import math
import os
import random
import re
import shutil
import signal
import socket
import statistics
import struct
import subprocess
import sys
import tempfile
import time
import unicodedata

__version__ = "0.1.0"
UYGULAMA_ADI = "Harfiyen"
KIMLIK = "harfiyen"

# ---------------------------------------------------------------------------
# Dosya yolları (XDG)
# ---------------------------------------------------------------------------


def _xdg(degisken, varsayilan):
    return os.environ.get(degisken) or os.path.expanduser(varsayilan)


VERI_DIZINI = os.path.join(_xdg("XDG_DATA_HOME", "~/.local/share"), KIMLIK)
AYAR_DIZINI = os.path.join(_xdg("XDG_CONFIG_HOME", "~/.config"), KIMLIK)
KAYIT_DOSYASI = os.path.join(VERI_DIZINI, "progress.json")
AYAR_DOSYASI = os.path.join(AYAR_DIZINI, "ayarlar.json")
TEMA_DIZINI = os.path.join(AYAR_DIZINI, "temalar")
METIN_DIZINI = os.path.join(AYAR_DIZINI, "metinler")
# önceki adın ("onparmak-tui") dizinleri: ilk çalıştırmada taşınır
ESKI_VERI_DIZINI = os.path.join(_xdg("XDG_DATA_HOME", "~/.local/share"), "onparmak-tui")
ESKI_AYAR_DIZINI = os.path.join(_xdg("XDG_CONFIG_HOME", "~/.config"), "onparmak-tui")

# ---------------------------------------------------------------------------
# Eğitim ayarları
# ---------------------------------------------------------------------------

PENCERE = 20                      # ustalık için bakılan son deneme sayısı
SIRA = "fjdkslaşeinrıtmuyobghzücvçpöğ"   # Türkçe Q için harf açılma sırası
BASLANGIC_ACIK = 8                # ilk açık harf sayısı
GECMIS_UST_SINIR = 100            # harf başına saklanan en fazla deneme
TUR_GECMISI = 60                  # saklanan son tur istatistiği
HARF_TUR_GECMISI = 30             # harf başına saklanan son tur hızı
TEST_GECMISI = 50
GERCEK_KELIME_OLASILIGI = 0.7
SATIR_KELIME = 8
SATIR_KARAKTER = 60
TABAN_AGIRLIK = 0.15              # ustalaşmış harfler de ara sıra gelsin
YENI_HARF_AGIRLIGI = 1.0          # en son açılan harfe ek ağırlık
FLAS_SURESI = 0.35                # yanlış tuşun kırmızı yanma süresi (sn)
BILGI_SURESI = 6.0                # geçici bilgi mesajlarının süresi (sn)
EN_UZUN_ARA = 5.0                 # bundan uzun duraklamalar hız/süreye sayılmaz (sn)
DOGRULUK_SERISI_ESIGI = 97.0      # doğruluk serisine sayılan en düşük satır doğruluğu
MIN_GENISLIK, MIN_YUKSEKLIK = 72, 22

SESLILER = frozenset("aeıioöuü")
HARFLER = frozenset(SIRA)

# ---------------------------------------------------------------------------
# Arayüz metinleri
# ---------------------------------------------------------------------------

METINLER = {
    "tr": {
        "sol": "Sol", "sag": "Sağ",
        "parmak_adlari": {"serce": "serçe", "yuzuk": "yüzük", "orta": "orta",
                          "isaret": "işaret", "basparmak": "başparmak"},
        "parmak_kisa": {"serce": "serçe", "yuzuk": "yüzük", "orta": "orta",
                        "isaret": "işaret", "basparmak": "baş"},
        "parmak_ek": "parmak", "basparmak": "başparmak", "Basparmak": "Başparmak",
        "bosluk": "boşluk",
        "yanlis": "Yanlış: '{bas}' bastın → {hedef}",
        "hedef_harf": "'{c}' için {parmak}",
        "hedef_bosluk": "boşluk için başparmak",
        "caps": " (Caps Lock?)",
        "yeni_harf": "Yeni harf açıldı: {h} · {parmak}",
        "yeni_rozet": "Yeni rozet: {ad} · +{xp} XP",
        "seviye_atladi": "Seviye {n}!",
        "hazir": "Yeni harf için {n}/{m} harf hazır",
        "tebrik": "Tebrikler! {m} harfin hepsi ustalaştı.",
        "tum_acik": "Tüm harfler açık · ustalaşan {n}/{m}",
        "siradaki_tus": "Sıradaki tuş",
        "shift_ile": "Shift: {parmak}",
        "yok": "—",
        # özet (keybr tarzı)
        "e_metrikler": "Metrikler", "e_harfler": "Harfler", "e_guncel": "Güncel harf",
        "e_dogruluk": "Doğruluk", "e_gunluk": "Günlük hedef",
        "m_hiz": "Hız", "m_dogruluk": "Doğruluk", "m_puan": "Puan", "dbk": "DBK",
        "son_hiz": "Son hız", "en_iyi": "En iyi", "ogrenme": "Öğrenme hızı",
        "tur_basina": "DBK/tur", "veri_yok": "henüz veri yok",
        "seri_yok": "Doğruluk serisi yok.",
        "seri_var": "{n} satır üst üste %{e:.0f} ve üzeri doğruluk",
        "gunluk_metin": "%{y} · {d}/{h} dakika", "gunluk_kapali": "Bugün {d} dakika pratik",
        "gun_serisi": "Seri: {n} gün", "seviye": "Seviye {n}", "xp": "{x} XP",
        # bölümler
        "k_ozet": "Özet", "k_yazi": "Yazı", "k_klavye": "Klavye", "k_isi": "Klavye · hata ısı haritası",
        "k_grafik": "Gelişim · son {n} tur", "k_guven": "Harf güveni",
        "son_n": "son {n} deneme",
        "grafik_bos": "Satır tamamladıkça hızınız ve doğruluğunuz burada çizilecek",
        "grafik_aciklama": "çubuk: DBK · renk: doğruluk",
        # modlar
        "modlar": {"ders": "Ders", "zayif": "Zayıf noktalar", "test": "Hız testi",
                   "metin": "Serbest metin"},
        "mod_aciklama": {"ders": "Harfler ustalaştıkça yenileri açılır",
                         "zayif": "En çok zorlandığınız harfler ve harf çiftleri",
                         "test": "{s} saniyelik hız testi (gerçek kelimeler)",
                         "metin": "Hazır bir metni ya da kendi metninizi yazın"},
        "test_hazir": "Başlamak için yazmaya başlayın", "test_kalan": "{s} sn",
        "test_sonuc": "Hız testi sonucu", "test_rekor": "Yeni rekor!",
        "test_tekrar": "Tekrar", "derse_don": "Derse dön",
        "metin_bitti": "Metin bitti, baştan başlıyor",
        "metin_sec": "Metin seçin", "metin_yok": "Metin bulunamadı",
        # düğmeler ve menüler
        "d_menu": "Menü", "d_ayarlar": "Ayarlar", "d_istatistik": "İstatistik",
        "d_yardim": "Yardım", "d_tam": "Tam ekran", "d_satir": "Yeni satır",
        "menu_baslik": "Duraklatıldı", "menu_devam": "Devam et", "menu_mod": "Alıştırma modu",
        "menu_istatistik": "İstatistikler", "menu_ayarlar": "Ayarlar", "menu_yardim": "Yardım",
        "menu_satir": "Yeni satır", "menu_tam": "Tam ekran aç/kapat", "menu_cikis": "Kaydet ve çık",
        "menu_ipucu": "↑↓ seç · Enter onayla · Esc kapat",
        "cikis_baslik": "Çıkılsın mı?", "cikis_metin": "İlerlemeniz kaydedilecek.",
        "evet": "Evet, çık", "hayir": "Vazgeç",
        "cikis_ipucu": "E / Ctrl-C: çık · H / Esc: vazgeç",
        "evet_tusu": "eE", "hayir_tusu": "hH",
        "ayar_baslik": "Ayarlar",
        "ayar_ipucu": "↑↓ seç · ←→ değiştir · Enter kaydet · Esc vazgeç",
        "kaydet": "Kaydet", "vazgec": "Vazgeç", "kapat": "Kapat",
        "ayar_kaydedildi": "Ayarlar kaydedildi.",
        "uyumsuz": "{duzen} düzeninde şu harfler yok: {eksik}",
        "kucuk1": "Terminal çok küçük", "kucuk2": "Şu an {w}×{h}, en az {mw}×{mh} gerekli",
        "kucuk3": "Pencereyi büyütün · Esc: menü",
        "yuzde": "%{v}",
        "gosterge_bilgi": "Göstergeler: parmaklarınızı ana sıraya koyup hizalayın",
        "yazi_boyutu_mesaj": "Yazı boyutu: {b}", "klavye_boyutu_mesaj": "Klavye: {b}",
        "rgb_baglandi": "Tuş aydınlatması: {ad}",
        "rgb_hata": "OpenRGB'ye bağlanılamadı ({adres}): {hata} · SDK sunucusu açık mı?",
        "gruplar": {"gorunum": "Görünüm", "klavye": "Klavye", "alistirma": "Alıştırma",
                    "hedefler": "Hedefler ve testler", "isik": "Klavye aydınlatması (OpenRGB)",
                    "pencere": "Pencere ve parmak göstergeleri", "etkilesim": "Etkileşim",
                    "veri": "Veri"},
        "eylem_adlari": {"ilerleme_sifirla": "İlerlemeyi sıfırla"},
        "eylem_deger": "Enter ›",
        "sifirla_baslik": "İlerleme sıfırlansın mı?",
        "sifirla_metin": [
            "Bu profil — {profil}:",
            "  açılan harfler, harf istatistikleri, turlar ve testler silinir.",
            "Tümü — bütün profiller, XP, seviye, rozetler ve günlük seri silinir.",
            "Önceki kayıt {yedek} dosyasına yedeklenir.",
        ],
        "sifirla_profil": "Bu profili sıfırla", "sifirla_tumu": "Tümünü sıfırla",
        "sifirla_ipucu": "←→ seç · Enter onayla · Esc vazgeç",
        "sifirlandi_profil": "{profil} ilerlemesi sıfırlandı.",
        "sifirlandi_tumu": "Tüm ilerleme sıfırlandı.",
        "ayar_adlari": {
            "tema": "Tema", "arayuz": "Arayüz dili", "yazi_boyutu": "Yazı boyutu",
            "klavye_boyutu": "Klavye boyutu", "klavye_gorunumu": "Klavye renkleri",
            "tus_stili": "Tuş stili", "tus_kenar": "Alt kenar yüksekliği",
            "sonraki_satir": "Sonraki satırı göster",
            "yazi_parmak": "Yazının altında parmaklar", "harf_paneli": "Harf güveni paneli",
            "klavye": "Klavye düzeni", "fiziksel": "Fiziksel düzen", "numpad": "Numpad",
            "dil": "Alıştırma dili", "ustalik_penceresi": "Ustalık penceresi",
            "ustalik_olcutu": "Ustalık ölçütü", "hedef_hiz": "Hedef hız",
            "buyuk_harf": "Büyük harfler", "noktalama": "Noktalama", "rakamlar": "Rakamlar",
            "gunluk_hedef_dk": "Günlük hedef", "test_suresi_sn": "Hız testi süresi",
            "acilis_boyutu": "Açılışta pencere", "gosterge": "Parmak göstergeleri",
            "gosterge_kaydirma_mm": "Gösterge kaydırma", "gosterge_olcek": "Gösterge aralığı",
            "tus_araligi_mm": "Tuş aralığı", "ekran_genisligi_mm": "Ekran genişliği",
            "fare": "Fare desteği", "rgb_isik": "Tuş aydınlatması", "rgb_zemin": "Diğer tuşlar",
            "rgb_parlaklik": "Parlaklık", "rgb_adres": "OpenRGB adresi",
        },
        "degerler": {
            True: "Açık", False: "Kapalı",
            "iso": "ISO (102 tuş)", "ansi": "ANSI (101 tuş)", "ansi102": "ANSI + 102. tuş",
            "parmak": "Parmak renkleri", "isi": "Hata ısı haritası",
            "kucuk": "Küçük", "normal": "Normal", "buyuk": "Büyük", "dev": "Dev",
            "otomatik_k": "Otomatik", "otomatik_uzun": "Otomatik · uzun", "gizli": "Gizli",
            "kompakt": "Kompakt", "orta": "Orta",
            "derinlik": "Derinlik (3B)", "duz": "Düz", "yuzen": "Yüzen",
            "dogruluk": "Doğruluk", "dogruluk_hiz": "Doğruluk + hız",
            "kapali": "Kapalı", "yeterli": "Yeterli boyuta getir", "kapla": "Ekranı kapla",
            "tam_ekran": "Tam ekran", "otomatik": "Tam ekrandayken", "her_zaman": "Her zaman",
            "dokunma": "Dokunma", "openrgb": "OpenRGB", "soluk": "Soluk beyaz",
        },
        "birim_deneme": "{v} deneme", "birim_mm": "{v} mm", "birim_otomatik": "Otomatik ({v} mm)",
        "birim_bilinmiyor": "Otomatik (bilinmiyor)", "birim_dbk": "{v} DBK",
        "birim_dk": "{v} dakika", "birim_sn": "{v} saniye", "birim_satir": "{v} satır",
        # istatistik ekranı
        "ist_baslik": "İstatistikler", "ist_genel": "Genel", "ist_gunler": "Son 14 gün",
        "ist_parmaklar": "Parmaklar", "ist_harfler": "Harfler", "ist_testler": "Hız testleri",
        "ist_rozetler": "Rozetler",
        "ist_seviye": "Seviye", "ist_sure": "Toplam pratik", "ist_satir": "Tamamlanan satır",
        "ist_vurus": "Doğru vuruş", "ist_en_iyi": "En iyi satır hızı",
        "ist_ortalama": "Son 10 satır", "ist_seri": "Günlük seri", "ist_en_uzun": "en uzun",
        "ist_yok": "Henüz yok",
        "saat_dk": "{s} sa {d} dk", "dk": "{d} dk", "gun": "{n} gün",
        "harf_baslik": "Harf: {h}", "harf_durum_usta": "Ustalaştı", "harf_durum_calis": "Çalışılıyor",
        "harf_durum_kilit": "Kilitli",
        "h_parmak": "Parmak", "h_dogruluk": "Doğruluk (son {n})", "h_deneme": "Deneme / hata",
        "h_hiz": "Ortalama hız", "h_son": "Son tur hızı", "h_en_iyi": "En iyi tur hızı",
        "h_durum": "Durum",
        # yardım
        "yardim_baslik": "Yardım",
        "yardim": [
            ("Yazma", ""), ("Harfleri yazın", "yanlış tuşta imleç bekler"),
            ("Tab", "yeni satır"), ("Esc", "menü"), ("Ctrl-C", "çıkış (onaylı)"),
            ("Kısayollar", ""), ("F1", "yardım"), ("F2", "ayarlar"), ("F3", "ısı haritası"),
            ("F4", "istatistikler"), ("F5 / F6", "yazıyı küçült / büyüt"),
            ("F7", "klavye boyutu"), ("F8", "alıştırma modu"), ("F11", "tam ekran"),
            ("Fare", ""), ("Tıklama", "düğmeler, menüler, ayar okları, harf çipleri"),
            ("Tekerlek", "listelerde gezinme"), ("✕ / dışarı tıklama", "pencereyi kapatır"),
            ("Dosyalar", ""), ("Ayarlar", "{ayar}"), ("Temalar", "{tema}"),
            ("Metinler", "{metin}"), ("İlerleme", "{kayit}"),
        ],
    },
    "en": {
        "sol": "Left", "sag": "Right",
        "parmak_adlari": {"serce": "pinky", "yuzuk": "ring", "orta": "middle",
                          "isaret": "index", "basparmak": "thumb"},
        "parmak_kisa": {"serce": "pinky", "yuzuk": "ring", "orta": "middle",
                        "isaret": "index", "basparmak": "thumb"},
        "parmak_ek": "finger", "basparmak": "thumb", "Basparmak": "Thumb",
        "bosluk": "space",
        "yanlis": "Wrong: you pressed '{bas}' → {hedef}",
        "hedef_harf": "'{c}' with {parmak}",
        "hedef_bosluk": "space with thumb",
        "caps": " (Caps Lock?)",
        "yeni_harf": "New letter unlocked: {h} · {parmak}",
        "yeni_rozet": "New badge: {ad} · +{xp} XP",
        "seviye_atladi": "Level {n}!",
        "hazir": "{n}/{m} letters ready for the next one",
        "tebrik": "Congratulations! All {m} letters mastered.",
        "tum_acik": "All letters unlocked · mastered {n}/{m}",
        "siradaki_tus": "Next key",
        "shift_ile": "Shift: {parmak}",
        "yok": "—",
        "e_metrikler": "Metrics", "e_harfler": "All keys", "e_guncel": "Current key",
        "e_dogruluk": "Accuracy", "e_gunluk": "Daily goal",
        "m_hiz": "Speed", "m_dogruluk": "Accuracy", "m_puan": "Score", "dbk": "WPM",
        "son_hiz": "Last speed", "en_iyi": "Top speed", "ogrenme": "Learning rate",
        "tur_basina": "WPM/line", "veri_yok": "no data yet",
        "seri_yok": "No accuracy streaks.",
        "seri_var": "{n} lines in a row at {e:.0f}% or better",
        "gunluk_metin": "{y}% · {d}/{h} minutes", "gunluk_kapali": "{d} minutes today",
        "gun_serisi": "Streak: {n} days", "seviye": "Level {n}", "xp": "{x} XP",
        "k_ozet": "Overview", "k_yazi": "Typing", "k_klavye": "Keyboard",
        "k_isi": "Keyboard · error heat map", "k_grafik": "Progress · last {n} lines",
        "k_guven": "Letter confidence", "son_n": "last {n} tries",
        "grafik_bos": "Complete lines to see your speed and accuracy here",
        "grafik_aciklama": "bar: WPM · color: accuracy",
        "modlar": {"ders": "Lesson", "zayif": "Weak spots", "test": "Speed test",
                   "metin": "Free text"},
        "mod_aciklama": {"ders": "New letters unlock as you master them",
                         "zayif": "The letters and pairs you struggle with most",
                         "test": "{s} second speed test (real words)",
                         "metin": "Type a built-in text or your own"},
        "test_hazir": "Start typing to begin", "test_kalan": "{s} s",
        "test_sonuc": "Speed test result", "test_rekor": "New record!",
        "test_tekrar": "Again", "derse_don": "Back to lesson",
        "metin_bitti": "Text finished, starting over",
        "metin_sec": "Choose a text", "metin_yok": "No texts found",
        "d_menu": "Menu", "d_ayarlar": "Settings", "d_istatistik": "Stats",
        "d_yardim": "Help", "d_tam": "Full screen", "d_satir": "New line",
        "menu_baslik": "Paused", "menu_devam": "Resume", "menu_mod": "Practice mode",
        "menu_istatistik": "Statistics", "menu_ayarlar": "Settings", "menu_yardim": "Help",
        "menu_satir": "New line", "menu_tam": "Toggle full screen", "menu_cikis": "Save and quit",
        "menu_ipucu": "↑↓ select · Enter confirm · Esc close",
        "cikis_baslik": "Quit?", "cikis_metin": "Your progress will be saved.",
        "evet": "Yes, quit", "hayir": "Cancel",
        "cikis_ipucu": "Y / Ctrl-C: quit · N / Esc: cancel",
        "evet_tusu": "yY", "hayir_tusu": "nN",
        "ayar_baslik": "Settings",
        "ayar_ipucu": "↑↓ select · ←→ change · Enter save · Esc cancel",
        "kaydet": "Save", "vazgec": "Cancel", "kapat": "Close",
        "ayar_kaydedildi": "Settings saved.",
        "uyumsuz": "The {duzen} layout lacks these letters: {eksik}",
        "kucuk1": "Terminal too small", "kucuk2": "Now {w}×{h}, at least {mw}×{mh} needed",
        "kucuk3": "Enlarge the window · Esc: menu",
        "yuzde": "{v}%",
        "gosterge_bilgi": "Indicators: rest your fingers on the home row and align",
        "yazi_boyutu_mesaj": "Text size: {b}", "klavye_boyutu_mesaj": "Keyboard: {b}",
        "rgb_baglandi": "Key lighting: {ad}",
        "rgb_hata": "Could not connect to OpenRGB ({adres}): {hata} · is the SDK server on?",
        "gruplar": {"gorunum": "Appearance", "klavye": "Keyboard", "alistirma": "Practice",
                    "hedefler": "Goals and tests", "isik": "Keyboard lighting (OpenRGB)",
                    "pencere": "Window and finger indicators", "etkilesim": "Interaction",
                    "veri": "Data"},
        "eylem_adlari": {"ilerleme_sifirla": "Reset progress"},
        "eylem_deger": "Enter ›",
        "sifirla_baslik": "Reset progress?",
        "sifirla_metin": [
            "This profile — {profil}:",
            "  unlocked letters, letter statistics, rounds and tests are deleted.",
            "All — every profile, XP, level, badges and the daily streak are deleted.",
            "The previous record is backed up to {yedek}.",
        ],
        "sifirla_profil": "Reset this profile", "sifirla_tumu": "Reset all",
        "sifirla_ipucu": "←→ select · Enter confirm · Esc cancel",
        "sifirlandi_profil": "{profil} progress reset.",
        "sifirlandi_tumu": "All progress reset.",
        "ayar_adlari": {
            "tema": "Theme", "arayuz": "Interface language", "yazi_boyutu": "Text size",
            "klavye_boyutu": "Keyboard size", "klavye_gorunumu": "Keyboard colors",
            "tus_stili": "Key style", "tus_kenar": "Key edge height",
            "sonraki_satir": "Show next line",
            "yazi_parmak": "Fingers under the text", "harf_paneli": "Letter confidence panel",
            "klavye": "Keyboard layout", "fiziksel": "Physical layout", "numpad": "Numpad",
            "dil": "Practice language", "ustalik_penceresi": "Mastery window",
            "ustalik_olcutu": "Mastery criterion", "hedef_hiz": "Target speed",
            "buyuk_harf": "Capital letters", "noktalama": "Punctuation", "rakamlar": "Numbers",
            "gunluk_hedef_dk": "Daily goal", "test_suresi_sn": "Speed test length",
            "acilis_boyutu": "Window at start", "gosterge": "Finger indicators",
            "gosterge_kaydirma_mm": "Indicator offset", "gosterge_olcek": "Indicator spacing",
            "tus_araligi_mm": "Key pitch", "ekran_genisligi_mm": "Screen width",
            "fare": "Mouse support", "rgb_isik": "Key lighting", "rgb_zemin": "Other keys",
            "rgb_parlaklik": "Brightness", "rgb_adres": "OpenRGB address",
        },
        "degerler": {
            True: "On", False: "Off",
            "iso": "ISO (102 keys)", "ansi": "ANSI (101 keys)", "ansi102": "ANSI + 102nd key",
            "parmak": "Finger colors", "isi": "Error heat map",
            "kucuk": "Small", "normal": "Normal", "buyuk": "Large", "dev": "Huge",
            "otomatik_k": "Automatic", "otomatik_uzun": "Automatic · tall", "gizli": "Hidden",
            "kompakt": "Compact", "orta": "Medium",
            "derinlik": "Depth (3D)", "duz": "Flat", "yuzen": "Floating",
            "dogruluk": "Accuracy", "dogruluk_hiz": "Accuracy + speed",
            "kapali": "Off", "yeterli": "Enlarge to fit", "kapla": "Maximize",
            "tam_ekran": "Full screen", "otomatik": "In full screen", "her_zaman": "Always",
            "dokunma": "Leave as is", "openrgb": "OpenRGB", "soluk": "Dim white",
        },
        "birim_deneme": "{v} tries", "birim_mm": "{v} mm", "birim_otomatik": "Automatic ({v} mm)",
        "birim_bilinmiyor": "Automatic (unknown)", "birim_dbk": "{v} WPM",
        "birim_dk": "{v} minutes", "birim_sn": "{v} seconds", "birim_satir": "{v} rows",
        "ist_baslik": "Statistics", "ist_genel": "General", "ist_gunler": "Last 14 days",
        "ist_parmaklar": "Fingers", "ist_harfler": "Letters", "ist_testler": "Speed tests",
        "ist_rozetler": "Badges",
        "ist_seviye": "Level", "ist_sure": "Total practice", "ist_satir": "Lines completed",
        "ist_vurus": "Correct keystrokes", "ist_en_iyi": "Best line speed",
        "ist_ortalama": "Last 10 lines", "ist_seri": "Daily streak", "ist_en_uzun": "longest",
        "ist_yok": "None yet",
        "saat_dk": "{s} h {d} min", "dk": "{d} min", "gun": "{n} days",
        "harf_baslik": "Key: {h}", "harf_durum_usta": "Mastered", "harf_durum_calis": "Learning",
        "harf_durum_kilit": "Locked",
        "h_parmak": "Finger", "h_dogruluk": "Accuracy (last {n})", "h_deneme": "Tries / errors",
        "h_hiz": "Average speed", "h_son": "Last line speed", "h_en_iyi": "Best line speed",
        "h_durum": "Status",
        "yardim_baslik": "Help",
        "yardim": [
            ("Typing", ""), ("Type the letters", "the cursor waits on a wrong key"),
            ("Tab", "new line"), ("Esc", "menu"), ("Ctrl-C", "quit (with confirmation)"),
            ("Shortcuts", ""), ("F1", "help"), ("F2", "settings"), ("F3", "heat map"),
            ("F4", "statistics"), ("F5 / F6", "smaller / larger text"),
            ("F7", "keyboard size"), ("F8", "practice mode"), ("F11", "full screen"),
            ("Mouse", ""), ("Click", "buttons, menus, setting arrows, key chips"),
            ("Wheel", "scroll lists"), ("✕ / click outside", "closes the window"),
            ("Files", ""), ("Settings", "{ayar}"), ("Themes", "{tema}"),
            ("Texts", "{metin}"), ("Progress", "{kayit}"),
        ],
    },
}

# Harf dışı tuşların etiketleri: sığan ilk seçenek kullanılır
TUS_ETIKETLERI = {
    "geri": {"tr": ["← Geri sil", "← Sil", "←"], "en": ["← Backspace", "← Bksp", "←"]},
    "tab": {"*": ["Tab ↹", "Tab", "↹"]},
    "caps": {"*": ["Caps Lock", "Caps", "⇪"]},
    "enter": {"*": ["Enter ↵", "Enter", "↵"]},
    "shift_s": {"*": ["⇧ Shift", "Shift", "⇧"]},
    "shift_r": {"*": ["⇧ Shift", "Shift", "⇧"]},
    "ctrl_s": {"*": ["Ctrl"]}, "ctrl_r": {"*": ["Ctrl"]},
    "meta_s": {"*": ["Meta", "◆"]}, "meta_r": {"*": ["Meta", "◆"]},
    "alt_s": {"*": ["Alt"]}, "altgr": {"*": ["Alt Gr", "AltGr", "AGr"]},
    "menu": {"tr": ["Menü", "≡"], "en": ["Menu", "≡"]},
    " ": {"tr": ["boşluk"], "en": ["space"]},
    "num": {"*": ["Num", "NL"]},
    "enter_n": {"*": ["Enter", "↵"]},
}

# Hazır metinler (serbest metin modu); kullanıcı metinleri METIN_DIZINI/*.txt
HAZIR_METINLER = {
    "tr": [
        ("Deniz kenarında",
         "Sabah erkenden deniz kenarına indik. Hava serindi ve dalgalar kıyıya usulca "
         "vuruyordu. Martılar tepemizde dönerken balıkçılar ağlarını topluyordu. Küçük bir "
         "çay bahçesine oturup simit ile çay istedik. Güneş yükseldikçe sahil kalabalıklaştı, "
         "çocuklar kumdan kaleler yaptı. Öğleye doğru eve dönerken hepimiz yorgun ama "
         "mutluyduk."),
        ("On parmak üzerine",
         "On parmak yazmak, klavyeye bakmadan hızlı ve doğru yazabilmek demektir. Her parmak "
         "kendi tuşlarından sorumludur ve eller ana sırada dinlenir. İlk günlerde yavaş "
         "ilerlemek normaldir; önemli olan hatasız yazmaktır. Hız, doğruluğun ardından "
         "kendiliğinden gelir. Düzenli ve kısa çalışmalar, uzun ama seyrek çalışmalardan "
         "daha etkilidir."),
    ],
    "en": [
        ("The garden",
         "Every morning she walked through the small garden behind the house. The roses were "
         "bright, the grass was wet, and the birds sang in the old apple tree. She liked to "
         "sit on the wooden bench and read a few pages before work. Some days were quiet; "
         "other days were loud with wind and rain. Still, the garden always felt like home."),
        ("On touch typing",
         "Touch typing means writing without looking at the keyboard. Each finger has its own "
         "keys, and your hands rest on the home row. At first you will be slow, and that is "
         "fine. Accuracy comes first; speed follows. Short daily practice works better than "
         "long sessions once a week."),
    ],
}

_KELIME_METNI = """
ak al aş as ad ada dal fal kal sal şal kaş laf saf kas aşk sakla kasa kafa
dalak salla kalas şaka kalk sakal aksak kalfa falaka adak lala kalsa aksa
dalsa akla dalda kasada salak salsa
el ele eş eşek kese kedi deli dile dilek delik ilk iki ile eski kişi şekil
keşif ses sel dil kil leke iş işle ilke ekle sil dik kek fil file fide kafes
aile eşik şelale kale lale sade ideal esas dakika defa sefa feda
ne en sen nine neden kendi keskin denk nane anne ana kanal kan din şans sinek
lise kasnak dinle kin sakin insan
kar kara ara arka ders dere er erken fark fikir kral renk resim kira keder
karar kardeş sirke fener fare kere rende nerede nereye irade serin nar
kısa akıl sıra kış ılık ışık kılıç kırk kadın ıslak kırık fındık kalın karın
sınır sınıf dışarı arı salı sarı
et at ata tat tatil taş tek tel test tren tane tarla atlas ateş kat kent dert
sert ters saat sat satış kitap tatlı titiz
jel jest ajan proje bej garaj masaj mesaj plaj enerji müjde jilet jeton rejim
jüri pijama ajanda teknoloji bagaj baraj viraj şarj
ve bir bu da de için gibi çok daha ama var yok ben biz siz onlar her şey
zaman gün yıl ev göz baş yol su ekmek kapı masa kalem okul çocuk baba arkadaş
adam kız oğlan dünya hayat şehir köy deniz dağ orman ağaç çiçek kuş köpek balık
elma armut üzüm kiraz çilek limon portakal domates biber soğan patates peynir
zeytin çay kahve süt şeker tuz yemek sabah akşam gece öğle hafta ay
bugün yarın dün şimdi sonra önce yeni büyük küçük uzun güzel iyi kötü sıcak
soğuk hızlı yavaş kolay zor doğru yanlış açık kapalı beyaz siyah kırmızı mavi
yeşil mor turuncu pembe gri üç dört beş altı yedi sekiz dokuz on yirmi otuz
elli altmış yetmiş seksen doksan yüz bin milyon
gel git yap bak oku yaz çiz söyle konuş sor ver koş yürü otur uyu ye iç sev bil
gör duy düşün anla başla bitir aç kapa tut bırak getir götür bul kaybet kazan
öde dön çık gir in bekle çalış oyna gül ağla sus dur taşı seç kes ol düş uç
kulak burun ağız diş saç kol bacak ayak parmak kalp söz harf kelime cümle
sayfa defter soru cevap sınav öğretmen öğrenci bilgi bilim sanat müzik şarkı
oyun film haber gazete dergi mektup telefon bilgisayar klavye ekran program
dosya klasör sistem güç pil lamba hava toprak kum yağmur rüzgar bulut güneş
yıldız gök çizgi nokta köşe kenar orta sağ sol üst alt ön dış yan yakın uzak
aşağı yukarı ileri geri para fiyat pazar dükkan fırın lokanta otel hastane
doktor ilaç sağlık hasta spor top takım maç gol koşu bisiklet araba otobüs uçak
gemi tekne köprü sokak cadde bahçe park oda mutfak banyo yatak dolap sandalye
pencere duvar tavan halı perde kapak kutu çanta cep düğme iğne iplik kumaş
gömlek etek ceket pantolon ayakkabı çorap şapka eldiven gözlük yüzük kolye
anahtar kilit kağıt makas bıçak çatal kaşık tabak bardak fincan tencere tava
ocak buz dondurma pasta bal reçel yağ un pirinç bulgur mercimek fasulye nohut
tavuk yumurta salata çorba pilav börek simit lokum baklava meyve sebze havuç
marul ıspanak kabak patlıcan karpuz kavun muz şeftali erik incir ceviz badem
zil sevgi sevinç mutluluk umut korku öfke merak heyecan rüya akıl ruh can
beden yaş boy kilo ölçü metre gram litre derece yüzde sayı hesap toplam çarpı
eşit doğa çevre hayvan bitki tohum kök yaprak dikkat özen sabır hız adım yön
kuzey güney doğu batı ülke millet halk devlet kanun hak adalet özgürlük barış
savaş ordu asker polis hakim avukat işçi şirket fabrika ürün alış borç kredi
banka faiz vergi maaş emek çaba başarı hata sorun çözüm yardım destek istek
seçim plan amaç hedef sonuç çünkü belki hemen artık hep hiç bazen sadece
yalnız birlikte beraber kadar göre karşı sanki tamam evet hayır lütfen merhaba
selam hoşça kaç nasıl hangi kim kimse biri hepsi bazı çoğu az fazla yarım
tam bütün tüm son inek koyun keçi tavşan aslan kaplan ayı kurt tilki sincap
yılan karınca kelebek böcek örümcek kartal güvercin serçe karga baykuş horoz
ördek kaz hindi yunus
zeki ince genç yaşlı zengin fakir temiz kirli boş dolu ucuz pahalı sessiz rahat
mutlu üzgün yorgun tok hafif ağır derin geniş dar yüksek alçak acı ekşi tuzlu
kuru yumuşak çiğ bağ eğitim değer değil eğlence düğün yoğurt boğaz sözlük
ilkbahar sonbahar şubat mart nisan mayıs haziran temmuz ağustos eylül ekim
kasım aralık pazartesi çarşamba perşembe cuma cumartesi
"""
_KELIME_METNI_EN = """
a as ask asks add adds all alas fall falls flask salad sad dad lad lads fad ads
lass glass flag half safe sale deal lake leaf feel keep seek desk kid kids
skill skills dish fish flash slash dash hall shall ask asked
the be to of and in that have it for not on with he you do at this but his by
from they we say her she or an will my one would there their what so up out if
about who get which go me when make can like time no just him know take people
into year your good some could them see other than then now look only come its
over think also back after use two how our work first well way even new want
because any these give day most us is was are were has had did said may should
very through long where much before great little own old right big high
different small large next early young important few public bad same able last
late hard real best better sure free true whole low full clear open short hot
cold fast slow word home hand house world life school water room mother father
night money book eye food ship bird tree city river car door table chair friend
family letter number name idea story music game paper light line side head face
voice fire sea land air sun moon star rain snow wind stone milk bread egg salt
sugar tea coffee apple lemon cat dog horse cow lion bed wall window floor street
road park shop bank farm field garden forest hill island black white red green
blue yellow brown gray pink orange type key keys finger fingers speed practice
lesson train learn teach read write spell sound quick fox jumps lazy
morning evening today tomorrow week month summer winter spring autumn
question answer problem reason result change point place group part case
system program question power area company country state family student
teacher child children woman man men women boy girl baby body heart mind
walk run jump sit stand sleep eat drink open close start stop begin end
help show tell call try need feel leave put mean keep let seem turn move play
live believe bring happen stand lose pay meet include continue set learn lead
understand watch follow create speak allow add spend grow offer remember love
consider appear buy wait serve die send expect build stay fall cut reach kill
remain suggest raise pass sell require report decide pull
"""


def _tekil(sozcukler):
    gorulen = set()
    return [k for k in sozcukler if not (k in gorulen or gorulen.add(k))]


KELIMELER = _tekil(_KELIME_METNI.split())
KELIMELER_EN = _tekil(_KELIME_METNI_EN.split())

DILLER = {
    "tr": {"ad": {"tr": "Türkçe", "en": "Turkish"},
           "harfler": "abcçdefgğhıijklmnoöprsştuüvyz", "sesliler": "aeıioöuü",
           "kelimeler": KELIMELER, "sira": {"tr-q": SIRA},
           "noktalama": ".,.,;:!?'-"},
    "en": {"ad": {"tr": "İngilizce", "en": "English"},
           "harfler": "abcdefghijklmnopqrstuvwxyz", "sesliler": "aeiou",
           "kelimeler": KELIMELER_EN, "sira": {},
           "noktalama": ".,.,;:!?'\"-"},
}


def tr_kucuk(s):
    """Türkçe kurallarıyla küçük harf (I → ı, İ → i)."""
    return s.replace("I", "ı").replace("İ", "i").lower()


def kucuk_harf(s, dil):
    return tr_kucuk(s) if dil == "tr" else s.lower()


def buyuk_harf(s, dil):
    """Dile göre büyük harf (Türkçede i → İ, ı → I)."""
    if dil == "tr":
        s = s.replace("i", "İ").replace("ı", "I")
    return s.upper()


# ---------------------------------------------------------------------------
# Piksel yazı tipi (büyük yazı boyutları için): 5×8, satır 7 alt uzantı
# ---------------------------------------------------------------------------

_YAZI_TIPI = """
a ..... ..... .###. ....# .#### #...# .#### .....
b #.... #.... #.##. ##..# #...# #...# ####. .....
c ..... ..... .###. #.... #.... #...# .###. .....
ç ..... ..... .###. #.... #...# .###. ..#.. .##..
d ....# ....# .##.# #..## #...# #...# .#### .....
e ..... ..... .###. #...# ##### #.... .###. .....
f ..##. .#..# .#... ###.. .#... .#... .#... .....
g ..... ..... .#### #...# #...# .#### ....# .###.
ğ #...# .###. .#### #...# .#### ....# .###. .....
h #.... #.... #.##. ##..# #...# #...# #...# .....
ı ..... ..... .##.. ..#.. ..#.. ..#.. .###. .....
i ..#.. ..... .##.. ..#.. ..#.. ..#.. .###. .....
j ...#. ..... ..##. ...#. ...#. #..#. .##.. .....
k #.... #.... #..#. #.#.. ##... #.#.. #..#. .....
l .##.. ..#.. ..#.. ..#.. ..#.. ..#.. .###. .....
m ..... ..... ##.#. #.#.# #.#.# #...# #...# .....
n ..... ..... #.##. ##..# #...# #...# #...# .....
o ..... ..... .###. #...# #...# #...# .###. .....
ö ..... .#.#. ..... .###. #...# #...# .###. .....
p ..... ..... ####. #...# ####. #.... #.... .....
q ..... ..... .##.# #..## .#### ....# ....# .....
r ..... ..... #.##. ##..# #.... #.... #.... .....
s ..... ..... .###. #.... .###. ....# ####. .....
ş ..... ..... .###. #.... .###. ....# ####. ..#..
t .#... .#... ###.. .#... .#... .#..# ..##. .....
u ..... ..... #...# #...# #...# #..## .##.# .....
ü ..... .#.#. ..... #...# #...# #..## .##.# .....
v ..... ..... #...# #...# #...# .#.#. ..#.. .....
w ..... ..... #...# #...# #.#.# #.#.# .#.#. .....
x ..... ..... #...# .#.#. ..#.. .#.#. #...# .....
y ..... ..... #...# #...# .#### ....# .###. .....
z ..... ..... ##### ...#. ..#.. .#... ##### .....
A .###. #...# #...# ##### #...# #...# #...# .....
B ####. #...# #...# ####. #...# #...# ####. .....
C .###. #...# #.... #.... #.... #...# .###. .....
Ç .###. #...# #.... #...# .###. ..#.. .##.. .....
D ###.. #..#. #...# #...# #...# #..#. ###.. .....
E ##### #.... #.... ####. #.... #.... ##### .....
F ##### #.... #.... ####. #.... #.... #.... .....
G .###. #...# #.... #.### #...# #...# .#### .....
Ğ .###. ..... .#### #.... #..## #...# .###. .....
H #...# #...# #...# ##### #...# #...# #...# .....
I .###. ..#.. ..#.. ..#.. ..#.. ..#.. .###. .....
İ ..#.. ..... .###. ..#.. ..#.. ..#.. .###. .....
J ..### ...#. ...#. ...#. ...#. #..#. .##.. .....
K #...# #..#. #.#.. ##... #.#.. #..#. #...# .....
L #.... #.... #.... #.... #.... #.... ##### .....
M #...# ##.## #.#.# #.#.# #...# #...# #...# .....
N #...# #...# ##..# #.#.# #..## #...# #...# .....
O .###. #...# #...# #...# #...# #...# .###. .....
Ö .#.#. ..... .###. #...# #...# #...# .###. .....
P ####. #...# #...# ####. #.... #.... #.... .....
Q .###. #...# #...# #...# #.#.# #..#. .##.# .....
R ####. #...# #...# ####. #.#.. #..#. #...# .....
S .#### #.... #.... .###. ....# ....# ####. .....
Ş .#### #.... .###. ....# ####. ..#.. .##.. .....
T ##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#.. .....
U #...# #...# #...# #...# #...# #...# .###. .....
Ü .#.#. ..... #...# #...# #...# #...# .###. .....
V #...# #...# #...# #...# #...# .#.#. ..#.. .....
W #...# #...# #...# #.#.# #.#.# #.#.# .#.#. .....
X #...# #...# .#.#. ..#.. .#.#. #...# #...# .....
Y #...# #...# .#.#. ..#.. ..#.. ..#.. ..#.. .....
Z ##### ....# ...#. ..#.. .#... #.... ##### .....
0 .###. #...# #..## #.#.# ##..# #...# .###. .....
1 ..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###. .....
2 .###. #...# ....# ...#. ..#.. .#... ##### .....
3 ##### ...#. ..#.. ...#. ....# #...# .###. .....
4 ...#. ..##. .#.#. #..#. ##### ...#. ...#. .....
5 ##### #.... ####. ....# ....# #...# .###. .....
6 ..##. .#... #.... ####. #...# #...# .###. .....
7 ##### ....# ...#. ..#.. .#... .#... .#... .....
8 .###. #...# #...# .###. #...# #...# .###. .....
9 .###. #...# #...# .#### ....# ...#. .##.. .....
. ..... ..... ..... ..... ..... .##.. .##.. .....
, ..... ..... ..... ..... .##.. .##.. ..#.. .#...
; ..... .##.. .##.. ..... .##.. .##.. ..#.. .#...
: ..... .##.. .##.. ..... .##.. .##.. ..... .....
! ..#.. ..#.. ..#.. ..#.. ..#.. ..... ..#.. .....
? .###. #...# ....# ...#. ..#.. ..... ..#.. .....
' ..#.. ..#.. .#... ..... ..... ..... ..... .....
" .#.#. .#.#. .#.#. ..... ..... ..... ..... .....
- ..... ..... ..... ##### ..... ..... ..... .....
( ...#. ..#.. .#... .#... .#... ..#.. ...#. .....
) .#... ..#.. ...#. ...#. ...#. ..#.. .#... .....
/ ..... ....# ...#. ..#.. .#... #.... ..... .....
* ..... ..#.. #.#.# .###. #.#.# ..#.. ..... .....
+ ..... ..#.. ..#.. ##### ..#.. ..#.. ..... .....
= ..... ..... ##### ..... ##### ..... ..... .....
_ ..... ..... ..... ..... ..... ..... ##### .....
< ...#. ..#.. .#... #.... .#... ..#.. ...#. .....
> .#... ..#.. ...#. ....# ...#. ..#.. .#... .....
é ...#. ..#.. .###. #...# ##### #.... .###. .....
bosluk ..... ..... ..... ..... ..#.. ..... ..... .....
bilinmeyen ##### #...# #...# #...# #...# #...# ##### .....
"""


def _yazi_tipi_coz(metin):
    tip = {}
    for satir in metin.strip().splitlines():
        ad, *satirlar = satir.split()
        c = {"bosluk": " ", "bilinmeyen": None}.get(ad, ad)
        tip[c] = tuple(tuple(ch == "#" for ch in r) for r in satirlar)
    return tip


YAZI_TIPI = _yazi_tipi_coz(_YAZI_TIPI)
GLIF_G, GLIF_Y = 5, 8


def glif(c):
    return YAZI_TIPI.get(c) or YAZI_TIPI[None]


def glif_hucreleri(c, olcek=1):
    """Glifi terminal hücrelerine çevirir: [satır metni, ...].

    olcek 1: yarım bloklarla 5 sütun × 4 satır; olcek 2: tam bloklarla 10 × 8.
    """
    p = glif(c)
    if olcek == 1:
        satirlar = []
        for r in range(0, GLIF_Y, 2):
            satir = ""
            for x in range(GLIF_G):
                ust, alt = p[r][x], p[r + 1][x]
                satir += "█" if ust and alt else ("▀" if ust else ("▄" if alt else " "))
            satirlar.append(satir)
        return satirlar
    return ["".join("██" if piksel else "  " for piksel in p[r]) for r in range(GLIF_Y)]


# ---------------------------------------------------------------------------
# Klavye düzenleri
# ---------------------------------------------------------------------------

# Her düzen: sayı sırası (13), üst sıra (12), orta sıra (11), ek1 (ISO'da orta
# sıranın sonundaki, ANSI'de üst sıranın sonundaki tuş), alt sıra (10), ek2
# (ISO'da ve 102 tuşlu ANSI'de sol Shift'in yanındaki tuş). "shift": Shift ile
# üretilen karakter → tuşun kendi karakteri.
DUZENLER = {
    "tr-q": {"ad": {"tr": "Türkçe Q", "en": "Turkish Q"},
             "sayilar": '"1234567890*-', "ust": "qwertyuıopğü", "orta": "asdfghjklşi",
             "ek1": ",", "alt": "zxcvbnmöç.", "ek2": "<", "ondalik": ",", "dil": "tr",
             "shift": dict(zip("é!'^+%&/()=?_;:>", '"1234567890*-,.<'))},
    "tr-f": {"ad": {"tr": "Türkçe F", "en": "Turkish F"},
             "sayilar": "+1234567890/-", "ust": "fgğıodrnhpqw", "orta": "uieaütkmlyş",
             "ek1": "x", "alt": "jövcçzsb.,", "ek2": "<", "ondalik": ",", "dil": "tr",
             "shift": dict(zip("*!\"^$%&'()=?_:;>", "+1234567890/-.,<"))},
    "us": {"ad": {"tr": "İngilizce (ABD)", "en": "English (US)"},
           "sayilar": "`1234567890-=", "ust": "qwertyuiop[]", "orta": "asdfghjkl;'",
           "ek1": "\\", "alt": "zxcvbnm,./", "ek2": "\\", "ondalik": ".", "dil": "en",
           "shift": dict(zip("~!@#$%^&*()_+{}:\"|<>?", "`1234567890-=[];'\\,./"))},
}
FIZIKSEL_DUZENLER = ["iso", "ansi", "ansi102"]


def _s(t):
    return ("sol", t)


def _g(t):
    return ("sag", t)


BASPARMAK = ("", "basparmak")
PARMAK_SAYI = [_s("serce"), _s("serce"), _s("yuzuk"), _s("orta"), _s("isaret"), _s("isaret"),
               _g("isaret"), _g("isaret"), _g("orta"), _g("yuzuk"), _g("serce"), _g("serce"),
               _g("serce")]
PARMAK_UST = [_s("serce"), _s("yuzuk"), _s("orta"), _s("isaret"), _s("isaret"),
              _g("isaret"), _g("isaret"), _g("orta"), _g("yuzuk"), _g("serce"), _g("serce"),
              _g("serce")]
PARMAK_ORTA = PARMAK_UST[:11]
PARMAK_ALT = PARMAK_UST[:10]
PARMAK_TURLERI = ["serce", "yuzuk", "orta", "isaret", "basparmak"]
TUM_PARMAKLAR = [_s("serce"), _s("yuzuk"), _s("orta"), _s("isaret"), BASPARMAK,
                 _g("isaret"), _g("orta"), _g("yuzuk"), _g("serce")]
ANA_SIRA_INDEKSLERI = (0, 1, 2, 3, 6, 7, 8, 9)   # sol serçe..işaret, sağ işaret..serçe
NUMPAD_X = 15.5                                   # ana bloktan yarım tuş ara


class Tus(collections.namedtuple("Tus", "ad karakter parmak satir x g yuk numpad")):
    """Klavyedeki bir tuş; x ve g (genişlik) tuş birimi, satir/yuk sıra cinsinden."""

    @property
    def merkez(self):
        return self.x + self.g / 2


class Duzen:
    """Bir klavye düzeninin fiziksel yerleşimi ve parmak haritası."""

    def __init__(self, kimlik="tr-q", fiziksel="iso", numpad=False):
        v = DUZENLER[kimlik]
        self.kimlik = kimlik
        self.fiziksel = fiziksel
        self.iso = fiziksel == "iso"
        self.ek2_var = fiziksel in ("iso", "ansi102")
        self.numpad = numpad
        self.dil = v["dil"]
        self.orta = v["orta"]
        self.shift_haritasi = v["shift"]
        self.tuslar = []
        t = self._ekle
        # 0: sayı sırası
        x = 0
        for c, p in zip(v["sayilar"], PARMAK_SAYI):
            x = t(c, p, 0, x, 1)
        t("geri", _g("serce"), 0, x, 2)
        # 1: üst sıra
        x = t("tab", _s("serce"), 1, 0, 1.5)
        for c, p in zip(v["ust"], PARMAK_UST):
            x = t(c, p, 1, x, 1)
        t("enter" if self.iso else v["ek1"], _g("serce"), 1, x, 1.5)
        # 2: orta (ana) sıra
        x = t("caps", _s("serce"), 2, 0, 1.75)
        for c, p in zip(v["orta"], PARMAK_ORTA):
            x = t(c, p, 2, x, 1)
        if self.iso:
            x = t(v["ek1"], _g("serce"), 2, x, 1)
            t("enter", _g("serce"), 2, x, 1.25)
        else:
            t("enter", _g("serce"), 2, x, 2.25)
        # 3: alt sıra
        x = t("shift_s", _s("serce"), 3, 0, 1.25 if self.ek2_var else 2.25)
        if self.ek2_var:
            x = t(v["ek2"], _s("serce"), 3, x, 1)
        for c, p in zip(v["alt"], PARMAK_ALT):
            x = t(c, p, 3, x, 1)
        t("shift_r", _g("serce"), 3, x, 2.75)
        # 4: boşluk sırası
        x = 0
        for ad, p, g in (("ctrl_s", _s("serce"), 1.25), ("meta_s", None, 1.25),
                         ("alt_s", BASPARMAK, 1.25), (" ", BASPARMAK, 6.25),
                         ("altgr", BASPARMAK, 1.25), ("meta_r", None, 1.25),
                         ("menu", None, 1.25), ("ctrl_r", _g("serce"), 1.25)):
            x = t(ad, p, 4, x, g)
        if numpad:
            n, i, o, y4 = _g("isaret"), _g("orta"), _g("yuzuk"), _g("serce")
            X = NUMPAD_X
            for sira, tuslar in enumerate((
                    [("num", n), ("/", i), ("*", o), ("-", y4)],
                    [("7", n), ("8", i), ("9", o)], [("4", n), ("5", i), ("6", o)],
                    [("1", n), ("2", i), ("3", o)])):
                for k, (ad, p) in enumerate(tuslar):
                    t(ad, p, sira, X + k, 1, numpad=True)
            t("+", y4, 1, X + 3, 1, yuk=2, numpad=True)
            t("enter_n", y4, 3, X + 3, 1, yuk=2, numpad=True)
            t("0", n, 4, X, 2, numpad=True)
            t(v["ondalik"], o, 4, X + 2, 1, numpad=True)
        self.parmak_haritasi = {}
        for k in self.tuslar:
            if k.karakter and not k.numpad:
                self.parmak_haritasi.setdefault(k.karakter, k.parmak)
        self.karakterler = frozenset(self.parmak_haritasi)
        self.ana_tuslar = [self.orta[i] for i in ANA_SIRA_INDEKSLERI]
        self.cikintilar = (self.orta[3], self.orta[6])
        self.genislik_birim = (NUMPAD_X + 4) if numpad else 15
        self.shift_tersi = {}
        for yuksek, taban in self.shift_haritasi.items():
            if taban in self.karakterler:
                self.shift_tersi.setdefault(taban, yuksek)

    def _ekle(self, ad, parmak, satir, x, g, yuk=1, numpad=False):
        karakter = ad if len(ad) == 1 else None
        self.tuslar.append(Tus(ad, karakter, parmak, satir, x, g, yuk, numpad))
        return x + g

    def led_konumlari(self):
        """[(tuş, konum)] — konum, tuşun fiziksel yerinin ABD klavyesindeki adı
        (OpenRGB'nin "Key: ..." adlarıyla aynı). Karaktere değil konuma bakılır:
        Türkçe Q'daki "ş", ABD'deki ";" tuşudur."""
        siralar = [
            ["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "Backspace"],
            ["Tab", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "[", "]",
             "Enter" if self.iso else "\\ (ANSI)"],
            ["Caps Lock", "A", "S", "D", "F", "G", "H", "J", "K", "L", ";", "'"]
            + (["#", "Enter"] if self.iso else ["Enter"]),
            ["Left Shift"] + (["\\ (ISO)"] if self.ek2_var else [])
            + ["Z", "X", "C", "V", "B", "N", "M", ",", ".", "/", "Right Shift"],
            ["Left Control", "Left Windows", "Left Alt", "Space", "Right Alt", "Right Windows",
             "Menu", "Right Control"],
        ]
        numpad = {"num": "Num Lock", "enter_n": "Number Pad Enter"}
        sayac = [0] * 5
        sonuc = []
        for k in self.tuslar:
            if k.numpad:
                sonuc.append((k, numpad.get(k.ad, f"Number Pad {k.ad}")))
            else:
                sonuc.append((k, siralar[k.satir][sayac[k.satir]]))
                sayac[k.satir] += 1
        return sonuc

    def tus(self, karakter):
        """Karakterin ana bloktaki tuşu (yoksa None)."""
        for k in self.tuslar:
            if k.karakter == karakter and not k.numpad:
                return k
        return None

    def tus_adi(self, ad):
        for k in self.tuslar:
            if k.ad == ad:
                return k
        return None

    def cozumle(self, c):
        """Karakteri yazmak için (taban karakter, Shift gerekli mi); yazılamıyorsa None."""
        if c in self.karakterler:
            return c, False
        kucuk = kucuk_harf(c, self.dil)
        if kucuk != c and kucuk in self.karakterler:
            return kucuk, True
        if c in self.shift_haritasi and self.shift_haritasi[c] in self.karakterler:
            return self.shift_haritasi[c], True
        return None

    def yazilabilir_mi(self, c):
        return c == " " or self.cozumle(c) is not None

    def parmak(self, c):
        """Karakterin tabanındaki tuşun parmağı (Shift'li karakterler için de)."""
        cozum = self.cozumle(c) if c != " " else (" ", False)
        return self.parmak_haritasi.get(cozum[0]) if cozum else None

    def shift_tusu(self, c):
        """Karakter Shift istiyorsa karşı eldeki Shift tuşunun adı, yoksa None."""
        cozum = self.cozumle(c)
        if not cozum or not cozum[1]:
            return None
        parmak = self.parmak_haritasi.get(cozum[0])
        return "shift_r" if parmak and parmak[0] == "sol" else "shift_s"

    def boyut(self, u, hk, ek=1):
        """(genişlik, yükseklik) — u: tuş birimi sütun, hk: tuş gövdesi satırı,
        ek: sıralar arasındaki (alt kenar + boşluk) satırı."""
        return round(self.genislik_birim * u) - 1, 5 * (hk + ek)

    def tus_kutulari(self, kx, ky, u, hk, ek=1):
        """[(tuş, x0, y0, x1, y1)] — gövde sütunları [x0, x1), satırları [y0, y1);
        alt kenar y1'den başlayan ek satırdadır."""
        liste = []
        for k in self.tuslar:
            x0 = kx + round(k.x * u)
            x1 = kx + round((k.x + k.g) * u) - 1
            y0 = ky + k.satir * (hk + ek)
            y1 = y0 + k.yuk * (hk + ek) - ek
            liste.append((k, x0, y0, x1, y1))
        return liste

    def harf_satirlari(self):
        """Sade düzen için yalnızca harf sıraları ve kaymaları."""
        v = DUZENLER[self.kimlik]
        if self.iso:
            return [v["ust"], v["orta"] + v["ek1"], v["ek2"] + v["alt"]], [2, 3, 1]
        if self.ek2_var:
            return [v["ust"] + v["ek1"], v["orta"], v["ek2"] + v["alt"]], [2, 3, 1]
        return [v["ust"] + v["ek1"], v["orta"], v["alt"]], [1, 2, 4]


class UyumsuzDuzen(ValueError):
    pass


def mufredat(dil, duzen):
    """Dil + düzen için harf açılma sırası: ana sıra harfleri, sonra sıklık."""
    d = DILLER[dil]
    if duzen.kimlik in d["sira"]:
        return d["sira"][duzen.kimlik]
    harfler = set(d["harfler"])
    eksik = sorted(harfler - duzen.karakterler)
    if eksik:
        raise UyumsuzDuzen("".join(eksik))
    ana = [c for c in (duzen.orta[i] for i in (3, 6, 2, 7, 1, 8, 0, 9)) if c in harfler]
    siklik = collections.Counter(c for k in d["kelimeler"] for c in k)
    kalan = sorted(harfler - set(ana), key=lambda c: (-siklik[c], c))
    return "".join(ana + kalan)


# ---------------------------------------------------------------------------
# Temalar
# ---------------------------------------------------------------------------

TEMA_ALANLARI = ["zemin", "yuzey", "yazi", "soluk", "cizgi", "baslik", "vurgu", "vurgu_yazi",
                 "dogru", "hata", "hata_yazi", "uyari", "tus_yazi", "ust_zemin", "ust_yazi",
                 "golge"]
# isteğe bağlı: "tus_notr" (renk; yoksa hesaplanır), "tus_karisim" (0–1, tuş dolgusunda
# parmak renginin payı)

YERLESIK_TEMALAR = {
    "gece": {
        "ad": "Gece",
        "zemin": "#0f1117", "yuzey": "#171b24", "yazi": "#c9ced6", "soluk": "#5c6370",
        "cizgi": "#3b4252", "baslik": "#e5e9f0", "vurgu": "#e5c07b", "vurgu_yazi": "#0f1117",
        "dogru": "#98c379", "hata": "#e06c75", "hata_yazi": "#0f1117", "uyari": "#d19a66",
        "tus_yazi": "#0f1117", "ust_zemin": "#1b1f27", "ust_yazi": "#c9ced6", "golge": "#07080b",
        "parmak": {"serce": "#c678dd", "yuzuk": "#61afef", "orta": "#56b6c2",
                   "isaret": "#98c379", "basparmak": "#abb2bf"},
        "tus_karisim": 0.6,
    },
    "siyah": {
        "ad": "Siyah", "miras": "gece",
        "zemin": "#000000", "yuzey": "#1c1c1c", "yazi": "#d0d0d0", "soluk": "#6c6c6c",
        "cizgi": "#4e4e4e", "baslik": "#ffffff", "vurgu": "#ffd75f", "vurgu_yazi": "#000000",
        "dogru": "#87d787", "hata": "#ff5f5f", "hata_yazi": "#000000", "uyari": "#ffaf5f",
        "tus_yazi": "#000000", "ust_zemin": "#1c1c1c", "ust_yazi": "#d0d0d0", "golge": "#121212",
        "parmak": {"serce": "#d787d7", "yuzuk": "#87afff", "orta": "#5fd7d7",
                   "isaret": "#87d787", "basparmak": "#bcbcbc"},
    },
    "gunduz": {
        "ad": "Gündüz", "miras": "gece",
        "zemin": "#f5f5f5", "yuzey": "#ffffff", "yazi": "#383a42", "soluk": "#9da0a6",
        "cizgi": "#d0d0d4", "baslik": "#1f2328", "vurgu": "#f0b400", "vurgu_yazi": "#1f2328",
        "dogru": "#2f9e44", "hata": "#d6336c", "hata_yazi": "#ffffff", "uyari": "#e8590c",
        "tus_yazi": "#ffffff", "ust_zemin": "#e4e4e7", "ust_yazi": "#383a42", "golge": "#d0d0d4",
        "parmak": {"serce": "#ae3ec9", "yuzuk": "#4263eb", "orta": "#1098ad",
                   "isaret": "#37b24d", "basparmak": "#868e96"},
        "tus_karisim": 0.35,
    },
    "toprak": {
        "ad": "Toprak", "miras": "gece",
        "zemin": "#1d2021", "yuzey": "#282828", "yazi": "#ebdbb2", "soluk": "#7c6f64",
        "cizgi": "#504945", "baslik": "#fbf1c7", "vurgu": "#fabd2f", "vurgu_yazi": "#1d2021",
        "dogru": "#b8bb26", "hata": "#fb4934", "hata_yazi": "#1d2021", "uyari": "#fe8019",
        "tus_yazi": "#1d2021", "ust_zemin": "#282828", "ust_yazi": "#ebdbb2", "golge": "#111111",
        "parmak": {"serce": "#d3869b", "yuzuk": "#83a598", "orta": "#8ec07c",
                   "isaret": "#b8bb26", "basparmak": "#a89984"},
        "tus_karisim": 0.75,
    },
    "kontrast": {
        "ad": "Yüksek karşıtlık", "miras": "gece",
        "zemin": "#000000", "yuzey": "#000000", "yazi": "#ffffff", "soluk": "#a8a8a8",
        "cizgi": "#808080", "baslik": "#ffffff", "vurgu": "#ffff00", "vurgu_yazi": "#000000",
        "dogru": "#00ff00", "hata": "#ff0000", "hata_yazi": "#ffffff", "uyari": "#ff8700",
        "tus_yazi": "#000000", "ust_zemin": "#303030", "ust_yazi": "#ffffff", "golge": None,
        "parmak": {"serce": "#ff5fff", "yuzuk": "#5f87ff", "orta": "#00ffff",
                   "isaret": "#00ff00", "basparmak": "#ffffff"},
        "tus_karisim": 0.75,
    },
    "terminal": {
        "ad": "Terminal renkleri", "miras": "gece",
        "zemin": None, "yuzey": None, "yazi": None, "soluk": 8, "cizgi": 8, "baslik": 15,
        "vurgu": 3, "vurgu_yazi": 0, "dogru": 2, "hata": 1, "hata_yazi": 15, "uyari": 3,
        "tus_yazi": 0, "ust_zemin": None, "ust_yazi": None, "golge": None,
        "parmak": {"serce": 5, "yuzuk": 4, "orta": 6, "isaret": 2, "basparmak": 7},
        "tus_karisim": 1.0, "tus_notr": 8,
    },
}

RENK_ADLARI = {"black": 0, "red": 1, "green": 2, "yellow": 3, "blue": 4, "magenta": 5,
               "cyan": 6, "white": 7, "bright-black": 8, "gray": 8, "grey": 8,
               "bright-red": 9, "bright-green": 10, "bright-yellow": 11, "bright-blue": 12,
               "bright-magenta": 13, "bright-cyan": 14, "bright-white": 15}
_TEMEL_RGB = [(0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0), (0, 0, 238), (205, 0, 205),
              (0, 205, 205), (229, 229, 229), (127, 127, 127), (255, 0, 0), (0, 255, 0),
              (255, 255, 0), (92, 92, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255)]
_KUP = [0, 95, 135, 175, 215, 255]


def xterm_rgb(i):
    if i < 16:
        return _TEMEL_RGB[i]
    if i < 232:
        i -= 16
        return _KUP[i // 36], _KUP[i // 6 % 6], _KUP[i % 6]
    g = 8 + (i - 232) * 10
    return g, g, g


def renk_coz(deger):
    """Tema rengi → ("rgb", (r, g, b)) | ("indeks", n) | ("yok",). Geçersizse ValueError."""
    if deger is None or (isinstance(deger, str) and deger.lower() in ("default", "yok", "none", "")):
        return ("yok",)
    if isinstance(deger, bool):
        raise ValueError(deger)
    if isinstance(deger, int):
        if 0 <= deger <= 255:
            return ("indeks", deger)
        raise ValueError(deger)
    if isinstance(deger, str):
        d = deger.strip().lower()
        if d in RENK_ADLARI:
            return ("indeks", RENK_ADLARI[d])
        m = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", d)
        if m:
            h = m.group(1)
            if len(h) == 3:
                h = "".join(c * 2 for c in h)
            return ("rgb", tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)))
    raise ValueError(deger)


def renk_rgb(deger):
    """Tema rengini RGB'ye çevirir; terminal rengi (null) için None."""
    tur = renk_coz(deger)
    if tur[0] == "yok":
        return None
    return xterm_rgb(tur[1]) if tur[0] == "indeks" else tur[1]


def karistir(a, b, oran):
    """a'dan oran, b'den (1 - oran) alan RGB karışımı."""
    return tuple(round(x * oran + y * (1 - oran)) for x, y in zip(a, b))


def parlaklik(rgb):
    return (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255


def _ycc(rgb):
    r, g, b = rgb
    y = 0.299 * r + 0.587 * g + 0.114 * b
    return y, b - y, r - y


@functools.lru_cache(maxsize=4096)
def en_yakin_renk(rgb, renk_sayisi):
    """RGB'yi terminalin paletindeki en yakın renk numarasına çevirir.

    Uzaklık parlaklık/renk tonu (YCbCr) uzayında, tona 4 kat ağırlıkla ölçülür:
    256 renkli paletin koyu, yumuşak tonları seyrek olduğundan düz RGB uzaklığı
    renkli tonları griye yuvarlar.
    """
    hedef = _ycc(tuple(rgb))
    aday = range(16, 256) if renk_sayisi >= 256 else range(min(renk_sayisi, 16))

    def uzaklik(i):
        c = _ycc(xterm_rgb(i))
        return (c[0] - hedef[0]) ** 2 + 4 * ((c[1] - hedef[1]) ** 2 + (c[2] - hedef[2]) ** 2)
    return min(aday, key=uzaklik)


def renk_numarasi(deger, renk_sayisi):
    tur = renk_coz(deger)
    if tur[0] == "yok":
        return -1
    if tur[0] == "indeks":
        n = tur[1]
        return n if n < renk_sayisi else en_yakin_renk(xterm_rgb(n), renk_sayisi)
    return en_yakin_renk(tur[1], renk_sayisi)


def _tema_birlestir(taban, ust):
    sonuc = dict(taban)
    sonuc["parmak"] = dict(taban.get("parmak", {}))
    for anahtar, deger in ust.items():
        if anahtar == "parmak" and isinstance(deger, dict):
            sonuc["parmak"].update(deger)
        elif not anahtar.startswith("_"):
            sonuc[anahtar] = deger
    return sonuc


def tema_dogrula(kimlik, tema):
    """Eksik alanları ve geçersiz renkleri listeler."""
    hatalar = []
    for alan in TEMA_ALANLARI:
        if alan not in tema:
            hatalar.append(f"{kimlik}: '{alan}' eksik")
            continue
        try:
            renk_coz(tema[alan])
        except ValueError:
            hatalar.append(f"{kimlik}: '{alan}' geçersiz renk {tema[alan]!r}")
    for p in PARMAK_TURLERI:
        try:
            renk_coz(tema.get("parmak", {}).get(p))
        except ValueError:
            hatalar.append(f"{kimlik}: 'parmak.{p}' geçersiz renk")
    if "tus_notr" in tema:
        try:
            renk_coz(tema["tus_notr"])
        except ValueError:
            hatalar.append(f"{kimlik}: 'tus_notr' geçersiz renk")
    oran = tema.get("tus_karisim", 0.6)
    if isinstance(oran, bool) or not isinstance(oran, (int, float)) or not 0 <= oran <= 1:
        hatalar.append(f"{kimlik}: 'tus_karisim' 0 ile 1 arasında olmalı")
    return hatalar


def temalari_yukle(dizin=TEMA_DIZINI):
    """{kimlik: tema} ve uyarı listesi. Kullanıcı temaları yerleşikleri geçersiz kılar."""
    ham = {k: dict(v) for k, v in YERLESIK_TEMALAR.items()}
    uyarilar = []
    try:
        dosyalar = sorted(f for f in os.listdir(dizin) if f.endswith(".json"))
    except OSError:
        dosyalar = []
    for dosya in dosyalar:
        kimlik = dosya[:-5]
        try:
            with open(os.path.join(dizin, dosya), encoding="utf-8") as f:
                veri = json.load(f)
            if not isinstance(veri, dict):
                raise ValueError("nesne değil")
            ham[kimlik] = veri
        except (OSError, ValueError) as hata:
            uyarilar.append(f"{dosya}: {hata}")

    temalar = {}

    def coz(kimlik, yol=()):
        if kimlik in temalar:
            return temalar[kimlik]
        v = ham[kimlik]
        miras = v.get("miras", "gece" if kimlik != "gece" else None)
        if miras and miras in ham and miras not in yol and miras != kimlik:
            taban = coz(miras, yol + (kimlik,))
        else:
            taban = YERLESIK_TEMALAR["gece"]
        tema = _tema_birlestir(taban, v)
        tema.setdefault("ad", kimlik)
        temalar[kimlik] = tema
        return tema

    for kimlik in ham:
        tema = coz(kimlik)
        hatalar = tema_dogrula(kimlik, tema)
        if hatalar:
            uyarilar.extend(hatalar)
            bozuk = {h.split("'")[1] for h in hatalar if "'" in h}
            temiz = {k: v for k, v in tema.items() if k not in bozuk}
            if any(b.startswith("parmak.") for b in bozuk):
                temiz["parmak"] = {p: r for p, r in tema["parmak"].items()
                                   if f"parmak.{p}" not in bozuk}
            temalar[kimlik] = _tema_birlestir(YERLESIK_TEMALAR["gece"], temiz)
    return temalar, uyarilar


ORNEK_TEMA = {
    "_aciklama": [
        "Bu dosyayı kopyalayıp adını değiştirin (ör. benim.json); tema kimliği dosya adıdır.",
        "'miras' ile bir temayı temel alın, yalnızca değiştirmek istediğiniz alanları yazın.",
        "Renkler: '#rrggbb', '#rgb', 0-255 arası xterm renk numarası, 'red' gibi ad ya da null.",
        "null = terminalin kendi rengi. Alanlar: " + ", ".join(TEMA_ALANLARI) + ", parmak.{"
        + ", ".join(PARMAK_TURLERI) + "}",
        "İsteğe bağlı: tus_notr (harf dışı tuşların dolgusu), tus_karisim (0-1: tuş "
        "dolgusunda parmak renginin payı; küçük değer daha sakin görünüm).",
    ],
    "ad": "Örnek tema",
    "miras": "gece",
    "vurgu": "#ff8fab",
    "tus_karisim": 0.35,
    "parmak": {"serce": "#b197fc", "isaret": "#8ce99a"},
}

# ---------------------------------------------------------------------------
# Ayarlar
# ---------------------------------------------------------------------------

VARSAYILAN_AYARLAR = {
    "tema": "siyah", "arayuz": "tr", "yazi_boyutu": "normal", "klavye_boyutu": "otomatik_k",
    "tus_stili": "derinlik", "tus_kenar": 4,
    "klavye_gorunumu": "parmak", "sonraki_satir": True, "yazi_parmak": True, "harf_paneli": True,
    "klavye": "tr-q", "fiziksel": "iso", "numpad": False,
    "dil": "tr", "ustalik_penceresi": PENCERE, "ustalik_olcutu": "dogruluk", "hedef_hiz": 35,
    "buyuk_harf": False, "noktalama": False, "rakamlar": False,
    "gunluk_hedef_dk": 30, "test_suresi_sn": 60,
    "acilis_boyutu": "yeterli", "gosterge": "otomatik", "gosterge_kaydirma_mm": 0,
    "gosterge_olcek": 100, "tus_araligi_mm": 19.0, "ekran_genisligi_mm": 0,
    "fare": True,
    "rgb_isik": "kapali", "rgb_zemin": "parmak", "rgb_parlaklik": 60, "rgb_adres": "127.0.0.1:6742",
}

YAZI_BOYUTLARI = ["kucuk", "normal", "buyuk", "dev"]
KLAVYE_BOYUTLARI = ["otomatik_k", "otomatik_uzun", "gizli", "kompakt", "orta", "buyuk"]
TUS_STILLERI = ["derinlik", "duz", "yuzen"]
TUS_KENARLARI = [1, 4, 8, 12, 16]

AYAR_KURALLARI = {
    "tema": ("tema",),
    "arayuz": ("secim", ["tr", "en"]),
    "yazi_boyutu": ("secim", YAZI_BOYUTLARI),
    "klavye_boyutu": ("secim", KLAVYE_BOYUTLARI),
    "tus_stili": ("secim", TUS_STILLERI),
    # sekizde bir satır; yalnızca üst blok karakterleriyle (▔ ▀ █) temiz çizilen değerler
    "tus_kenar": ("secim", TUS_KENARLARI),
    "klavye_gorunumu": ("secim", ["parmak", "isi"]),
    "sonraki_satir": ("bool",),
    "yazi_parmak": ("bool",),
    "harf_paneli": ("bool",),
    "klavye": ("secim", list(DUZENLER)),
    "fiziksel": ("secim", FIZIKSEL_DUZENLER),
    "numpad": ("bool",),
    "dil": ("secim", list(DILLER)),
    "ustalik_penceresi": ("sayi", 5, 50, 5),
    "ustalik_olcutu": ("secim", ["dogruluk", "dogruluk_hiz"]),
    "hedef_hiz": ("sayi", 10, 150, 5),
    "buyuk_harf": ("bool",),
    "noktalama": ("bool",),
    "rakamlar": ("bool",),
    "gunluk_hedef_dk": ("sayi", 0, 240, 5),
    "test_suresi_sn": ("sayi", 15, 300, 15),
    "acilis_boyutu": ("secim", ["dokunma", "yeterli", "kapla", "tam_ekran"]),
    "gosterge": ("secim", ["kapali", "otomatik", "her_zaman"]),
    "gosterge_kaydirma_mm": ("sayi", -150, 150, 1),
    "gosterge_olcek": ("sayi", 50, 150, 1),
    "tus_araligi_mm": ("ondalik", 14.0, 24.0, 0.1),
    "ekran_genisligi_mm": ("sayi", 0, 2000, 1),
    "fare": ("bool",),
    "rgb_isik": ("secim", ["kapali", "openrgb"]),
    "rgb_zemin": ("secim", ["kapali", "soluk", "parmak"]),
    "rgb_parlaklik": ("sayi", 10, 100, 10),
    "rgb_adres": ("metin", r"^[\w.\-\[\]:]+:\d{1,5}$"),      # yalnızca JSON'dan düzenlenir
}

AYAR_SAYFASI = [
    ("gorunum", ["tema", "arayuz", "yazi_boyutu", "klavye_boyutu", "tus_stili", "tus_kenar",
                 "klavye_gorunumu",
                 "sonraki_satir", "yazi_parmak", "harf_paneli"]),
    ("klavye", ["klavye", "fiziksel", "numpad"]),
    ("alistirma", ["dil", "ustalik_penceresi", "ustalik_olcutu", "hedef_hiz", "buyuk_harf",
                   "noktalama", "rakamlar"]),
    ("hedefler", ["gunluk_hedef_dk", "test_suresi_sn"]),
    ("pencere", ["acilis_boyutu", "gosterge", "gosterge_kaydirma_mm", "gosterge_olcek",
                 "tus_araligi_mm", "ekran_genisligi_mm"]),
    ("isik", ["rgb_isik", "rgb_zemin", "rgb_parlaklik", "rgb_adres"]),
    ("etkilesim", ["fare"]),
]
AYAR_EYLEMLERI = [("veri", ["ilerleme_sifirla"])]     # ayar değil, onaylı eylem satırları
CANLI_AYARLAR = {"tema", "arayuz", "yazi_boyutu", "klavye_boyutu", "tus_stili", "tus_kenar",
                 "klavye_gorunumu",
                 "sonraki_satir", "yazi_parmak", "harf_paneli", "fiziksel", "numpad", "gosterge",
                 "gosterge_kaydirma_mm", "gosterge_olcek", "tus_araligi_mm",
                 "ekran_genisligi_mm", "rgb_zemin", "rgb_parlaklik"}
SATIRI_YENILEYEN = {"buyuk_harf", "noktalama", "rakamlar"}


def ayar_dogrula(ham, temalar):
    """Dosyadan okunan ayarları doğrular: (ayarlar, uyarılar)."""
    ayarlar, uyarilar = dict(VARSAYILAN_AYARLAR), []
    ham = dict(ham or {})
    if ham.get("klavye_boyutu") == "otomatik":          # eski yazım
        ham["klavye_boyutu"] = "otomatik_k"
    for anahtar, deger in ham.items():
        if anahtar.startswith("_"):
            continue
        kural = AYAR_KURALLARI.get(anahtar)
        if kural is None:
            uyarilar.append(f"bilinmeyen ayar: {anahtar}")
            continue
        tur = kural[0]
        gecerli = (
            (tur == "tema" and deger in temalar)
            or (tur == "secim" and deger in kural[1])
            or (tur == "bool" and isinstance(deger, bool))
            or (tur == "metin" and isinstance(deger, str) and re.match(kural[1], deger))
            or (tur == "sayi" and isinstance(deger, int) and not isinstance(deger, bool)
                and kural[1] <= deger <= kural[2])
            or (tur == "ondalik" and isinstance(deger, (int, float))
                and not isinstance(deger, bool) and kural[1] <= deger <= kural[2]))
        if gecerli:
            ayarlar[anahtar] = float(deger) if tur == "ondalik" else deger
        else:
            uyarilar.append(f"geçersiz değer: {anahtar} = {deger!r}")
    return ayarlar, uyarilar


def ayar_degistir(ayarlar, anahtar, yon, temalar):
    """Bir ayarı bir adım ileri/geri çevirir (yon: ±1 ya da ±10)."""
    kural = AYAR_KURALLARI[anahtar]
    tur, deger = kural[0], ayarlar[anahtar]
    if tur in ("secim", "tema"):
        secenekler = list(temalar) if tur == "tema" else kural[1]
        i = secenekler.index(deger) if deger in secenekler else 0
        ayarlar[anahtar] = secenekler[(i + (1 if yon > 0 else -1)) % len(secenekler)]
    elif tur == "bool":
        ayarlar[anahtar] = not deger
    elif tur == "metin":
        return                                           # yalnızca ayar dosyasından
    else:
        alt, ust, adim = kural[1], kural[2], kural[3]
        yeni = deger + adim * yon
        yeni = round(yeni, 1) if tur == "ondalik" else int(yeni)
        ayarlar[anahtar] = min(ust, max(alt, yeni))


def ayarlari_yukle(yol=AYAR_DOSYASI, temalar=None):
    temalar = temalar or YERLESIK_TEMALAR
    try:
        with open(yol, encoding="utf-8") as f:
            ham = json.load(f)
        if not isinstance(ham, dict):
            raise ValueError("nesne değil")
    except FileNotFoundError:
        return dict(VARSAYILAN_AYARLAR), [], False
    except (OSError, ValueError) as hata:
        return dict(VARSAYILAN_AYARLAR), [f"ayarlar.json okunamadı: {hata}"], True
    ayarlar, uyarilar = ayar_dogrula(ham, temalar)
    return ayarlar, uyarilar, True


def json_yaz(yol, veri, girinti=2):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=girinti)
        f.write("\n")
    os.replace(gecici, yol)


def eski_dizinleri_tasi():
    """Önceki ad ("onparmak-tui") altındaki ayar ve ilerlemeyi yeni dizinlere kopyalar."""
    tasinan = []
    for eski, yeni in ((ESKI_AYAR_DIZINI, AYAR_DIZINI), (ESKI_VERI_DIZINI, VERI_DIZINI)):
        if os.path.isdir(eski) and not os.path.exists(yeni):
            shutil.copytree(eski, yeni)
            tasinan.append(yeni)
    return tasinan


def yapilandirma_hazirla():
    """İlk çalıştırmada ayar dosyasını, örnek temayı ve metin dizinini oluşturur."""
    if not os.path.exists(AYAR_DOSYASI):
        json_yaz(AYAR_DOSYASI, VARSAYILAN_AYARLAR)
    if not os.path.isdir(TEMA_DIZINI):
        os.makedirs(TEMA_DIZINI, exist_ok=True)
        json_yaz(os.path.join(TEMA_DIZINI, "ornek.json"), ORNEK_TEMA)
    if not os.path.isdir(METIN_DIZINI):
        os.makedirs(METIN_DIZINI, exist_ok=True)
        with open(os.path.join(METIN_DIZINI, "BENİOKU.txt"), "w", encoding="utf-8") as f:
            f.write("Bu dizine koyduğunuz .txt dosyaları 'Serbest metin' modunda seçilebilir.\n"
                    "Klavyede yazılamayan karakterler atlanır; tırnaklar ve tireler sadeleşir.\n")


# ---------------------------------------------------------------------------
# Rozetler, seviye ve günlük hedef
# ---------------------------------------------------------------------------

ROZET_XP = 50
ROZETLER = [
    # kimlik, tr adı, en adı, tr açıklama, en açıklama, koşul(durum)
    ("ilk_satir", "İlk adım", "First step", "İlk satırı tamamla", "Finish your first line",
     lambda d: d["satir"] >= 1),
    ("satir_100", "Yüz satır", "Hundred lines", "100 satır tamamla", "Finish 100 lines",
     lambda d: d["satir"] >= 100),
    ("satir_1000", "Bin satır", "Thousand lines", "1000 satır tamamla", "Finish 1000 lines",
     lambda d: d["satir"] >= 1000),
    ("ana_sira", "Ana sıra ustası", "Home row master", "İlk 8 harfte ustalaş",
     "Master the first 8 letters", lambda d: d["acik"] > BASLANGIC_ACIK),
    ("yari_yol", "Yarı yol", "Halfway", "Harflerin yarısını aç", "Unlock half of the letters",
     lambda d: d["acik"] * 2 >= d["toplam"]),
    ("tum_harfler", "Tüm harfler", "All letters", "Bütün harfleri aç", "Unlock every letter",
     lambda d: d["acik"] >= d["toplam"]),
    ("kusursuz", "Kusursuz", "Flawless", "Hatasız bir satır yaz", "Type a line without errors",
     lambda d: d["kusursuz"]),
    ("keskin", "Keskin nişancı", "Sharpshooter", "10 satır üst üste %97+ doğruluk",
     "10 lines in a row at 97%+ accuracy", lambda d: d["dogruluk_serisi"] >= 10),
    ("hiz_30", "Isınma", "Warming up", "Bir satırı 30 DBK ile yaz", "Type a line at 30 WPM",
     lambda d: d["en_iyi_dbk"] >= 30),
    ("hiz_50", "Hızlı parmaklar", "Quick fingers", "Bir satırı 50 DBK ile yaz",
     "Type a line at 50 WPM", lambda d: d["en_iyi_dbk"] >= 50),
    ("hiz_70", "Şimşek", "Lightning", "Bir satırı 70 DBK ile yaz", "Type a line at 70 WPM",
     lambda d: d["en_iyi_dbk"] >= 70),
    ("hedef", "Hedefe ulaştı", "Goal reached", "Günlük hedefi tamamla",
     "Reach your daily goal", lambda d: d["hedef_bugun"]),
    ("seri_3", "Üç gün", "Three days", "3 gün üst üste pratik", "Practice 3 days in a row",
     lambda d: d["seri"] >= 3),
    ("seri_7", "Bir hafta", "One week", "7 gün üst üste pratik", "Practice 7 days in a row",
     lambda d: d["seri"] >= 7),
    ("seri_30", "Bir ay", "One month", "30 gün üst üste pratik", "Practice 30 days in a row",
     lambda d: d["seri"] >= 30),
    ("maraton", "Maraton", "Marathon", "Bir günde 60 dakika pratik",
     "Practice 60 minutes in one day", lambda d: d["bugun_dk"] >= 60),
    ("test", "Sınavda", "Tested", "Bir hız testi tamamla", "Complete a speed test",
     lambda d: d["test_sayisi"] >= 1),
    ("test_50", "Test ustası", "Test ace", "Hız testinde 50 DBK", "Reach 50 WPM in a test",
     lambda d: d["en_iyi_test"] >= 50),
    ("gece_kusu", "Gece kuşu", "Night owl", "Gece yarısından sonra pratik",
     "Practice after midnight", lambda d: d["gece"]),
]


def seviye_hesapla(xp):
    """(seviye, bu seviyenin başladığı XP, sonraki seviyenin XP'si). Seviye n: 125·n·(n-1)."""
    n = 1
    while 125 * (n + 1) * n <= xp:
        n += 1
    return n, 125 * n * (n - 1), 125 * (n + 1) * n


def bugun_anahtari(zaman=None):
    return datetime.date.fromtimestamp(zaman or time.time()).isoformat()


def gun_serisi(gunluk, hedef_sn, bugun=None):
    """Hedefin tuttuğu ardışık gün sayısı (bugün henüz tutmadıysa dünden geriye sayar)."""
    esik = max(60, hedef_sn)
    gun = datetime.date.fromisoformat(bugun or bugun_anahtari())
    if gunluk.get(gun.isoformat(), 0) < esik:
        gun -= datetime.timedelta(days=1)
    seri = 0
    while gunluk.get(gun.isoformat(), 0) >= esik:
        seri += 1
        gun -= datetime.timedelta(days=1)
    return seri


def puan_hesapla(dbk, dogruluk, acik_sayisi):
    """keybr'daki gibi hız × doğruluk × zorluk; karşılaştırma içindir."""
    return round(dbk * (dogruluk / 100) ** 2 * (1 + acik_sayisi / 5) * 10)


# ---------------------------------------------------------------------------
# İlerleme ve ustalık (curses'tan bağımsız)
# ---------------------------------------------------------------------------


class Ilerleme:
    """Açık harf sayısı, harf başına deneme ve hız geçmişi, harf çiftleri, turlar."""

    def __init__(self, pencere=PENCERE, sira=SIRA, olcut="dogruluk", hedef_hiz=35):
        if pencere < 1:
            raise ValueError("pencere en az 1 olmalı")
        self.pencere = pencere
        self.sira = sira
        self.olcut = olcut
        self.hedef_hiz = hedef_hiz
        self.acik_sayisi = min(BASLANGIC_ACIK, len(sira))
        self.gecmis = {h: [] for h in sira}
        self.hizlar = {h: [] for h in sira}
        self.harf_turlari = {h: [] for h in sira}
        self.deneme = {h: 0 for h in sira}
        self.hata = {h: 0 for h in sira}
        self.ciftler = {}
        self.turlar = []
        self.testler = []

    @property
    def _sinir(self):
        return max(self.pencere, GECMIS_UST_SINIR)

    @property
    def acik_harfler(self):
        return self.sira[:self.acik_sayisi]

    @property
    def siradaki_harf(self):
        return self.sira[self.acik_sayisi] if self.acik_sayisi < len(self.sira) else None

    @property
    def guncel_harf(self):
        """keybr'daki "current key": en son açılan harf."""
        return self.sira[self.acik_sayisi - 1]

    def son_pencere(self, harf):
        return self.gecmis[harf][-self.pencere:]

    def dogru_sayisi(self, harf):
        return sum(self.son_pencere(harf))

    def dogruluk_orani(self, harf):
        return self.dogru_sayisi(harf) / self.pencere

    def hiz(self, harf):
        """Son penceredeki ortalama hız (DBK); yeterli veri yoksa None."""
        son = self.hizlar[harf][-self.pencere:]
        if len(son) < max(3, self.pencere // 2):
            return None
        return statistics.fmean(son)

    def guven(self, harf):
        """0–1 arası güven: doğruluk; ölçüt hız da içeriyorsa hız/hedef ile küçük olanı."""
        oran = self.dogruluk_orani(harf)
        if self.olcut == "dogruluk_hiz":
            hiz = self.hiz(harf)
            oran = min(oran, (hiz or 0) / self.hedef_hiz)
        return min(1.0, oran)

    def ustalasti_mi(self, harf):
        son = self.son_pencere(harf)
        if len(son) < self.pencere or not all(son):
            return False
        if self.olcut == "dogruluk_hiz":
            hiz = self.hiz(harf)
            return hiz is not None and hiz >= self.hedef_hiz
        return True

    def hazir_sayisi(self):
        return sum(self.ustalasti_mi(h) for h in self.acik_harfler)

    def tumu_ustalasti_mi(self):
        return all(self.ustalasti_mi(h) for h in self.acik_harfler)

    def deneme_kaydet(self, harf, dogru, hiz=None):
        if harf not in self.gecmis:
            return
        g = self.gecmis[harf]
        g.append(bool(dogru))
        del g[:-self._sinir]
        self.deneme[harf] += 1
        if not dogru:
            self.hata[harf] += 1
        if hiz is not None:
            h = self.hizlar[harf]
            h.append(round(hiz, 1))
            del h[:-self._sinir]

    def cift_kaydet(self, onceki, harf, dogru):
        if onceki not in self.gecmis or harf not in self.gecmis:
            return
        kayit = self.ciftler.setdefault(onceki + harf, [0, 0])
        kayit[0] += 1
        if not dogru:
            kayit[1] += 1

    def zayif_ciftler(self, n=5):
        """Hata oranı en yüksek harf çiftleri (yalnızca açık harflerle, en az 3 deneme)."""
        acik = set(self.acik_harfler)
        adaylar = [(h / d, c) for c, (d, h) in self.ciftler.items()
                   if d >= 3 and h and set(c) <= acik]
        return [c for _, c in sorted(adaylar, reverse=True)[:n]]

    def harf_tur_kaydet(self, harf, hiz):
        if harf in self.harf_turlari:
            liste = self.harf_turlari[harf]
            liste.append(round(hiz, 1))
            del liste[:-HARF_TUR_GECMISI]

    def ogrenme_hizi(self, harf, n=10):
        """Son n turdaki hız eğimi (DBK/tur); en az 3 tur yoksa None."""
        son = self.harf_turlari.get(harf, [])[-n:]
        if len(son) < 3:
            return None
        xs = range(len(son))
        ort_x, ort_y = statistics.fmean(xs), statistics.fmean(son)
        pay = sum((x - ort_x) * (y - ort_y) for x, y in zip(xs, son))
        payda = sum((x - ort_x) ** 2 for x in xs)
        return pay / payda if payda else 0.0

    def tur_kaydet(self, istatistik):
        self.turlar.append({k: round(v, 1) for k, v in istatistik.items()} | {"t": int(time.time())})
        del self.turlar[:-TUR_GECMISI]

    def test_kaydet(self, sonuc):
        self.testler.append(dict(sonuc, t=int(time.time())))
        del self.testler[:-TEST_GECMISI]

    def dogruluk_serisi(self, esik=DOGRULUK_SERISI_ESIGI):
        seri = 0
        for tur in reversed(self.turlar):
            if tur.get("dogruluk", 0) < esik:
                break
            seri += 1
        return seri

    def yeni_harf_dene(self):
        """Açık harflerin hepsi ustalaşmışsa sıradaki harfi açar ve döndürür."""
        if self.acik_sayisi < len(self.sira) and self.tumu_ustalasti_mi():
            self.acik_sayisi += 1
            return self.sira[self.acik_sayisi - 1]
        return None

    def sozluk(self):
        return {
            "acik_harf_sayisi": self.acik_sayisi,
            "harfler": {h: {"gecmis": [int(x) for x in self.gecmis[h]],
                            "hizlar": self.hizlar[h], "turlar": self.harf_turlari[h],
                            "deneme": self.deneme[h], "hata": self.hata[h]}
                        for h in self.sira},
            "ciftler": self.ciftler,
            "turlar": self.turlar,
            "testler": self.testler,
        }

    @classmethod
    def sozlukten(cls, veri, pencere=PENCERE, sira=SIRA, olcut="dogruluk", hedef_hiz=35):
        il = cls(pencere, sira, olcut, hedef_hiz)
        try:
            n = int(veri.get("acik_harf_sayisi", il.acik_sayisi))
        except (TypeError, ValueError):
            n = il.acik_sayisi
        il.acik_sayisi = min(len(sira), max(il.acik_sayisi, n))
        harfler = veri.get("harfler") or {}
        for h in sira:
            kayit = harfler.get(h) or {}
            try:
                g = [bool(x) for x in kayit.get("gecmis", [])][-il._sinir:]
                il.gecmis[h] = g
                il.hizlar[h] = [float(x) for x in kayit.get("hizlar", [])][-il._sinir:]
                il.harf_turlari[h] = [float(x) for x in kayit.get("turlar", [])][-HARF_TUR_GECMISI:]
                il.deneme[h] = int(kayit.get("deneme", len(g)))
                il.hata[h] = int(kayit.get("hata", g.count(False)))
            except (TypeError, ValueError, AttributeError):
                pass
        ciftler = veri.get("ciftler")
        if isinstance(ciftler, dict):
            il.ciftler = {c: [int(v[0]), int(v[1])] for c, v in ciftler.items()
                          if isinstance(v, list) and len(v) == 2}
        for alan in ("turlar", "testler"):
            liste = veri.get(alan)
            if isinstance(liste, list):
                setattr(il, alan, [t for t in liste if isinstance(t, dict)]
                        [-(TUR_GECMISI if alan == "turlar" else TEST_GECMISI):])
        return il


def profil_anahtari(dil, duzen_kimligi):
    return f"{dil}/{duzen_kimligi}"


def _yeni_genel():
    return {"xp": 0, "rozetler": {}, "gunluk": {}, "satir": 0, "vurus": 0, "saniye": 0.0,
            "en_uzun_seri": 0, "kusursuz": False, "gece": False}


class IlerlemeDeposu:
    """Tüm profillerin (dil/düzen) ilerlemesi ve genel oyun verisi tek dosyada."""

    def __init__(self, yol=KAYIT_DOSYASI):
        self.yol = yol
        self.uyari = None
        self.veri = {"surum": 3, "profiller": {}, "genel": _yeni_genel()}
        try:
            with open(yol, encoding="utf-8") as f:
                veri = json.load(f)
            if not isinstance(veri, dict):
                raise ValueError("beklenmeyen biçim")
        except FileNotFoundError:
            return
        except (OSError, ValueError) as hata:
            yedek = yol + ".bozuk"
            try:
                os.replace(yol, yedek)
            except OSError:
                yedek = None
            self.uyari = f"Kayıt okunamadı ({hata}); sıfırdan başlandı." + (
                f" Eski dosya: {yedek}" if yedek else "")
            return
        if "profiller" not in veri:                      # 1. sürüm: yalnızca Türkçe Q
            veri = {"profiller": {profil_anahtari("tr", "tr-q"): veri}}
        if not isinstance(veri.get("profiller"), dict):
            veri["profiller"] = {}
        genel = _yeni_genel()
        if isinstance(veri.get("genel"), dict):
            genel.update(veri["genel"])
        veri["genel"] = genel
        veri["surum"] = 3
        self.veri = veri

    @property
    def genel(self):
        return self.veri["genel"]

    def profil(self, anahtar, pencere, sira, olcut="dogruluk", hedef_hiz=35):
        ham = self.veri["profiller"].get(anahtar)
        if isinstance(ham, dict):
            return Ilerleme.sozlukten(ham, pencere, sira, olcut, hedef_hiz)
        return Ilerleme(pencere, sira, olcut, hedef_hiz)

    def kaydet(self, anahtar, ilerleme):
        self.veri["profiller"][anahtar] = ilerleme.sozluk()
        json_yaz(self.yol, self.veri, girinti=None)

    def sifirla(self, anahtar=None):
        """Bir profilin (anahtar) ya da tüm ilerlemenin kaydını siler; önceki hâli
        <kayıt>.yedek dosyasına yazılır."""
        json_yaz(self.yol + ".yedek", self.veri, girinti=None)
        if anahtar is None:
            self.veri = {"surum": 3, "profiller": {}, "genel": _yeni_genel()}
        else:
            self.veri["profiller"].pop(anahtar, None)
        json_yaz(self.yol, self.veri, girinti=None)

    def en_iyi(self, alan):
        """Tüm profillerdeki en iyi tur/test hızı."""
        en = 0.0
        for p in self.veri["profiller"].values():
            for t in p.get(alan, []) if isinstance(p, dict) else []:
                en = max(en, float(t.get("dbk", 0)))
        return en

    def test_sayisi(self):
        return sum(len(p.get("testler", [])) for p in self.veri["profiller"].values()
                   if isinstance(p, dict))



# ---------------------------------------------------------------------------
# Kelime üretimi (curses'tan bağımsız)
# ---------------------------------------------------------------------------


def yazilabilir_mi(kelime, acik):
    return set(kelime) <= set(acik)


def odak_agirliklari(ilerleme):
    """Açık her harf için odak ağırlığı: taban + zayıflık (+ en yeniye ek)."""
    acik = ilerleme.acik_harfler
    en_yeni = acik[-1]
    agirlik = {}
    for h in acik:
        zayiflik = 1 - ilerleme.dogru_sayisi(h) / ilerleme.pencere
        agirlik[h] = TABAN_AGIRLIK + zayiflik + (YENI_HARF_AGIRLIGI if h == en_yeni else 0)
    return agirlik


def zayif_agirliklari(ilerleme):
    """Zayıf noktalar modu: zayıflığın karesiyle ağırlık, hızı düşük harflere ek pay."""
    agirlik = {}
    for h in ilerleme.acik_harfler:
        dogruluk = ilerleme.dogruluk_orani(h) if ilerleme.gecmis[h] else 0.5
        hiz = ilerleme.hiz(h)
        yavaslik = max(0.0, 1 - hiz / ilerleme.hedef_hiz) if hiz else 0.3
        agirlik[h] = 0.05 + 3 * (1 - dogruluk) ** 2 + yavaslik
    return agirlik


def uydurma_kelime(odak, acik, rng, sesliler=SESLILER):
    """Açık harflerden, sesli-sessiz dönüşümlü, odak harfi içeren 3–6 harflik kelime."""
    sesli = [h for h in acik if h in sesliler]
    sessiz = [h for h in acik if h not in sesliler]
    uzunluk = rng.randint(3, 6)
    if not sesli or not sessiz:
        havuz = sesli or sessiz
        harfler = [rng.choice(havuz) for _ in range(uzunluk)]
        harfler[rng.randrange(uzunluk)] = odak
        return "".join(harfler)
    bas_sesli = rng.random() < 0.5
    siniflar = [(i % 2 == 0) == bas_sesli for i in range(uzunluk)]   # True = sesli
    harfler = [rng.choice(sesli if s else sessiz) for s in siniflar]
    yerler = [i for i, s in enumerate(siniflar) if s == (odak in sesliler)]
    harfler[rng.choice(yerler)] = odak
    return "".join(harfler)


def kelime_uret(odak, acik, yazilabilir, rng, onceki=None, sesliler=SESLILER,
                gercek_olasilik=GERCEK_KELIME_OLASILIGI):
    """Odak harfi içeren bir kelime: çoğunlukla gerçek, yoksa uydurma."""
    adaylar = [k for k in yazilabilir if odak in k and k != onceki]
    if adaylar and rng.random() < gercek_olasilik:
        return rng.choice(adaylar)
    kelime = uydurma_kelime(odak, acik, rng, sesliler)
    for _ in range(20):
        if kelime != onceki:
            break
        kelime = uydurma_kelime(odak, acik, rng, sesliler)
    return kelime


def cift_kelimesi(cift, acik, yazilabilir, rng, onceki=None, sesliler=SESLILER):
    """Harf çiftini içeren gerçek ya da uydurma kelime."""
    adaylar = [k for k in yazilabilir if cift in k and k != onceki]
    if adaylar and rng.random() < 0.7:
        return rng.choice(adaylar)
    harfler = list(uydurma_kelime(cift[0], acik, rng, sesliler))
    konum = rng.randrange(len(harfler) - 1)
    harfler[konum:konum + 2] = list(cift)
    return "".join(harfler)


def satir_uret(ilerleme, rng, max_karakter=SATIR_KARAKTER, max_kelime=SATIR_KELIME,
               onceki=None, kelimeler=KELIMELER, sesliler=SESLILER, agirlik=None, ciftler=(),
               gercek_olasilik=GERCEK_KELIME_OLASILIGI):
    acik = ilerleme.acik_harfler
    acik_kume = set(acik)
    yazilabilir = [k for k in kelimeler if set(k) <= acik_kume]
    agirlik = agirlik or odak_agirliklari(ilerleme)
    harfler, agirliklar = list(agirlik), list(agirlik.values())

    satir, uzunluk = [], 0
    for _ in range(max_kelime * 6):
        if len(satir) >= max_kelime or max_karakter - uzunluk < 4:
            break
        son = satir[-1] if satir else onceki
        if ciftler and rng.random() < 0.5:
            kelime = cift_kelimesi(rng.choice(ciftler), acik, yazilabilir, rng, son, sesliler)
        else:
            odak = rng.choices(harfler, agirliklar)[0]
            kelime = kelime_uret(odak, acik, yazilabilir, rng, son, sesliler, gercek_olasilik)
        ek = len(kelime) + (1 if satir else 0)
        if uzunluk + ek > max_karakter:
            if satir:
                continue            # sığmadı; daha kısa bir kelime dene
            kelime = kelime[:max_karakter]
            ek = len(kelime)
        satir.append(kelime)
        uzunluk += ek
    return " ".join(satir)


def susle(satir, rng, duzen, dil, buyuk=False, noktalama=False, rakam=False,
          max_karakter=SATIR_KARAKTER):
    """Satıra seçeneğe göre büyük harf, noktalama ve rakam ekler (yazılabilenlerle)."""
    if not (buyuk or noktalama or rakam):
        return satir
    isaretler = [c for c in DILLER[dil]["noktalama"] if c != "-" and duzen.yazilabilir_mi(c)]
    rakamlar = [c for c in "0123456789" if duzen.yazilabilir_mi(c)]
    sonuc, cumle_basi = [], True
    for kelime in satir.split():
        if rakam and rakamlar and rng.random() < 0.12:
            kelime = "".join(rng.choice(rakamlar) for _ in range(rng.randint(1, 4)))
        elif buyuk and (cumle_basi or rng.random() < 0.2):
            ilk = buyuk_harf(kelime[0], dil)
            if duzen.yazilabilir_mi(ilk):
                kelime = ilk + kelime[1:]
        cumle_basi = False
        if noktalama and isaretler and rng.random() < 0.25:
            isaret = rng.choice(isaretler)
            if isaret in "'\"":
                kelime = isaret + kelime + isaret
            else:
                kelime += isaret
                cumle_basi = isaret in ".!?"
        sonuc.append(kelime)
    while len(" ".join(sonuc)) > max_karakter and len(sonuc) > 1:
        sonuc.pop()
    return " ".join(sonuc)[:max_karakter]


METIN_DONUSUM = {"“": '"', "”": '"', "„": '"', "«": '"', "»": '"', "‘": "'", "’": "'",
                 "–": "-", "—": "-", "…": "...", "â": "a", "î": "i", "û": "u", "Â": "A",
                 "Î": "İ", "Û": "U", "\t": " ", "\n": " ", "\r": " "}


def metin_hazirla(metin, duzen):
    """Serbest metni klavyede yazılabilir kelimelere çevirir."""
    m = unicodedata.normalize("NFC", metin)
    m = "".join(METIN_DONUSUM.get(c, c) for c in m)
    return "".join(c for c in m if c == " " or duzen.yazilabilir_mi(c)).split()


def metin_satiri(kelimeler, bas, max_karakter):
    """Kelime listesinden bas'tan başlayan satır: (satır, yeni_baş, başa_sarıldı_mı)."""
    if not kelimeler:
        return "", 0, False
    sarildi = False
    if bas >= len(kelimeler):
        bas, sarildi = 0, True
    satir, i = [], bas
    while i < len(kelimeler):
        kelime = kelimeler[i][:max_karakter]
        if satir and len(" ".join(satir + [kelime])) > max_karakter:
            break
        satir.append(kelime)
        i += 1
    return " ".join(satir), i, sarildi


def metinleri_listele(dil, dizin=METIN_DIZINI):
    """[(ad, içerik)] — hazır metinler ve kullanıcının .txt dosyaları."""
    liste = list(HAZIR_METINLER.get(dil, []))
    try:
        dosyalar = sorted(f for f in os.listdir(dizin)
                          if f.endswith(".txt") and not f.upper().startswith(("BENİOKU", "README")))
    except OSError:
        dosyalar = []
    for dosya in dosyalar:
        try:
            with open(os.path.join(dizin, dosya), encoding="utf-8") as f:
                icerik = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        if icerik.strip():
            liste.append((dosya[:-4], icerik))
    return liste


def tur_istatistikleri(zamanlar, hatali_basis):
    """Doğru vuruş zamanlarından DBK, doğruluk ve tutarlılık (%)."""
    if len(zamanlar) < 2:
        return None
    sure = zamanlar[-1] - zamanlar[0]
    if sure <= 0:
        return None
    karakter = len(zamanlar)
    dbk = ((karakter - 1) / 5) / (sure / 60)
    dogruluk = 100 * karakter / (karakter + hatali_basis)
    araliklar = [b - a for a, b in zip(zamanlar, zamanlar[1:])]
    ortalama = statistics.fmean(araliklar)
    sapma = statistics.pstdev(araliklar)
    tutarlilik = max(0.0, 100 * (1 - sapma / ortalama)) if ortalama > 0 else 0.0
    return {"dbk": dbk, "dogruluk": dogruluk, "tutarlilik": tutarlilik}


# ---------------------------------------------------------------------------
# Çizgi motoru
# ---------------------------------------------------------------------------

_YUKARI, _ASAGI, _SOL, _SAG = 1, 2, 4, 8
_KUTU_KARAKTER = {
    _YUKARI | _ASAGI: "│", _SOL | _SAG: "─",
    _YUKARI: "│", _ASAGI: "│", _SOL: "─", _SAG: "─",
    _ASAGI | _SAG: "╭", _ASAGI | _SOL: "╮", _YUKARI | _SAG: "╰", _YUKARI | _SOL: "╯",
    _YUKARI | _ASAGI | _SAG: "├", _YUKARI | _ASAGI | _SOL: "┤",
    _SOL | _SAG | _ASAGI: "┬", _SOL | _SAG | _YUKARI: "┴",
    _YUKARI | _ASAGI | _SOL | _SAG: "┼",
}


class Cizim:
    """Birim kenarlardan çizgi çizimi; kesişimlerde doğru köşe/kavşak karakteri seçilir."""

    def __init__(self):
        self.yatay = set()        # (x, y): (x, y) → (x+1, y)
        self.dikey = set()        # (x, y): (x, y) → (x, y+1)

    def yatay_cizgi(self, x0, x1, y):
        self.yatay.update((x, y) for x in range(x0, x1))

    def dikey_cizgi(self, x, y0, y1):
        self.dikey.update((x, y) for y in range(y0, y1))

    def kutu(self, x0, y0, x1, y1):
        self.yatay_cizgi(x0, x1, y0)
        self.yatay_cizgi(x0, x1, y1)
        self.dikey_cizgi(x0, y0, y1)
        self.dikey_cizgi(x1, y0, y1)

    def yatay_sil(self, x0, x1, y):
        self.yatay.difference_update((x, y) for x in range(x0, x1))

    def karakterler(self):
        """{(x, y): karakter}"""
        yon = {}

        def ekle(nokta, bit):
            yon[nokta] = yon.get(nokta, 0) | bit

        for x, y in self.yatay:
            ekle((x, y), _SAG)
            ekle((x + 1, y), _SOL)
        for x, y in self.dikey:
            ekle((x, y), _ASAGI)
            ekle((x, y + 1), _YUKARI)
        return {n: _KUTU_KARAKTER[b] for n, b in yon.items()}


def kutu_cizgileri(kutular):
    """(x0, y0, x1, y1) köşeli kutuların kenarları: {(x, y): karakter}."""
    cizim = Cizim()
    for k in kutular:
        cizim.kutu(*k)
    return cizim.karakterler()


def kutu_kenari(x0, y0, x1, y1):
    """Kutunun kenarındaki hücreler."""
    return ([(x, y) for x in range(x0, x1 + 1) for y in (y0, y1)]
            + [(x, y) for y in range(y0 + 1, y1) for x in (x0, x1)])


def cizgi_cubugu(oran, genislik):
    """İnce çizgi stili çubuk: (dolu, boş) hücre sayıları."""
    dolu = round(min(1.0, max(0.0, oran)) * genislik)
    return dolu, genislik - dolu


def kivilcim(degerler, genislik):
    """Son değerlerden küçük bir çizgi grafiği."""
    degerler = degerler[-genislik:]
    if not degerler:
        return ""
    alt, ust = min(degerler), max(degerler)
    aralik = (ust - alt) or 1
    return "".join("▁▂▃▄▅▆▇█"[min(7, int((v - alt) / aralik * 7.999))] for v in degerler)


# ---------------------------------------------------------------------------
# Yerleşim motoru (curses'tan bağımsız): yuvarlak köşeli ayrı kartlar
# ---------------------------------------------------------------------------

YAZI_SATIRLARI = {"kucuk": 1, "normal": 1, "buyuk": 4, "dev": 8}
KLAVYE_HK = {"kompakt": 1, "orta": 2, "buyuk": 3}
GOSTERGE_Y = 3                    # parmak göstergesi şeridi
OZET_SECENEKLERI = (5, 3)         # özet kartının iç yüksekliği
PANEL_CUBUKLARI = (16, 12, 8, 6)
ANA_MIN_G = 70                    # ana sütunun en az iç genişliği
GRAFIK_MIN_Y, GRAFIK_MAX_Y = 5, 16
BIRIMLER = (8, 7, 6, 5, 4)        # tuş birimi (sütun)


def kenar_satirlari(stil, kenar):
    """Tuş sıraları arasındaki satır sayısı: alt kenar (sekizde bir satır) + en az 3/8 boşluk."""
    if stil == "yuzen":
        return 1
    return max(1, math.ceil((kenar + 3) / 8))


def _klavye_hkleri(kb):
    if kb == "gizli":
        return [0]
    if kb == "otomatik_k":
        return [2, 1]
    if kb == "otomatik_uzun":                     # önceki sürümlerin davranışı
        return [3, 2, 1]
    return list(range(KLAVYE_HK[kb], 0, -1))


YAZI_PARMAK_SATIRI = {None: 0, "cip": 2, "gosterge": 1 + GOSTERGE_Y}
YAZI_GOSTERGE_ADIM = (7, 15)          # tuş birimi başına sütun: altında adlar çakışır, üstü çok seyrek


def yazi_ic_yuksekligi(boyut, sonraki, parmak=None):
    """mesaj, boşluk, satır(lar), [sonraki], [boşluk, parmaklar], boşluk, ipucu"""
    return (1 + 1 + YAZI_SATIRLARI[boyut] + (1 if sonraki else 0) + YAZI_PARMAK_SATIRI[parmak]
            + 1 + 1)


def _yazi_parmak_secenekleri(s, hk, duzen=None, genislik=None):
    """Yazı kartının altındaki parmak satırı, tercih sırasıyla (sığmayan düşer).

    Ayar açıksa ekranın altındaki göstergelerin benzeri; kart çok darsa ya da yükseklik
    yetmezse klavye gizliyken çiplere, değilse hiçbir şeye düşülür.
    """
    yedek = "cip" if hk == 0 else None
    if not s.get("yazi_parmak"):
        return [yedek]
    if duzen is not None and genislik is not None and yazi_gosterge_konumlari(duzen, genislik) is None:
        return [yedek]
    return ["gosterge", yedek]


def _yerlesim_dene(H, w, duzen, n_harf, s, panel):
    alt_sutun = satir_say = cubuk = 0
    tek = True
    if panel:
        ic = H - 2
        tek = ic >= n_harf + 1
        alt_sutun = 1 if tek else 2
        satir_say = n_harf if tek else math.ceil(n_harf / 2)
        if satir_say + (1 if tek else 0) > ic:
            return None
    en_iyi = None                 # önce en büyük tuşlar, eşitlikte en uzun güven çubuğu
    for cubuk in (PANEL_CUBUKLARI if panel else (0,)):
        kenar = alt_sutun * (cubuk + 11) + (alt_sutun - 1) + 2 if panel else 0
        ana_w = w - (kenar + 1 if panel else 0)
        u = next((b for b in BIRIMLER if duzen.boyut(b, 1)[0] + 4 <= ana_w - 2), None)
        if u is not None and ana_w - 2 >= ANA_MIN_G and (en_iyi is None or u > en_iyi[0]):
            en_iyi = (u, cubuk, kenar, ana_w)
    if en_iyi is None:
        return None
    u, cubuk, kenar, ana_w = en_iyi

    istenen = s.get("yazi_boyutu", "normal")
    boyutlar = YAZI_BOYUTLARI[:YAZI_BOYUTLARI.index(istenen) + 1][::-1]
    hkler = _klavye_hkleri(s.get("klavye_boyutu", "otomatik_k"))
    ek = kenar_satirlari(s.get("tus_stili", "derinlik"), s.get("tus_kenar", 4))
    sonrakiler = [True, False] if s.get("sonraki", True) else [False]
    for yb in boyutlar:
        for hk in hkler:
            for parmak in _yazi_parmak_secenekleri(s, hk, duzen, ana_w - 2):
                for oz in OZET_SECENEKLERI:
                    for sonraki in sonrakiler:
                        yazi_ic = yazi_ic_yuksekligi(yb, sonraki, parmak)
                        kl_ic = duzen.boyut(u, hk, ek)[1] + 2 if hk else 0
                        kartlar = [oz + 2, yazi_ic + 2] + ([kl_ic + 2] if hk else [])
                        if sum(kartlar) <= H:
                            return _yerlesim_kur(H, w, duzen, panel, u, hk, ek, yb, oz, sonraki,
                                                 parmak, kartlar, kenar, ana_w, cubuk, alt_sutun,
                                                 satir_say, tek)
    return None


def _yerlesim_kur(H, w, duzen, panel, u, hk, ek_satir, yb, oz, sonraki, parmak, kartlar, kenar, ana_w,
                  cubuk, alt_sutun, satir_say, tek):
    artik = H - sum(kartlar)
    ek = {"bosluk": 0, "yazi_a": 0, "yazi_b": 0, "kl_ust": 0, "kl_alt": 0}
    bosluk_sayisi = len(kartlar) - 1
    if bosluk_sayisi and artik >= bosluk_sayisi:           # kartlar arasında birer satır
        ek["bosluk"] = 1
        artik -= bosluk_sayisi
    sinir = {"yazi_a": 2, "yazi_b": 2}
    if hk:
        sinir.update(kl_ust=1, kl_alt=1)
    while artik > 0 and any(ek[k] < s for k, s in sinir.items()):   # ölçülü iç boşluklar
        for k, s in sinir.items():
            if artik and ek[k] < s:
                ek[k] += 1
                artik -= 1
    grafik_h = 0
    if artik >= GRAFIK_MIN_Y + 2 + ek["bosluk"]:
        grafik_h = min(GRAFIK_MAX_Y, artik - 2 - ek["bosluk"])
        artik -= grafik_h + 2 + ek["bosluk"]
    sira = ["yazi_a", "yazi_b"] + (["kl_ust", "kl_alt"] if hk else [])
    for i in range(artik):
        ek[sira[i % len(sira)]] += 1

    x0, x1 = 0, ana_w - 1
    kb_w, kb_h = duzen.boyut(u, hk, ek_satir) if hk else (0, 0)
    d = {"u": u, "hk": hk, "ek": ek_satir, "yb": yb, "oz": oz, "sonraki": sonraki, "parmak": parmak,
         "kb_w": kb_w, "kb_h": kb_h,
         "cubuk": cubuk, "alt_sutun": alt_sutun, "satir_say": satir_say, "tek": tek,
         "yazi_a": ek["yazi_a"], "yazi_b": ek["yazi_b"], "kl_ust": ek["kl_ust"],
         "kl_alt": ek["kl_alt"], "x1": x1}
    y = 1
    d["ozet"] = (x0, y, x1, y + oz + 1)
    y += oz + 2 + ek["bosluk"]
    yazi_ic = yazi_ic_yuksekligi(yb, sonraki, parmak) + ek["yazi_a"] + ek["yazi_b"]
    d["yazi"] = (x0, y, x1, y + yazi_ic + 1)
    y += yazi_ic + 2
    d["klavye"] = None
    if hk:
        y += ek["bosluk"]
        kl_ic = kb_h + 2 + ek["kl_ust"] + ek["kl_alt"]
        d["klavye"] = (x0, y, x1, y + kl_ic + 1)
        y += kl_ic + 2
    d["grafik"] = None
    if grafik_h:
        y += ek["bosluk"]
        d["grafik"] = (x0, y, x1, y + grafik_h + 1)
        y += grafik_h + 2
    assert y - 1 == H, (y, H, d)
    d["panel"] = (w - kenar, 1, w - 1, H) if panel else None
    return d


def yerlesim_hesapla(h, w, duzen, n_harf, secenek=None):
    """Terminale sığan kart düzeni; hiçbiri sığmazsa None (sade düzen kullanılır).

    secenek: {"gosterge", "panel", "yazi_boyutu", "klavye_boyutu", "sonraki", "yazi_parmak"}
    """
    s = secenek or {}
    alt = GOSTERGE_Y if s.get("gosterge") else 0
    H = h - 1 - alt
    if H < 14 or w < MIN_GENISLIK:
        return None
    for panel in ([True, False] if s.get("panel", True) else [False]):
        d = _yerlesim_dene(H, w, duzen, n_harf, s, panel)
        if d:
            d["gosterge_y"] = h - GOSTERGE_Y if alt else None
            return d
    return None


def gereken_boyut(duzen, n_harf, secenek=None):
    """Rahat bir görünüm (6 sütunluk tuşlar, tek sütun harf paneli) için (sütun, satır)."""
    s = secenek or {}
    hk = _klavye_hkleri(s.get("klavye_boyutu", "otomatik_k"))[0]
    ek = kenar_satirlari(s.get("tus_stili", "derinlik"), s.get("tus_kenar", 4))
    yb = s.get("yazi_boyutu", "normal")
    sonraki = s.get("sonraki", True)
    parmak = _yazi_parmak_secenekleri(s, hk)[0]
    kartlar = [OZET_SECENEKLERI[0] + 2, yazi_ic_yuksekligi(yb, sonraki, parmak) + 2]
    if hk:
        kartlar.append(duzen.boyut(6, hk, ek)[1] + 4)
    H = max(sum(kartlar) + len(kartlar) - 1, n_harf + 3)
    w = max(duzen.boyut(6, 1)[0] + 4, ANA_MIN_G) + 2 + 1 + (12 + 11 + 2)
    return w, 1 + H + (GOSTERGE_Y if s.get("gosterge") else 0)


def el_cipleri(genislik, metinler):
    """Parmak çiplerinin göreli x konumları: [(x, genişlik)] — ortalanmış, eşit aralıklı."""
    toplam = sum(len(m) + 2 for m in metinler) + (len(metinler) - 1)
    x = max(0, (genislik - toplam) // 2)
    konumlar = []
    for m in metinler:
        konumlar.append((x, len(m) + 2))
        x += len(m) + 3
    return konumlar


# ---------------------------------------------------------------------------
# Parmak göstergeleri (fiziksel konum hesabı, curses'tan bağımsız)
# ---------------------------------------------------------------------------


def ekran_genisligi_mm(cikis=None):
    """Panelin fiziksel genişliği (mm), EDID'den; bulunamazsa None."""
    adaylar = []
    for yol in sorted(os.listdir("/sys/class/drm")) if os.path.isdir("/sys/class/drm") else []:
        tam = os.path.join("/sys/class/drm", yol)
        if not os.path.exists(os.path.join(tam, "edid")):
            continue
        ad = yol.split("-", 1)[1] if "-" in yol else yol
        try:
            with open(os.path.join(tam, "status")) as f:
                if f.read().strip() != "connected":
                    continue
            with open(os.path.join(tam, "edid"), "rb") as f:
                edid = f.read()
        except OSError:
            continue
        if len(edid) < 128:
            continue
        mm = edid[21] * 10
        if edid[54] | edid[55]:                    # ilk tanımlayıcı bir zamanlama bloğu
            dtd = ((edid[68] & 0xF0) << 4) | edid[66]
            if mm and 0.8 * mm <= dtd <= 1.2 * mm:
                mm = dtd
        if mm:
            oncelik = 0 if ad == cikis else (1 if ad.startswith("eDP") else 2)
            adaylar.append((oncelik, mm))
    return min(adaylar)[1] if adaylar else None


def ok_isareti(dx, dy):
    """Tuşun ana sıradaki parmağa göre yönü."""
    if dy < 0:
        return "↖" if dx < -0.5 else ("↗" if dx > 0.5 else "↑")
    if dy > 0:
        return "↙" if dx < -0.5 else ("↘" if dx > 0.5 else "↓")
    return "←" if dx < -0.5 else ("→" if dx > 0.5 else "•")


def _parmak_birimleri(duzen):
    """Ana sıradaki parmakların (ve başparmakların) tuş birimi cinsinden yatay konumu."""
    konum_birim = {}
    for i, c in zip(ANA_SIRA_INDEKSLERI, duzen.ana_tuslar):
        konum_birim[PARMAK_ORTA[i]] = duzen.tus(c).merkez
    el_ortasi = (konum_birim[_s("isaret")] + konum_birim[_g("isaret")]) / 2
    konum_birim[("sol", "basparmak")] = el_ortasi - 1
    konum_birim[("sag", "basparmak")] = el_ortasi + 1
    return konum_birim, el_ortasi


def yazi_gosterge_konumlari(duzen, genislik):
    """Yazı kartındaki göstergeler için {(taraf, tür): sütun}, 0..genislik aralığında ortalı.

    Parmaklar klavyedeki gibi aralıklı dizilir; başparmaklar işaret parmaklarının biraz
    içinde durur. Adlar çakışmadan sığmıyorsa None.
    """
    birim, orta = _parmak_birimleri(duzen)
    yari = max(abs(b - orta) for b in birim.values())
    adim = min(YAZI_GOSTERGE_ADIM[1], (genislik / 2 - 4) / yari)
    if adim < YAZI_GOSTERGE_ADIM[0]:
        return None
    merkez = genislik / 2
    sonuc = {p: int(round(merkez + (b - orta) * adim)) for p, b in birim.items()
             if p[1] != "basparmak"}
    for taraf, yon in (("sol", 1), ("sag", -1)):
        isaret = sonuc[(taraf, "isaret")]
        sonuc[(taraf, "basparmak")] = isaret + yon * max(7, int(round(0.5 * adim)))
    return sonuc


def gosterge_konumlari(duzen, sutun_sayisi, ayarlar, bilgi=None, ekran_mm=None):
    """Her parmağın ekran sütunu: {(taraf, tür): sütun}.

    Klavyenin ana bloğu ekranın ortasının altında varsayılır. bilgi (KWin'den
    pencere ve ekran geometrisi) varsa pencere konumu hesaba katılır; yoksa
    terminalin ekranı yatayda tamamen kapladığı varsayılır.
    """
    ekran_mm = ayarlar.get("ekran_genisligi_mm") or ekran_mm or 300
    adim = ayarlar.get("tus_araligi_mm", 19.0) * ayarlar.get("gosterge_olcek", 100) / 100
    kaydir = ayarlar.get("gosterge_kaydirma_mm", 0)
    merkez_birim = 7.5
    konum_birim, _ = _parmak_birimleri(duzen)
    sonuc = {}
    for parmak, birim in konum_birim.items():
        mm = (birim - merkez_birim) * adim + kaydir
        if bilgi and bilgi.get("eg") and bilgi.get("g"):
            px_mm = bilgi["eg"] / ekran_mm
            px = bilgi["ex"] + bilgi["eg"] / 2 + mm * px_mm
            sutun = (px - bilgi["x"]) / (bilgi["g"] / sutun_sayisi)
        else:
            sutun = sutun_sayisi / 2 + mm / (ekran_mm / sutun_sayisi)
        sonuc[parmak] = int(round(sutun))
    return sonuc


# ---------------------------------------------------------------------------
# Pencere boyutu (KDE'de KWin betiği, yoksa xterm kaçış kodları)
# ---------------------------------------------------------------------------


def _ata_pidleri():
    p, liste = os.getpid(), []
    while p > 1 and len(liste) < 64:
        liste.append(p)
        try:
            with open(f"/proc/{p}/stat") as f:
                p = int(f.read().rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
    return liste


class PencereYoneticisi:
    """Terminal penceresini büyütür ve çıkışta geri alır.

    KDE'de terminal hangisi olursa olsun KWin betiği kullanılır; diğer
    masaüstlerinde xterm'in standart kaçış kodları (CSI 8/9/10 t) denenir.
    İkisi de işe yaramazsa uygulama küçük düzene geçer.
    """

    def __init__(self):
        masaustu = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
        self.kwin = "KDE" in masaustu and shutil.which("dbus-send") is not None
        self.atalar = _ata_pidleri()
        self.yapilan = None           # ("boyut", sütun, satır) | ("kapla",) | ("tam_ekran",)
        self._sayac = 0

    def _kwin_betigi(self, govde):
        return """(function () {
  const atalar = %s;
  let w = workspace.activeWindow;
  if (!w || atalar.indexOf(w.pid) < 0) {
    w = null;
    const eslesen = workspace.windowList().filter(function (p) {
      return atalar.indexOf(p.pid) >= 0 && p.normalWindow; });
    if (eslesen.length === 1) w = eslesen[0];
  }
  if (!w) return;
  %s
})();""" % (json.dumps(self.atalar), govde)

    def _kwin_calistir(self, govde):
        if not self.kwin:
            return False
        self._sayac += 1
        ad = f"{KIMLIK}-{os.getpid()}-{self._sayac}"
        dizin = os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir()
        yol = os.path.join(dizin, ad + ".js")
        temel = ["dbus-send", "--session", "--print-reply", "--dest=org.kde.KWin"]
        try:
            with open(yol, "w", encoding="utf-8") as f:
                f.write(self._kwin_betigi(govde))
            r = subprocess.run(temel + ["/Scripting", "org.kde.kwin.Scripting.loadScript",
                                        f"string:{yol}", f"string:{ad}"],
                               capture_output=True, text=True, timeout=3)
            m = re.search(r"int32 (-?\d+)", r.stdout)
            if not m or int(m.group(1)) < 0:
                return False
            subprocess.run(temel + [f"/Scripting/Script{m.group(1)}", "org.kde.kwin.Script.run"],
                           capture_output=True, timeout=3)
            time.sleep(0.05)
            subprocess.run(temel + ["/Scripting", "org.kde.kwin.Scripting.unloadScript",
                                    f"string:{ad}"], capture_output=True, timeout=3)
            return True
        except (OSError, subprocess.SubprocessError):
            return False
        finally:
            try:
                os.remove(yol)
            except OSError:
                pass

    def bilgi(self):
        """KWin'den pencere ve ekran geometrisi (mantıksal piksel); yoksa None."""
        if not self.kwin or not shutil.which("journalctl"):
            return None
        isaret = f"{KIMLIK.upper()}-{os.getpid()}-{time.monotonic_ns()}"
        bas = time.time() - 2
        govde = """const c = w.clientGeometry;
  const o = w.output;
  const e = o ? o.geometry : workspace.clientArea(KWin.FullScreenArea, w);
  print("%s " + JSON.stringify({tam: w.fullScreen, x: c.x, y: c.y, g: c.width, y2: c.height,
        ex: e.x, ey: e.y, eg: e.width, ey2: e.height, cikis: o ? o.name : ""}));""" % isaret
        if not self._kwin_calistir(govde):
            return None
        for _ in range(12):
            try:
                r = subprocess.run(["journalctl", "--user", "-o", "cat", "--no-pager",
                                    "--since", f"@{bas:.0f}"], capture_output=True, text=True,
                                   timeout=3)
            except (OSError, subprocess.SubprocessError):
                return None
            for satir in reversed(r.stdout.splitlines()):
                if isaret in satir:
                    try:
                        return json.loads(satir.split(isaret, 1)[1])
                    except ValueError:
                        return None
            time.sleep(0.05)
        return None

    @staticmethod
    def _xterm(kod):
        try:
            os.write(sys.stdout.fileno(), kod.encode())
        except OSError:
            pass

    @staticmethod
    def _bekle(kosul, sure=0.8):
        son = time.monotonic() + sure
        while time.monotonic() < son:
            if kosul():
                return True
            time.sleep(0.04)
        return kosul()

    def boyut_iste(self, sutun, satir):
        """Terminali en az sutun×satir yapmaya çalışır; ekrana sığmazsa ekranı kaplar."""
        ilk = shutil.get_terminal_size()
        if ilk.columns >= sutun and ilk.lines >= satir:
            return True
        sutun, satir = max(sutun, ilk.columns), max(satir, ilk.lines)

        def yeterli():
            b = shutil.get_terminal_size()
            return b.columns >= sutun - 1 and b.lines >= satir - 1

        govde = """if (w.fullScreen) return;
  const c = w.clientGeometry, f = w.frameGeometry;
  const a = workspace.clientArea(KWin.MaximizeArea, w);
  const nw = Math.ceil(f.width + (%d - %d) * c.width / %d);
  const nh = Math.ceil(f.height + (%d - %d) * c.height / %d);
  if (nw > a.width || nh > a.height) { w.setMaximize(true, true); return; }
  let x = Math.round(f.x - (nw - f.width) / 2), y = Math.round(f.y - (nh - f.height) / 2);
  x = Math.max(a.x, Math.min(x, a.x + a.width - nw));
  y = Math.max(a.y, Math.min(y, a.y + a.height - nh));
  w.frameGeometry = {x: x, y: y, width: nw, height: nh};""" % (
            sutun, ilk.columns, ilk.columns, satir, ilk.lines, ilk.lines)
        if self._kwin_calistir(govde) and self._bekle(yeterli):
            self.yapilan = ("boyut", ilk.columns, ilk.lines)
            return True
        self._xterm(f"\x1b[8;{satir};{sutun}t")
        if self._bekle(yeterli):
            self.yapilan = ("boyut", ilk.columns, ilk.lines)
            return True
        return False

    def kapla(self):
        ilk = shutil.get_terminal_size()
        if not self._kwin_calistir("w.setMaximize(true, true);"):
            self._xterm("\x1b[9;1t")
        self.yapilan = ("kapla",)
        return self._bekle(lambda: shutil.get_terminal_size() != ilk)

    def tam_ekran(self):
        ilk = shutil.get_terminal_size()
        if not self._kwin_calistir("w.fullScreen = true;"):
            self._xterm("\x1b[10;1t")
        self.yapilan = ("tam_ekran",)
        return self._bekle(lambda: shutil.get_terminal_size() != ilk)

    def tam_ekran_degistir(self, simdi_tam):
        """Tam ekranı açar ya da kapatır (simdi_tam: şu an tam ekran mı)."""
        if simdi_tam:
            if not self._kwin_calistir("w.fullScreen = false;"):
                self._xterm("\x1b[10;0t")
            if self.yapilan == ("tam_ekran",):
                self.yapilan = None
            return True
        onceki = self.yapilan
        sonuc = self.tam_ekran()
        if onceki and onceki[0] == "boyut":
            self.yapilan = onceki        # çıkışta ilk boyuta dönmek için
        return sonuc

    def uygula(self, kip, hedef):
        if kip == "yeterli":
            return self.boyut_iste(*hedef)
        if kip == "kapla":
            return self.kapla()
        if kip == "tam_ekran":
            return self.tam_ekran()
        return True

    def geri_al(self):
        """Uygulamanın yaptığı pencere değişikliğini geri alır."""
        yapilan, self.yapilan = self.yapilan, None
        if not yapilan:
            return
        if yapilan[0] == "kapla":
            if not self._kwin_calistir("w.setMaximize(false, false);"):
                self._xterm("\x1b[9;0t")
        elif yapilan[0] == "tam_ekran":
            if not self._kwin_calistir("w.fullScreen = false;"):
                self._xterm("\x1b[10;0t")
        elif yapilan[0] == "boyut":
            self._kwin_calistir("if (w.fullScreen) w.fullScreen = false;")
            time.sleep(0.2)
            simdi = shutil.get_terminal_size()
            sutun, satir = yapilan[1], yapilan[2]
            govde = """const c = w.clientGeometry, f = w.frameGeometry;
  const nw = Math.round(f.width + (%d - %d) * c.width / %d);
  const nh = Math.round(f.height + (%d - %d) * c.height / %d);
  w.frameGeometry = {x: Math.round(f.x + (f.width - nw) / 2), y: Math.round(f.y + (f.height - nh) / 2),
                     width: nw, height: nh};""" % (sutun, simdi.columns, simdi.columns,
                                                   satir, simdi.lines, simdi.lines)
            if not self._kwin_calistir(govde):
                self._xterm(f"\x1b[8;{satir};{sutun}t")



# ---------------------------------------------------------------------------
# Tuş başına RGB aydınlatma (OpenRGB SDK sunucusu üzerinden)
# ---------------------------------------------------------------------------

# Farklı sürücülerin aynı tuş için kullandığı adlar → OpenRGB'nin standart adı
LED_ESANLAMLARI = {
    "grave": "`", "tilde": "`", "backtick": "`", "back quote": "`",
    "left ctrl": "left control", "lctrl": "left control", "ctrl": "left control",
    "right ctrl": "right control", "rctrl": "right control",
    "left super": "left windows", "left win": "left windows", "left gui": "left windows",
    "left meta": "left windows", "lwin": "left windows", "windows": "left windows",
    "right super": "right windows", "right win": "right windows", "right gui": "right windows",
    "right meta": "right windows", "rwin": "right windows",
    "altgr": "right alt", "alt gr": "right alt", "ralt": "right alt", "lalt": "left alt",
    "alt": "left alt", "capslock": "caps lock", "caps": "caps lock", "back space": "backspace",
    "bksp": "backspace", "return": "enter", "spacebar": "space", "space bar": "space",
    "lshift": "left shift", "rshift": "right shift", "shift": "left shift",
    "application": "menu", "context menu": "menu", "apps": "menu", "numlock": "num lock",
    "semicolon": ";", "quote": "'", "apostrophe": "'", "comma": ",", "period": ".",
    "slash": "/", "backslash": "\\", "minus": "-", "equals": "=", "equal": "=",
    "left bracket": "[", "right bracket": "]",
}
_NUMPAD_ONEKLERI = ("numpad ", "num pad ", "keypad ", "kp ", "number pad")


def _led_normal(ad):
    """"Key: Left Ctrl" → "left control" (esanlamlar ve numpad önekleri birleştirilir)."""
    a = ad.strip()
    if a.lower().startswith("key:"):
        a = a[4:]
    a = " ".join(a.lower().split())
    for onek in _NUMPAD_ONEKLERI:
        if a.startswith(onek) and a != onek.strip():
            a = "number pad " + a[len(onek):].strip()
            break
    return LED_ESANLAMLARI.get(a, a)


def _niteleyicisiz(ad):
    """"\\ (iso)" → "\\" """
    return re.sub(r"\s*\([^)]*\)$", "", ad)


def led_eslestir(led_adlari, konumlar):
    """{konum: LED sırası} — cihazın LED adlarını tuş konumlarına eşler."""
    dizin = {}
    for i, ad in enumerate(led_adlari):
        n = _led_normal(ad)
        dizin.setdefault(n, i)
        dizin.setdefault(_niteleyicisiz(n), i)
    sonuc = {}
    for konum in konumlar:
        n = _led_normal(konum)
        for aday in (n, _niteleyicisiz(n)):
            if aday in dizin:
                sonuc[konum] = dizin[aday]
                break
    return sonuc


class OpenRGBHatasi(Exception):
    pass


class OpenRGBIstemci:
    """OpenRGB SDK sunucusuyla konuşan küçük istemci (protokol 3; yalnızca standart kütüphane).

    Paket başlığı: "ORGB", cihaz (u32), paket kimliği (u32), veri boyu (u32). Klavye
    olarak bildirilen, tuş adları eşleşen cihazların en uygunu seçilir; çıkışta ilk
    renkler ve etkin mod (efekt) geri yüklenir.
    """

    PROTOKOL = 3
    KLAVYE_TURU = 5
    P_SAYI, P_VERI, P_SURUM, P_AD = 0, 1, 40, 50
    P_LEDLER, P_OZEL_MOD, P_MOD = 1050, 1100, 1101

    def __init__(self, adres="127.0.0.1:6742", zaman_asimi=0.5):
        konak, _, port = adres.rpartition(":")
        self.adres = (konak or "127.0.0.1", int(port or 6742))
        self.zaman_asimi = zaman_asimi
        self.soket = None
        self.cihaz = None             # {"sira", "ad", "led_sayisi", "ilk_renkler", ...}
        self.son_gonderilen = None

    # -- düşük seviye -------------------------------------------------------------

    def _gonder(self, cihaz, kimlik, veri=b""):
        self.soket.sendall(b"ORGB" + struct.pack("<III", cihaz, kimlik, len(veri)) + veri)

    def _oku(self, n):
        veri = b""
        while len(veri) < n:
            parca = self.soket.recv(n - len(veri))
            if not parca:
                raise OpenRGBHatasi("bağlantı kapandı")
            veri += parca
        return veri

    def _yanit(self, kimlik):
        """İstenen kimlikli yanıtı okur; araya giren bildirimleri (ör. cihaz listesi değişti) atlar."""
        for _ in range(64):
            bas = self._oku(16)
            if bas[:4] != b"ORGB":
                raise OpenRGBHatasi("geçersiz yanıt")
            _, gelen, boy = struct.unpack("<III", bas[4:])
            veri = self._oku(boy)
            if gelen == kimlik:
                return veri
        raise OpenRGBHatasi("yanıt alınamadı")

    @staticmethod
    def denetleyici_coz(veri, surum=PROTOKOL):
        """Denetleyici verisinden tür, ad, modlar (ham baytlarıyla) ve LED adları/renkleri."""
        i = 0

        def al(bicim):
            nonlocal i
            deger = struct.unpack_from(bicim, veri, i)
            i += struct.calcsize(bicim)
            return deger[0]

        def dizge():
            nonlocal i
            n = al("<H")
            metin = veri[i:i + n].rstrip(b"\0").decode("utf-8", "replace")
            i += n
            return metin

        def renkler():
            nonlocal i
            n = al("<H")
            liste = [tuple(veri[i + 4 * k:i + 4 * k + 3]) for k in range(n)]
            i += 4 * n
            return liste

        al("<I")                                         # veri boyu
        sonuc = {"tur": al("<i"), "ad": dizge()}
        if surum >= 1:
            dizge()                                      # satıcı
        for _ in range(4):
            dizge()                                      # açıklama, sürüm, seri, konum
        mod_sayisi = al("<H")
        sonuc["etkin_mod"] = al("<i")
        modlar = []
        for _ in range(mod_sayisi):
            bas = i
            ad = dizge()
            al("<i")                                     # değer
            al("<I")                                     # bayraklar
            al("<I"), al("<I")                           # hız en az/en çok
            if surum >= 3:
                al("<I"), al("<I")                       # parlaklık en az/en çok
            al("<I"), al("<I"), al("<I")                 # renk en az/en çok, hız
            if surum >= 3:
                al("<I")                                 # parlaklık
            al("<I"), al("<I")                           # yön, renk kipi
            renkler()
            modlar.append((ad, veri[bas:i]))
        sonuc["modlar"] = modlar
        for _ in range(al("<H")):                        # bölgeler
            dizge()
            al("<i"), al("<I"), al("<I"), al("<I")
            matris = al("<H")
            if matris:
                yuk, gen = al("<I"), al("<I")
                i += 4 * yuk * gen
        led_sayisi = al("<H")
        sonuc["ledler"] = []
        for _ in range(led_sayisi):
            sonuc["ledler"].append(dizge())
            al("<I")
        sonuc["renkler"] = renkler()
        return sonuc

    # -- yüksek seviye --------------------------------------------------------------

    def baglan(self, konumlar):
        """Sunucuya bağlanır ve konumlarla en çok eşleşen klavyeyi seçer; seçilen cihazın adı."""
        self.kapat()
        try:
            self.soket = socket.create_connection(self.adres, timeout=self.zaman_asimi)
            self.soket.settimeout(2.0)
            self._gonder(0, self.P_AD, f"{UYGULAMA_ADI}\0".encode())
            self._gonder(0, self.P_SURUM, struct.pack("<I", self.PROTOKOL))
            surum = min(self.PROTOKOL, struct.unpack("<I", self._yanit(self.P_SURUM))[0])
            self._gonder(0, self.P_SAYI)
            sayi = struct.unpack("<I", self._yanit(self.P_SAYI))[0]
            en_iyi = None
            for sira in range(sayi):
                self._gonder(sira, self.P_VERI, struct.pack("<I", surum))
                d = self.denetleyici_coz(self._yanit(self.P_VERI), surum)
                eslesme = led_eslestir(d["ledler"], konumlar)
                puan = len(eslesme) + (1000 if d["tur"] == self.KLAVYE_TURU else 0)
                if len(eslesme) >= 20 and (en_iyi is None or puan > en_iyi[0]):
                    en_iyi = (puan, sira, d, eslesme)
            if en_iyi is None:
                raise OpenRGBHatasi("tuş başına aydınlatmalı klavye bulunamadı")
            _, sira, d, eslesme = en_iyi
            self.cihaz = {"sira": sira, "ad": d["ad"], "led_sayisi": len(d["ledler"]),
                          "ilk_renkler": d["renkler"], "etkin_mod": d["etkin_mod"],
                          "modlar": d["modlar"], "eslesme": eslesme}
            self._gonder(sira, self.P_OZEL_MOD)          # doğrudan (Direct) kipe geç
            self.son_gonderilen = None
            return d["ad"]
        except (OSError, struct.error, ValueError) as hata:
            self.kapat()
            raise OpenRGBHatasi(str(hata)) from hata
        except OpenRGBHatasi:
            self.kapat()
            raise

    @property
    def bagli(self):
        return self.soket is not None and self.cihaz is not None

    def _bildirimleri_at(self):
        """Sunucunun kendiliğinden gönderdiği paketleri okumadan biriktirmemek için boşaltır."""
        try:
            self.soket.setblocking(False)
            while self.soket.recv(4096):
                pass
        except (BlockingIOError, InterruptedError):
            pass
        finally:
            self.soket.settimeout(2.0)

    def renkleri_gonder(self, renkler):
        """renkler: her LED için (r, g, b) listesi; değişmediyse gönderilmez."""
        if not self.bagli or renkler == self.son_gonderilen:
            return
        try:
            self._bildirimleri_at()
            govde = struct.pack("<H", len(renkler)) + b"".join(
                bytes((r, g, b, 0)) for r, g, b in renkler)
            self._gonder(self.cihaz["sira"], self.P_LEDLER, struct.pack("<I", 4 + len(govde)) + govde)
            self.son_gonderilen = list(renkler)
        except OSError as hata:
            self.kapat()
            raise OpenRGBHatasi(str(hata)) from hata

    def geri_yukle(self):
        """İlk renkleri ve etkin modu (kullanıcının efektini) geri yükler, bağlantıyı kapatır."""
        if not self.bagli:
            self.kapat()
            return
        c = self.cihaz
        try:
            self.renkleri_gonder(c["ilk_renkler"])
            if 0 <= c["etkin_mod"] < len(c["modlar"]):
                ham = c["modlar"][c["etkin_mod"]][1]
                veri = struct.pack("<i", c["etkin_mod"]) + ham
                self._gonder(c["sira"], self.P_MOD, struct.pack("<I", 4 + len(veri)) + veri)
        except (OSError, OpenRGBHatasi):
            pass
        finally:
            self.kapat()

    def kapat(self):
        if self.soket is not None:
            try:
                self.soket.close()
            except OSError:
                pass
        self.soket = None
        self.cihaz = None


# ---------------------------------------------------------------------------
# Arayüz (curses)
# ---------------------------------------------------------------------------


def guvenli_yaz(pencere, y, x, metin, attr=0):
    """Ekran dışına taşanı kırpar; sağ alt köşedeki curses.error'u yutar."""
    h, w = pencere.getmaxyx()
    if y < 0 or y >= h or x >= w or not metin:
        return
    if x < 0:
        metin, x = metin[-x:], 0
    metin = metin[:w - x]
    if not metin:
        return
    try:
        pencere.addstr(y, x, metin, attr)
    except curses.error:
        pass


GUN_ADLARI = {"tr": ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"],
              "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}


class Oturum:
    """Arayüzden bağımsız alıştırma oturumu: profil, satırlar, vuruşlar, modlar, XP ve rozetler.

    Terminal arayüzü (Uygulama) ve masaüstü arayüzü (harfiyen_masaustu) bunun üstüne
    kurulur; çizim ve girdi alt sınıfın işidir."""

    def __init__(self, ayarlar, temalar, depo, pencere_cli=None, rng=None):
        self.ayarlar = ayarlar
        self.temalar = temalar
        self.depo = depo
        self.pencere_cli = pencere_cli
        self.rng = rng or random.Random()
        self.duraklama = None
        self.mesaj = None
        self.mesaj_tur = None
        self.mesaj_bitis = 0.0
        self.flas_tus = None
        self.flas_bitis = 0.0
        self.satir_maks = SATIR_KARAKTER
        self.alistirma_modu = "ders"
        self.test = None
        self.metin = None
        self.son_vurus = None
        self.tur_harf_hizlari = collections.defaultdict(list)
        self.satir = ""
        self.sonraki = ""
        self._son_seviye = seviye_hesapla(self.depo.genel["xp"])[0]
        self.profili_yukle()

    # -- metinler ----------------------------------------------------------------

    @property
    def m(self):
        return METINLER[self.ayarlar["arayuz"]]

    @property
    def arayuz(self):
        return self.ayarlar["arayuz"]

    def parmak_adi(self, parmak):
        if parmak is None:
            return ""
        taraf, tur = parmak
        if not taraf:
            return self.m["Basparmak"]
        return f"{self.m[taraf]} {self.m['parmak_adlari'][tur]}"

    def parmak_tarifi(self, parmak):
        if parmak is None:
            return ""
        taraf, tur = parmak
        if not taraf:
            return self.m["basparmak"]
        return f"{self.m[taraf]} {self.m['parmak_adlari'][tur]} {self.m['parmak_ek']}"

    def tus_adi(self, c):
        return self.m["bosluk"] if c == " " else c

    def yuzde(self, v, ondalik=0):
        return self.m["yuzde"].format(v=f"{v:.{ondalik}f}")

    def deger_adi(self, deger):
        return self.m["degerler"].get(deger, str(deger))

    # -- profil ve satırlar --------------------------------------------------------

    def profili_yukle(self):
        self.duzen = Duzen(self.ayarlar["klavye"], self.ayarlar["fiziksel"], self.ayarlar["numpad"])
        dil = self.ayarlar["dil"]
        try:
            sira = mufredat(dil, self.duzen)
        except UyumsuzDuzen as eksik:
            dil = DUZENLER[self.ayarlar["klavye"]]["dil"]
            self.ayarlar["dil"] = dil
            sira = mufredat(dil, self.duzen)
            self.mesaj_ver(self.m["uyumsuz"].format(duzen=self.ayarlar["klavye"],
                                                    eksik=str(eksik)), "uyari", 10)
        self.dil_kodu = dil
        self.dil = DILLER[dil]
        self.anahtar = profil_anahtari(dil, self.ayarlar["klavye"])
        pencere = self.pencere_cli or self.ayarlar["ustalik_penceresi"]
        self.ilerleme = self.depo.profil(self.anahtar, pencere, sira,
                                         self.ayarlar["ustalik_olcutu"], self.ayarlar["hedef_hiz"])
        if self.alistirma_modu == "metin":
            self.alistirma_modu = "ders"
        self.satir = ""
        self.sonraki = ""
        self.yeni_satir(tazele=True)

    def _satir_uret(self, onceki):
        a, il = self.ayarlar, self.ilerleme
        sesliler = frozenset(self.dil["sesliler"])
        mod = self.alistirma_modu
        if mod == "metin" and self.metin:
            satir, self.metin["konum"], sarildi = metin_satiri(
                self.metin["kelimeler"], self.metin["konum"], self.satir_maks)
            if sarildi:
                self.mesaj_ver(self.m["metin_bitti"], "bilgi", 4)
            return satir
        ek = {}
        if mod == "zayif":
            ek = {"agirlik": zayif_agirliklari(il), "ciftler": il.zayif_ciftler()}
        elif mod == "test":
            ek = {"gercek_olasilik": 0.95}
        satir = satir_uret(il, self.rng, self.satir_maks, onceki=onceki,
                           kelimeler=self.dil["kelimeler"], sesliler=sesliler, **ek)
        return susle(satir, self.rng, self.duzen, self.dil_kodu, a["buyuk_harf"], a["noktalama"],
                     a["rakamlar"], self.satir_maks)

    def yeni_satir(self, tazele=False):
        """Sonraki satıra geç; tazele=True ise ikisini de yeniden üret."""
        son = self.satir.split()[-1] if self.satir else None
        if tazele or not self.sonraki:
            self.satir = self._satir_uret(son)
        else:
            self.satir = self.sonraki
        self.sonraki = self._satir_uret(self.satir.split()[-1] if self.satir else None)
        self.konum = 0
        self.hatalar = set()
        self.konumda_hata = False
        self.zamanlar = []
        self.hatali_basis = 0
        self.tur_harf_hizlari = collections.defaultdict(list)

    @property
    def hedef(self):
        return self.satir[self.konum] if self.konum < len(self.satir) else None

    def mesaj_ver(self, metin, tur, sure=0.0):
        self.mesaj, self.mesaj_tur = metin, tur
        self.mesaj_bitis = time.monotonic() + sure if sure else 0.0

    def bildir(self, metinler):
        """Birden çok geçici bilgiyi tek mesajda gösterir."""
        if metinler:
            self.mesaj_ver(" · ".join(metinler), "bilgi", BILGI_SURESI)

    def kaydet(self):
        try:
            self.depo.kaydet(self.anahtar, self.ilerleme)
        except OSError as hata:
            self.mesaj_ver(f"{hata}", "hata")

    def _durum_mesaji(self):
        il, m = self.ilerleme, self.m
        n = len(il.acik_harfler)
        if il.siradaki_harf is None:
            if il.tumu_ustalasti_mi():
                return m["tebrik"].format(m=len(il.sira))
            return m["tum_acik"].format(n=il.hazir_sayisi(), m=n)
        return m["hazir"].format(n=il.hazir_sayisi(), m=n)

    # -- oyun: günlük süre, XP, rozetler ------------------------------------------

    def _bugun_sn(self):
        return self.depo.genel["gunluk"].get(bugun_anahtari(), 0.0)

    def _sure_ekle(self, saniye):
        g = self.depo.genel
        gun = bugun_anahtari()
        g["gunluk"][gun] = g["gunluk"].get(gun, 0.0) + saniye
        g["saniye"] = g.get("saniye", 0.0) + saniye

    def xp_ekle(self, miktar, bildirimler):
        self.depo.genel["xp"] += miktar

    def seviye_denetle(self, bildirimler):
        """Vuruşlardan ve ödüllerden gelen XP ile seviye atlandıysa bildirir."""
        yeni = seviye_hesapla(self.depo.genel["xp"])[0]
        if yeni > self._son_seviye:
            bildirimler.append(self.m["seviye_atladi"].format(n=yeni))
        self._son_seviye = yeni

    def _rozet_durumu(self):
        g, il = self.depo.genel, self.ilerleme
        hedef_sn = self.ayarlar["gunluk_hedef_dk"] * 60
        return {"satir": g["satir"], "acik": il.acik_sayisi, "toplam": len(il.sira),
                "kusursuz": g.get("kusursuz", False), "dogruluk_serisi": il.dogruluk_serisi(),
                "en_iyi_dbk": self.depo.en_iyi("turlar"),
                "hedef_bugun": bool(hedef_sn) and self._bugun_sn() >= hedef_sn,
                "seri": gun_serisi(g["gunluk"], hedef_sn), "bugun_dk": self._bugun_sn() / 60,
                "test_sayisi": self.depo.test_sayisi(), "en_iyi_test": self.depo.en_iyi("testler"),
                "gece": g.get("gece", False)}

    def rozetleri_denetle(self, bildirimler):
        self.kaydet()                            # en iyi değerler depodan okunur
        g = self.depo.genel
        durum = self._rozet_durumu()
        g["en_uzun_seri"] = max(g.get("en_uzun_seri", 0), durum["seri"])
        for kimlik, ad_tr, ad_en, _, _, kosul in ROZETLER:
            if kimlik not in g["rozetler"] and kosul(durum):
                g["rozetler"][kimlik] = bugun_anahtari()
                bildirimler.append(self.m["yeni_rozet"].format(
                    ad=ad_tr if self.arayuz == "tr" else ad_en, xp=ROZET_XP))
                self.xp_ekle(ROZET_XP, bildirimler)

    # -- yazma ---------------------------------------------------------------------

    def satir_bitti(self, tamamlandi):
        bildirimler = []
        il = self.ilerleme
        if tamamlandi:
            ist = tur_istatistikleri(self.zamanlar, self.hatali_basis)
            if ist:
                ist["puan"] = puan_hesapla(ist["dbk"], ist["dogruluk"], il.acik_sayisi)
                il.tur_kaydet(ist)
                g = self.depo.genel
                g["satir"] += 1
                self.xp_ekle(5 + (10 if ist["dogruluk"] >= 100 else 0), bildirimler)
                if ist["dogruluk"] >= 100 and len(self.satir) >= 20:
                    g["kusursuz"] = True
                if datetime.datetime.now().hour < 5:
                    g["gece"] = True
                for h, hizlar in self.tur_harf_hizlari.items():
                    il.harf_tur_kaydet(h, statistics.fmean(hizlar))
        if self.alistirma_modu in ("ders", "zayif"):
            yeni = il.yeni_harf_dene()
            if yeni:
                bildirimler.insert(0, self.m["yeni_harf"].format(
                    h=yeni, parmak=self.parmak_tarifi(self.duzen.parmak(yeni))))
                self.xp_ekle(100, bildirimler)
        else:
            yeni = None
        if tamamlandi:
            self.rozetleri_denetle(bildirimler)
        self.seviye_denetle(bildirimler)
        self.kaydet()
        self.bildir(bildirimler)
        self.yeni_satir(tazele=bool(yeni))

    def tus_isle(self, tus):
        hedef = self.hedef
        if hedef is None:
            return
        simdi = time.monotonic()
        if self.alistirma_modu == "test" and self.test is not None and self.test["bas"] is None:
            self.test["bas"] = simdi
        ara = simdi - self.son_vurus if self.son_vurus is not None else None
        self.son_vurus = simdi
        harf = kucuk_harf(hedef, self.dil_kodu)
        izli = harf in self.ilerleme.gecmis
        onceki = kucuk_harf(self.satir[self.konum - 1], self.dil_kodu) if self.konum else None
        ilk_basis = not self.konumda_hata
        if tus == hedef:
            hiz = 12 / ara if ara and ara < EN_UZUN_ARA else None
            if ara and ara < EN_UZUN_ARA:
                self._sure_ekle(ara)
            if ilk_basis:
                if izli:
                    self.ilerleme.deneme_kaydet(harf, True, hiz)
                    if hiz:
                        self.tur_harf_hizlari[harf].append(hiz)
                    if onceki:
                        self.ilerleme.cift_kaydet(onceki, harf, True)
                self.depo.genel["vurus"] += 1
                self.depo.genel["xp"] += 1
            if self.test is not None:
                self.test["dogru"] += 1
            self.zamanlar.append(simdi)
            self.konum += 1
            self.konumda_hata = False
            if self.mesaj_tur == "hata":
                self.mesaj = None
            if self.konum >= len(self.satir):
                self.satir_bitti(tamamlandi=True)
            return
        # yanlış tuş: imleç ilerlemez, bu konum bir kez "yanlış" sayılır
        self.hatali_basis += 1
        if self.test is not None:
            self.test["hata"] += 1
        if ilk_basis:
            self.konumda_hata = True
            self.hatalar.add(self.konum)
            if izli:
                self.ilerleme.deneme_kaydet(harf, False)
                if onceki:
                    self.ilerleme.cift_kaydet(onceki, harf, False)
        cozum = self.duzen.cozumle(tus)
        self.flas_tus = cozum[0] if cozum else tus
        self.flas_bitis = simdi + FLAS_SURESI
        if hedef == " ":
            hedef_tarif = self.m["hedef_bosluk"]
        else:
            hedef_tarif = self.m["hedef_harf"].format(
                c=hedef, parmak=self.parmak_tarifi(self.duzen.parmak(hedef)))
        metin = self.m["yanlis"].format(bas=self.tus_adi(tus), hedef=hedef_tarif)
        kucuk = kucuk_harf(tus, self.dil_kodu)
        if tus != kucuk and kucuk == hedef:
            metin += self.m["caps"]
        self.mesaj_ver(metin, "hata")

    # -- alıştırma modları -------------------------------------------------------------

    def alistirma_modu_sec(self, mod, metin=None):
        self.alistirma_modu = mod
        self.test = None
        self.metin = None
        if mod == "test":
            self.test = {"bas": None, "dogru": 0, "hata": 0,
                         "sure": self.ayarlar["test_suresi_sn"]}
        elif mod == "metin" and metin:
            ad, icerik = metin
            self.metin = {"ad": ad, "kelimeler": metin_hazirla(icerik, self.duzen), "konum": 0}
        self.satir = ""
        self.sonraki = ""
        self.yeni_satir(tazele=True)

    def test_kalan(self):
        """Hız testinde kalan saniye (test başlamadıysa tam süre); test yoksa None."""
        t = self.test
        if t is None:
            return None
        if t["bas"] is None:
            return float(t["sure"])
        gecen = (self.duraklama or time.monotonic()) - t["bas"]
        return max(0.0, t["sure"] - gecen)

    def test_sonucu_kaydet(self):
        """Süresi dolan hız testini kaydeder ve yenisini hazırlar.

        (sonuç, önceki en iyi DBK, bildirimler) döner."""
        t = self.test
        dakika = t["sure"] / 60
        sonuc = {"dbk": t["dogru"] / 5 / dakika,
                 "dogruluk": 100 * t["dogru"] / max(1, t["dogru"] + t["hata"]),
                 "sure": t["sure"], "dogru": t["dogru"], "hata": t["hata"]}
        onceki_en_iyi = self.depo.en_iyi("testler")
        self.ilerleme.test_kaydet(sonuc)
        bildirimler = []
        self.xp_ekle(20, bildirimler)
        self.rozetleri_denetle(bildirimler)
        self.seviye_denetle(bildirimler)
        self.kaydet()
        self.test = {"bas": None, "dogru": 0, "hata": 0, "sure": self.ayarlar["test_suresi_sn"]}
        self.yeni_satir(tazele=True)
        return sonuc, onceki_en_iyi, bildirimler

    # -- duraklama -----------------------------------------------------------------

    def duraklat(self):
        """Yazmaya ara verildi (menü, pencere): geçen süre hıza ve teste sayılmaz."""
        if self.duraklama is None:
            self.duraklama = time.monotonic()

    def surdur(self):
        if self.duraklama is None:
            return
        gecen = time.monotonic() - self.duraklama
        self.zamanlar = [t + gecen for t in self.zamanlar]   # duraklama süreyi bozmasın
        if self.son_vurus is not None:
            self.son_vurus += gecen
        if self.test and self.test["bas"] is not None:
            self.test["bas"] += gecen
        self.duraklama = None


class Uygulama(Oturum):
    def __init__(self, ekran, ayarlar, temalar, depo, pencere, uyarilar=(), pencere_cli=None,
                 rng=None):
        self.ekran = ekran
        self.pencere = pencere
        self.calisiyor = True
        self.mod = "yaz"
        self.liste = None
        self.bilgi_d = None
        self.cikis_secim = 1
        self._cikis_donus = "yaz"
        self.sifirla_secim = 2
        self.ayar_secim = 0
        self.ayar_kaydirma = 0
        self.ayar_yedek = None
        self.ayar_hata = None
        self.ayar_bilgi = None
        self.bolgeler = []
        self.kutu = None
        self.disari = None
        self.yerlesim = None
        self.pencere_bilgisi = None
        self.bilgi_zamani = time.monotonic() + 0.2
        self.ekran_mm = ekran_genisligi_mm()
        self._renkler_hazir = False
        self.ayarlar = ayarlar
        self.temalar = temalar
        self.renkleri_kur()
        self.fareyi_kur()
        super().__init__(ayarlar, temalar, depo, pencere_cli, rng)
        if uyarilar:
            self.mesaj_ver(" · ".join(uyarilar)[:220], "uyari", 12)
        self.rgb = None
        self.rgb_deneme = None
        self.rgb_kur()

    # -- tuş başına RGB aydınlatma -------------------------------------------------

    RGB_YENIDEN_DENE = 15.0

    def rgb_kur(self, sessiz=False):
        """Ayara göre OpenRGB'ye bağlanır ya da bağlantıyı bırakıp ışıkları geri yükler."""
        self.rgb_kapat()
        if self.ayarlar["rgb_isik"] != "openrgb":
            return
        self.rgb = OpenRGBIstemci(self.ayarlar["rgb_adres"])
        try:
            ad = self.rgb.baglan([k for _, k in self.duzen.led_konumlari()])
            self.rgb_deneme = None
            if not sessiz:
                self.mesaj_ver(self.m["rgb_baglandi"].format(ad=ad), "bilgi", 4)
        except (OpenRGBHatasi, ValueError) as hata:
            self.rgb_deneme = time.monotonic() + self.RGB_YENIDEN_DENE
            if not sessiz:
                self.mesaj_ver(self.m["rgb_hata"].format(adres=self.ayarlar["rgb_adres"], hata=hata),
                               "uyari", 8)

    def rgb_kapat(self):
        if self.rgb is not None:
            self.rgb.geri_yukle()
        self.rgb = None
        self.rgb_deneme = None

    def _isik(self, ad, oran=1.0):
        rgb = self.rgb_renkler.get(ad) or (200, 200, 200)
        carpan = oran * self.ayarlar["rgb_parlaklik"] / 100
        return tuple(max(0, min(255, round(c * carpan))) for c in rgb)

    def rgb_guncelle(self):
        """Basılacak tuşu (ve Shift eşini) klavyede yakar; diğer tuşlar ayara göre."""
        istemci = self.rgb
        if istemci is None or not istemci.bagli:
            return
        c = istemci.cihaz
        zemin = self.ayarlar["rgb_zemin"]
        bos = self._isik("yazi", 0.12) if zemin == "soluk" else (0, 0, 0)
        renkler = [bos] * c["led_sayisi"]
        acik = set(self.ilerleme.acik_harfler)
        for tus, konum in self.duzen.led_konumlari():
            sira = c["eslesme"].get(konum)
            if sira is None or sira >= len(renkler):
                continue
            k = tus.karakter
            if self.flas_tus is not None and k == self.flas_tus and not tus.numpad:
                renk = self._isik("hata")
            elif k is not None and k == self.hedef_taban and not tus.numpad:
                renk = self._isik("vurgu")
            elif self.hedef_shift and tus.ad == self.hedef_shift:
                renk = self._isik("vurgu", 0.45)
            elif zemin == "parmak" and k is not None and (k == " " or k in acik) and not tus.numpad:
                renk = self._isik("p:" + tus.parmak[1], 0.3)
            elif renkler[sira] != bos:
                continue                                  # aynı LED'e bağlı ikinci parça (ISO Enter)
            else:
                renk = bos
            renkler[sira] = renk
        try:
            istemci.renkleri_gonder(renkler)
        except OpenRGBHatasi as hata:
            self.rgb_deneme = time.monotonic() + self.RGB_YENIDEN_DENE
            self.mesaj_ver(self.m["rgb_hata"].format(adres=self.ayarlar["rgb_adres"], hata=hata),
                           "uyari", 8)

    # -- renkler -------------------------------------------------------------------

    def renkleri_kur(self):
        self.renkli = curses.has_colors() and curses.COLORS >= 8
        self.cifler = {}
        if self.renkli and not self._renkler_hazir:
            try:
                curses.use_default_colors()
            except curses.error:
                pass
            self._renkler_hazir = True
        tema = self.temalar.get(self.ayarlar["tema"]) or self.temalar["gece"]
        self.tema = tema
        n = curses.COLORS if self.renkli else 0
        self.rn, self.rgb_renkler = {}, {}
        for alan in TEMA_ALANLARI:
            self.rgb_renkler[alan] = renk_rgb(tema[alan])
            self.rn[alan] = renk_numarasi(tema[alan], n) if self.renkli else -1
        for p in PARMAK_TURLERI:
            self.rgb_renkler["p:" + p] = renk_rgb(tema["parmak"][p])
            self.rn["p:" + p] = renk_numarasi(tema["parmak"][p], n) if self.renkli else -1
        zemin = self.rgb_renkler["zemin"] or (0, 0, 0)
        yazi = self.rgb_renkler["yazi"] or ((30, 30, 30) if parlaklik(zemin) > 0.5 else (220, 220, 220))
        oran = tema.get("tus_karisim", 0.6)

        def kontrast(dolgu):
            return (24, 24, 24) if parlaklik(dolgu) > 0.55 else (238, 238, 238)

        def turet(ad, rgb, yazi_rgb=None, sabit=None):
            self.rgb_renkler[ad] = rgb
            self.rn[ad] = sabit if sabit is not None else (en_yakin_renk(rgb, n) if self.renkli else -1)
            yazi_rgb = yazi_rgb or kontrast(rgb)
            self.rgb_renkler["y" + ad] = yazi_rgb
            self.rn["y" + ad] = en_yakin_renk(yazi_rgb, n) if self.renkli else -1

        for p in PARMAK_TURLERI:
            ham = tema["parmak"][p]
            parmak_rgb = self.rgb_renkler["p:" + p] or (170, 170, 170)
            sabit = None
            if oran >= 1 and renk_coz(ham)[0] == "indeks":
                sabit = self.rn["p:" + p]           # terminal teması: paletin kendi rengi
            turet("t:" + p, karistir(parmak_rgb, zemin, oran), sabit=sabit)
        notr_ham = tema.get("tus_notr")
        if notr_ham is not None:
            turet("t:notr", renk_rgb(notr_ham), karistir(yazi, renk_rgb(notr_ham), 0.75),
                  sabit=renk_numarasi(notr_ham, n) if self.renkli else -1)
        else:
            notr = karistir(yazi, zemin, 0.13)
            turet("t:notr", notr, karistir(yazi, notr, 0.62))
        vurgu = self.rgb_renkler["vurgu"] or (230, 190, 80)
        turet("t:vurgu2", karistir(vurgu, zemin, 0.45))
        for ad in ("dogru", "uyari", "hata"):
            turet("isi:" + ad, karistir(self.rgb_renkler[ad] or (128, 128, 128), zemin, 0.55))
        # harf çiplerinin güven dereceleri: hata → uyarı → doğru
        hata, uyari, dogru = (self.rgb_renkler[a] or (128, 128, 128) for a in ("hata", "uyari", "dogru"))
        for i in range(6):
            g = i / 5
            renk = karistir(uyari, hata, g * 2) if g <= 0.5 else karistir(dogru, uyari, (g - 0.5) * 2)
            turet(f"cip:{i}", karistir(renk, zemin, 0.5 + 0.1 * (i == 5)))
        self.ekran.bkgd(" ", self.cift("yazi", "zemin"))

    def dudak(self, dolgu):
        """Tuşun alt kenarı için dolgudan koyu ton (adı döner)."""
        ad = "d:" + dolgu
        if ad not in self.rn:
            rgb = self.rgb_renkler.get(dolgu) or (90, 90, 90)
            govde = self.rn.get(dolgu, -1)
            numara = -1
            if self.renkli:
                # koyu ton palette gövdeyle aynı renge yuvarlanırsa daha koyusunu dene
                for oran in (0.62, 0.45, 0.3):
                    numara = en_yakin_renk(karistir(rgb, (0, 0, 0), oran), curses.COLORS)
                    if numara != govde:
                        break
                self.rgb_renkler[ad] = xterm_rgb(numara)
            self.rn[ad] = numara
        return ad

    def cift(self, on, arka="zemin"):
        """Tema alan adları ya da türetilmiş renk adlarıyla renk çifti özniteliği."""
        if not self.renkli:
            return 0
        fg = self.rn.get(on, -1) if isinstance(on, str) else on
        bg = self.rn.get(arka, -1) if isinstance(arka, str) else arka
        if bg == -1 and arka not in (None, "zemin"):
            bg = self.rn["zemin"]
        anahtar = (fg, bg)
        if anahtar not in self.cifler:
            no = len(self.cifler) + 1
            if no >= curses.COLOR_PAIRS:
                return 0
            try:
                curses.init_pair(no, fg, bg)
            except curses.error:
                return 0
            self.cifler[anahtar] = no
        return curses.color_pair(self.cifler[anahtar])

    def fareyi_kur(self):
        if self.ayarlar["fare"]:
            curses.mousemask(curses.ALL_MOUSE_EVENTS)
            curses.mouseinterval(0)
        else:
            curses.mousemask(0)

    # -- alıştırma modları -------------------------------------------------------------

    def mod_listesi(self):
        m = self.m
        ogeler = []
        for mod in ("ders", "zayif", "test", "metin"):
            aciklama = m["mod_aciklama"][mod].format(s=self.ayarlar["test_suresi_sn"])
            if mod == "metin":
                eylem = self.metin_listesi
            else:
                eylem = (lambda mod=mod: self.alistirma_modu_sec(mod))
            isaret = "● " if mod == self.alistirma_modu else "  "
            ogeler.append((isaret + m["modlar"][mod], aciklama, eylem))
        self.liste_ac(m["menu_mod"], ogeler)

    def metin_listesi(self):
        metinler = metinleri_listele(self.dil_kodu)
        ogeler = [(ad, f"{len(icerik.split())} kelime" if self.arayuz == "tr"
                   else f"{len(icerik.split())} words",
                   (lambda ad=ad, icerik=icerik: self.alistirma_modu_sec("metin", (ad, icerik))))
                  for ad, icerik in metinler]
        if not ogeler:
            self.mesaj_ver(self.m["metin_yok"], "uyari", 4)
            return
        self.liste_ac(self.m["metin_sec"], ogeler)

    def test_bitir(self):
        sonuc, onceki_en_iyi, bildirimler = self.test_sonucu_kaydet()
        m = self.m
        satirlar = [
            [(f"{sonuc['dbk']:.1f}", "baslik", curses.A_BOLD), (f" {m['dbk']}", "soluk", 0)],
            [(f"{m['m_dogruluk']}: ", "soluk", 0),
             (self.yuzde(sonuc["dogruluk"], 1), "baslik", curses.A_BOLD)],
            [(f"{sonuc['dogru']} ✓  {sonuc['hata']} ✗  ·  {sonuc['sure']} s", "yazi", 0)],
        ]
        if sonuc["dbk"] > onceki_en_iyi:
            satirlar.append([(m["test_rekor"], "dogru", curses.A_BOLD)])
        satirlar += [[(b, "uyari", 0)] for b in bildirimler]
        self.bilgi_ac(m["test_sonuc"], satirlar,
                      [(m["test_tekrar"], lambda: self.alistirma_modu_sec("test")),
                       (m["derse_don"], lambda: self.alistirma_modu_sec("ders"))], genislik=44)

    def alistirma_modu_sec(self, mod, metin=None):
        super().alistirma_modu_sec(mod, metin)
        self.mod_ac("yaz")

    # -- modlar (pencereler) ------------------------------------------------------------

    def mod_ac(self, mod):
        if self.mod == "yaz" and mod != "yaz":
            self.duraklat()
        self.mod = mod
        if mod == "cikis":
            self.cikis_secim = 1
        elif mod == "sifirla":
            self.sifirla_secim = 2
        elif mod == "ayarlar":
            self.ayar_yedek = dict(self.ayarlar)
            self.ayar_hata = self.ayar_bilgi = None
            self.ayar_secim = self._ayar_satirlari_secilebilir()[0]
        elif mod == "yaz":
            self.surdur()

    def liste_ac(self, baslik, ogeler, ipucu=None):
        self.liste = {"baslik": baslik, "ogeler": ogeler, "secim": 0,
                      "ipucu": ipucu or self.m["menu_ipucu"]}
        self.mod_ac("liste")

    def bilgi_ac(self, baslik, satirlar, dugmeler=(), genislik=None):
        self.bilgi_d = {"baslik": baslik, "satirlar": satirlar, "kaydirma": 0,
                        "dugmeler": list(dugmeler), "genislik": genislik}
        self.mod_ac("bilgi")

    def kapat(self):
        self.liste = None
        self.bilgi_d = None
        self.mod_ac("yaz")

    def menu_ac(self):
        m = self.m
        self.liste_ac(m["menu_baslik"], [
            (m["menu_devam"], "Esc", self.kapat),
            (m["menu_mod"], "F8", self.mod_listesi),
            (m["menu_istatistik"], "F4", self.istatistik_ac),
            (m["menu_ayarlar"], "F2", lambda: self.mod_ac("ayarlar")),
            (m["menu_yardim"], "F1", self.yardim_ac),
            (m["menu_tam"], "F11", self.tam_ekran_degistir),
            (m["menu_satir"], "Tab", lambda: (self.kapat(), self.satir_bitti(False))),
            (m["menu_cikis"], "Ctrl-C", self.cikis_onayi),
        ])

    def cikis_onayi(self):
        if self.mod != "cikis":
            self._cikis_donus = self.mod
            self.mod_ac("cikis")

    def cikis_iptal(self):
        self.mod = self._cikis_donus
        if self.mod == "yaz":
            self.mod_ac("yaz")

    def cik(self):
        self.calisiyor = False

    def tam_ekran_mi(self):
        b = self.pencere_bilgisi
        if b:
            return bool(b.get("tam"))
        return self.pencere.yapilan == ("tam_ekran",)

    def tam_ekran_degistir(self):
        if self.mod != "yaz":
            self.kapat()
        self.pencere.tam_ekran_degistir(self.tam_ekran_mi())
        self.pencere_bilgisi = None
        self.bilgi_zamani = time.monotonic() + 0.3

    def yazi_boyutu_degistir(self, yon):
        i = YAZI_BOYUTLARI.index(self.ayarlar["yazi_boyutu"])
        self.ayarlar["yazi_boyutu"] = YAZI_BOYUTLARI[max(0, min(len(YAZI_BOYUTLARI) - 1, i + yon))]
        self.ayarlari_yaz()
        self.mesaj_ver(self.m["yazi_boyutu_mesaj"].format(
            b=self.deger_adi(self.ayarlar["yazi_boyutu"])), "bilgi", 2)

    def klavye_boyutu_degistir(self):
        ayar_degistir(self.ayarlar, "klavye_boyutu", 1, self.temalar)
        self.ayarlari_yaz()
        self.mesaj_ver(self.m["klavye_boyutu_mesaj"].format(
            b=self.deger_adi(self.ayarlar["klavye_boyutu"])), "bilgi", 2)

    def isi_haritasi_degistir(self):
        self.ayarlar["klavye_gorunumu"] = "isi" if self.ayarlar["klavye_gorunumu"] == "parmak" \
            else "parmak"
        self.ayarlari_yaz()

    # -- olaylar -------------------------------------------------------------------------

    KISAYOLLAR = {
        "F1": "yardim_ac", "F2": "_ayarlari_ac", "F3": "isi_haritasi_degistir",
        "F4": "istatistik_ac", "F7": "klavye_boyutu_degistir", "F8": "mod_listesi",
        "F11": "tam_ekran_degistir",
    }

    def _ayarlari_ac(self):
        self.liste = self.bilgi_d = None
        self.mod_ac("ayarlar")

    def olay(self, tus):
        if tus == curses.KEY_RESIZE:
            self.boyut_degisti()
            return
        if tus == curses.KEY_MOUSE:
            self.fare_olayi()
            return
        if tus == "\x03":                               # Ctrl-C
            if self.mod == "cikis":
                self.cik()
            else:
                self.cikis_onayi()
            return
        if self.mod in ("yaz", "liste", "bilgi") and isinstance(tus, int):
            for ad, yontem in self.KISAYOLLAR.items():
                if tus == getattr(curses, "KEY_" + ad):
                    getattr(self, yontem)()
                    return
        getattr(self, "_olay_" + self.mod)(tus)

    def _olay_yaz(self, tus):
        if tus == "\x1b":
            self.menu_ac()
        elif tus == "\t":
            self.satir_bitti(tamamlandi=False)
        elif tus == curses.KEY_F5:
            self.yazi_boyutu_degistir(-1)
        elif tus == curses.KEY_F6:
            self.yazi_boyutu_degistir(1)
        elif isinstance(tus, str) and tus.isprintable() and self.yerlesim is not False:
            self.tus_isle(unicodedata.normalize("NFC", tus))

    def _olay_liste(self, tus):
        ogeler = self.liste["ogeler"]
        if tus == "\x1b":
            self.kapat()
        elif tus in (curses.KEY_UP, curses.KEY_BTAB):
            self.liste["secim"] = (self.liste["secim"] - 1) % len(ogeler)
        elif tus in (curses.KEY_DOWN, "\t"):
            self.liste["secim"] = (self.liste["secim"] + 1) % len(ogeler)
        elif tus in ("\n", "\r", curses.KEY_ENTER, " "):
            ogeler[self.liste["secim"]][2]()

    def _olay_bilgi(self, tus):
        b = self.bilgi_d
        if tus in ("\x1b", "q"):
            self.kapat()
        elif tus in (curses.KEY_UP,):
            b["kaydirma"] = max(0, b["kaydirma"] - 1)
        elif tus in (curses.KEY_DOWN,):
            b["kaydirma"] += 1
        elif tus == curses.KEY_PPAGE:
            b["kaydirma"] = max(0, b["kaydirma"] - 10)
        elif tus == curses.KEY_NPAGE:
            b["kaydirma"] += 10
        elif tus in ("\n", "\r", curses.KEY_ENTER):
            if b["dugmeler"]:
                b["dugmeler"][0][1]()
            else:
                self.kapat()

    def _olay_cikis(self, tus):
        if tus == "\x1b" or (isinstance(tus, str) and tus in self.m["hayir_tusu"]):
            self.cikis_iptal()
        elif isinstance(tus, str) and tus in self.m["evet_tusu"]:
            self.cik()
        elif tus in (curses.KEY_LEFT, curses.KEY_RIGHT, "\t", curses.KEY_BTAB):
            self.cikis_secim = 1 - self.cikis_secim
        elif tus in ("\n", "\r", curses.KEY_ENTER, " "):
            if self.cikis_secim == 0:
                self.cik()
            else:
                self.cikis_iptal()

    def _ayar_satirlari(self):
        """[(tür, anahtar)] — tür: 'grup' | 'ayar' | 'eylem' | 'bos' | 'dugmeler'."""
        satirlar = []
        for tur, sayfa in (("ayar", AYAR_SAYFASI), ("eylem", AYAR_EYLEMLERI)):
            for grup, anahtarlar in sayfa:
                if satirlar:
                    satirlar.append(("bos", None))
                satirlar.append(("grup", grup))
                satirlar.extend((tur, a) for a in anahtarlar)
        satirlar.append(("bos", None))
        satirlar.append(("dugmeler", None))
        return satirlar

    def _ayar_satirlari_secilebilir(self):
        return [i for i, (t, _) in enumerate(self._ayar_satirlari())
                if t in ("ayar", "eylem", "dugmeler")]

    def _ayar_eylemi(self, anahtar):
        if anahtar == "ilerleme_sifirla":
            self.mod_ac("sifirla")

    # -- ilerlemeyi sıfırlama ------------------------------------------------------------

    def profil_adi(self):
        return (f"{DILLER[self.dil_kodu]['ad'][self.arayuz]} · "
                f"{DUZENLER[self.duzen.kimlik]['ad'][self.arayuz]}")

    def ilerleme_sifirla(self, tumu):
        """Etkin profilin ya da tüm ilerlemenin kaydını siler; ayarlar sayfasına döner."""
        profil = self.profil_adi()
        self.kaydet()                                   # yedeğe son hâli girsin
        try:
            self.depo.sifirla(None if tumu else self.anahtar)
        except OSError as hata:
            self.ayar_hata = str(hata)
            self.mod = "ayarlar"
            return
        il = self.ilerleme
        self.ilerleme = self.depo.profil(self.anahtar, il.pencere, il.sira, il.olcut, il.hedef_hiz)
        self._son_seviye = seviye_hesapla(self.depo.genel["xp"])[0]
        if self.test:
            self.test = {"bas": None, "dogru": 0, "hata": 0, "sure": self.test["sure"]}
        self.son_vurus = None
        self.satir = ""
        self.sonraki = ""
        self.yeni_satir(tazele=True)
        self.mod = "ayarlar"                            # kaydedilmemiş ayar değişiklikleri kalsın
        self.ayar_hata = None
        self.ayar_bilgi = (self.m["sifirlandi_tumu"] if tumu
                           else self.m["sifirlandi_profil"].format(profil=profil))

    def sifirla_iptal(self):
        self.mod = "ayarlar"

    def _sifirla_dugmeleri(self):
        m = self.m
        return [(m["sifirla_profil"], lambda: self.ilerleme_sifirla(False), ("hata_yazi", "hata")),
                (m["sifirla_tumu"], lambda: self.ilerleme_sifirla(True), ("hata_yazi", "hata")),
                (m["vazgec"], self.sifirla_iptal, ("vurgu_yazi", "vurgu"))]

    def _olay_sifirla(self, tus):
        if tus in ("\x1b", "q"):
            self.sifirla_iptal()
        elif tus in (curses.KEY_LEFT, curses.KEY_BTAB):
            self.sifirla_secim = (self.sifirla_secim - 1) % 3
        elif tus in (curses.KEY_RIGHT, "\t"):
            self.sifirla_secim = (self.sifirla_secim + 1) % 3
        elif tus in ("\n", "\r", curses.KEY_ENTER, " "):
            self._sifirla_dugmeleri()[self.sifirla_secim][1]()

    def _ayar_oynat(self, yon):
        tur, anahtar = self._ayar_satirlari()[self.ayar_secim]
        if tur != "ayar":
            return
        ayar_degistir(self.ayarlar, anahtar, yon, self.temalar)
        self.ayar_hata = None
        if anahtar in CANLI_AYARLAR:
            self._canli_uygula(anahtar)

    def _canli_uygula(self, anahtar):
        if anahtar == "tema":
            self.renkleri_kur()
        elif anahtar in ("fiziksel", "numpad"):
            # düzenin kendisi (ve müfredat) kaydedince değişir; burada yalnızca görünüm
            self.duzen = Duzen(self.duzen.kimlik, self.ayarlar["fiziksel"], self.ayarlar["numpad"])
        elif anahtar.startswith("gosterge") or anahtar in ("tus_araligi_mm", "ekran_genisligi_mm"):
            self.bilgi_zamani = time.monotonic()

    def _olay_ayarlar(self, tus):
        secilebilir = self._ayar_satirlari_secilebilir()
        i = secilebilir.index(self.ayar_secim) if self.ayar_secim in secilebilir else 0
        tur, anahtar = self._ayar_satirlari()[self.ayar_secim]
        self.ayar_bilgi = None
        if tur == "eylem" and tus in ("\n", "\r", curses.KEY_ENTER, curses.KEY_RIGHT, " "):
            self._ayar_eylemi(anahtar)
        elif tus == "\x1b":
            self.ayar_vazgec()
        elif tus in (curses.KEY_UP, curses.KEY_BTAB):
            self.ayar_secim = secilebilir[(i - 1) % len(secilebilir)]
        elif tus in (curses.KEY_DOWN, "\t"):
            self.ayar_secim = secilebilir[(i + 1) % len(secilebilir)]
        elif tus in (curses.KEY_LEFT, "-"):
            self._ayar_oynat(-1)
        elif tus in (curses.KEY_RIGHT, "+", " "):
            self._ayar_oynat(1)
        elif tus == curses.KEY_NPAGE:
            self._ayar_oynat(-10)
        elif tus == curses.KEY_PPAGE:
            self._ayar_oynat(10)
        elif tus == curses.KEY_HOME:
            self.ayar_secim = secilebilir[0]
        elif tus == curses.KEY_END:
            self.ayar_secim = secilebilir[-1]
        elif tus in ("\n", "\r", curses.KEY_ENTER, curses.KEY_F2):
            self.ayar_kaydet()

    def ayar_vazgec(self):
        yedek, self.ayar_yedek = self.ayar_yedek, None
        if yedek:
            self.ayarlar.clear()
            self.ayarlar.update(yedek)
            self.renkleri_kur()
            self.duzen = Duzen(self.ayarlar["klavye"], self.ayarlar["fiziksel"],
                               self.ayarlar["numpad"])
        self.mod_ac("yaz")

    def ayarlari_yaz(self):
        try:
            json_yaz(AYAR_DOSYASI, self.ayarlar)
        except OSError as hata:
            self.mesaj_ver(str(hata), "hata", 8)

    def ayar_kaydet(self):
        yedek = self.ayar_yedek or dict(self.ayarlar)
        yeni = self.ayarlar
        try:
            mufredat(yeni["dil"], Duzen(yeni["klavye"], yeni["fiziksel"], yeni["numpad"]))
        except UyumsuzDuzen as eksik:
            self.ayar_hata = self.m["uyumsuz"].format(
                duzen=DUZENLER[yeni["klavye"]]["ad"][yeni["arayuz"]], eksik=" ".join(str(eksik)))
            return
        self.ayar_yedek = None
        self.ayarlari_yaz()
        if (yeni["klavye"], yeni["dil"]) != (yedek["klavye"], yedek["dil"]):
            self.kaydet()
            self.profili_yukle()
        else:
            self.duzen = Duzen(yeni["klavye"], yeni["fiziksel"], yeni["numpad"])
            il = self.ilerleme
            if yeni["ustalik_penceresi"] != yedek["ustalik_penceresi"]:
                self.pencere_cli = None
                il.pencere = yeni["ustalik_penceresi"]
            il.olcut, il.hedef_hiz = yeni["ustalik_olcutu"], yeni["hedef_hiz"]
            if any(yeni[k] != yedek[k] for k in SATIRI_YENILEYEN):
                self.yeni_satir(tazele=True)
        if yeni["fare"] != yedek["fare"]:
            self.fareyi_kur()
        if self.test and yeni["test_suresi_sn"] != yedek["test_suresi_sn"]:
            self.test["sure"] = yeni["test_suresi_sn"]
        self.renkleri_kur()
        self.mod_ac("yaz")
        self.mesaj_ver(self.m["ayar_kaydedildi"], "bilgi", 3)
        if yeni["acilis_boyutu"] != yedek["acilis_boyutu"]:
            self.pencereyi_ayarla()
        if any(yeni[k] != yedek[k] for k in ("rgb_isik", "rgb_adres", "klavye", "fiziksel",
                                              "numpad")):
            self.rgb_kur()

    def pencereyi_ayarla(self):
        kip = self.ayarlar["acilis_boyutu"]
        if kip == "dokunma":
            return
        self.pencere.uygula(kip, gereken_boyut(self.duzen, len(self.ilerleme.sira),
                                               self._yerlesim_secenekleri(False)))

    def fare_olayi(self):
        try:
            _, x, y, _, durum = curses.getmouse()
        except curses.error:
            return
        tekerlek_yukari = durum & getattr(curses, "BUTTON4_PRESSED", 0)
        tekerlek_asagi = durum & getattr(curses, "BUTTON5_PRESSED", 0)
        if tekerlek_yukari or tekerlek_asagi:
            yon = -1 if tekerlek_yukari else 1
            if self.mod == "ayarlar":
                secilebilir = self._ayar_satirlari_secilebilir()
                i = secilebilir.index(self.ayar_secim) if self.ayar_secim in secilebilir else 0
                self.ayar_secim = secilebilir[max(0, min(len(secilebilir) - 1, i + yon))]
            elif self.mod == "liste":
                self.liste["secim"] = (self.liste["secim"] + yon) % len(self.liste["ogeler"])
            elif self.mod == "bilgi":
                self.bilgi_d["kaydirma"] = max(0, self.bilgi_d["kaydirma"] + 3 * yon)
            return
        if not durum & (curses.BUTTON1_PRESSED | curses.BUTTON1_CLICKED):
            return
        for by, bx0, bx1, eylem in reversed(self.bolgeler):
            if by == y and bx0 <= x < bx1:
                eylem()
                return
        if self.kutu and self.disari:
            x0, y0, x1, y1 = self.kutu
            if not (x0 <= x <= x1 and y0 <= y <= y1):
                self.disari()

    def boyut_degisti(self):
        curses.update_lines_cols()
        self.ekran.clear()
        self.bilgi_zamani = time.monotonic() + 0.25

    def bekleme_suresi(self):
        """Zamanlı bir iş varsa kısa zaman aşımı, yoksa bloklu bekle."""
        simdi = time.monotonic()
        if self.bilgi_zamani and self.bilgi_zamani <= simdi:
            return 0
        bitisler = [t for t in (self.flas_bitis, self.mesaj_bitis, self.bilgi_zamani or 0,
                                self.rgb_deneme or 0) if t > simdi]
        if self.test and self.test["bas"] is not None and self.mod == "yaz":
            bitisler.append(simdi + 0.25)
        if not bitisler:
            return -1
        return max(10, int((min(bitisler) - simdi) * 1000) + 5)

    def _zamanli_isler(self):
        if self.bilgi_zamani and time.monotonic() >= self.bilgi_zamani:
            self.bilgi_zamani = None
            if self.ayarlar["gosterge"] != "kapali":
                self.pencere_bilgisi = self.pencere.bilgi()
                if self.pencere_bilgisi and self.pencere_bilgisi.get("cikis"):
                    self.ekran_mm = ekran_genisligi_mm(self.pencere_bilgisi["cikis"]) or self.ekran_mm
        if self.rgb_deneme and time.monotonic() >= self.rgb_deneme:
            self.rgb_kur(sessiz=True)
        t = self.test
        if (t and t["bas"] is not None and self.mod == "yaz"
                and time.monotonic() - t["bas"] >= t["sure"]):
            self.test_bitir()

    def dongu(self):
        while self.calisiyor:
            self._zamanli_isler()
            self.ciz()
            self.ekran.timeout(self.bekleme_suresi())
            try:
                tus = self.ekran.get_wch()
            except curses.error:
                continue
            except KeyboardInterrupt:
                tus = "\x03"
            self.olay(tus)

    # -- çizim yardımcıları ---------------------------------------------------------------

    def yaz(self, y, x, metin, attr=0):
        guvenli_yaz(self.ekran, y, x, metin, attr)

    def parcalar(self, y, x, parcalar, sinir=None):
        """[(metin, renk_adı, öznitelik)] parçalarını art arda yazar; bitiş x'ini döndürür."""
        for metin, renk, ek in parcalar:
            if sinir is not None:
                metin = metin[:max(0, sinir - x)]
            self.yaz(y, x, metin, (self.cift(renk) if isinstance(renk, str) else renk) | ek)
            x += len(metin)
        return x

    def bolge(self, y, x0, x1, eylem):
        self.bolgeler.append((y, x0, x1, eylem))

    def cizgiler(self, cizgi, attr=None):
        taban = self.cift("cizgi") if attr is None else attr
        for (x, y), ch in cizgi.items():
            self.yaz(y, x, ch, taban)

    def dolgu(self, y0, y1, x0, x1, attr):
        for y in range(y0, y1):
            self.yaz(y, x0, " " * (x1 - x0), attr)

    def kart(self, kutu, baslik=None, sag=None, alt=None):
        """Yuvarlak köşeli kart; sag: [(metin, eylem | None, renk)] başlık çizgisinin sağında."""
        x0, y0, x1, y1 = kutu
        self.cizgiler(kutu_cizgileri([kutu]))
        if baslik:
            self.yaz(y0, x0 + 2, f" {baslik} ", self.cift("baslik") | curses.A_BOLD)
        if sag:
            x = x1 - 1 - sum(len(m) + 2 for m, _, _ in sag)
            for metin, eylem, renk in sag:
                parca = f" {metin} "
                self.yaz(y0, x, parca, self.cift(renk) | (curses.A_BOLD if eylem else 0))
                if eylem and self.mod == "yaz":
                    self.bolge(y0, x, x + len(parca), eylem)
                x += len(parca) + 1
        if alt:
            self.yaz(y1, x0 + 2, f" {alt} ", self.cift("soluk"))

    def gosterge_etkin(self):
        g = self.ayarlar["gosterge"]
        if g == "her_zaman":
            return True
        if g == "kapali":
            return False
        b = self.pencere_bilgisi
        if b:
            return bool(b.get("tam")) or (b.get("g", 0) >= 0.97 * b.get("eg", 1e9))
        return self.pencere.yapilan == ("tam_ekran",)

    def _yerlesim_secenekleri(self, gosterge):
        a = self.ayarlar
        return {"gosterge": gosterge, "panel": a["harf_paneli"], "yazi_boyutu": a["yazi_boyutu"],
                "klavye_boyutu": a["klavye_boyutu"], "sonraki": a["sonraki_satir"],
                "yazi_parmak": a["yazi_parmak"], "tus_stili": a["tus_stili"], "tus_kenar": a["tus_kenar"]}

    # -- çizim ------------------------------------------------------------------------------

    def ciz(self):
        e = self.ekran
        e.erase()
        self.bolgeler = []
        self.kutu = self.disari = None
        h, w = e.getmaxyx()
        simdi = time.monotonic()
        if self.flas_tus is not None and simdi >= self.flas_bitis:
            self.flas_tus = None
        if self.mesaj and self.mesaj_bitis and simdi >= self.mesaj_bitis:
            self.mesaj = None
        hedef = self.hedef
        cozum = self.duzen.cozumle(hedef) if hedef not in (None, " ") else None
        self.hedef_taban = " " if hedef == " " else (cozum[0] if cozum else None)
        self.hedef_shift = self.duzen.shift_tusu(hedef) if cozum else None

        if w < MIN_GENISLIK or h < MIN_YUKSEKLIK:
            self.yerlesim = False
            m = self.m
            satirlar = [m["kucuk1"], m["kucuk2"].format(w=w, h=h, mw=MIN_GENISLIK, mh=MIN_YUKSEKLIK),
                        m["kucuk3"]]
            for i, s in enumerate(satirlar):
                x = max(0, (w - len(s)) // 2)
                self.yaz(h // 2 - 1 + i, x, s,
                         self.cift("baslik") | curses.A_BOLD if i == 0 else self.cift("yazi"))
            self.bolge(h // 2 + 1, 0, w, self.menu_ac)
        else:
            gosterge = self.gosterge_etkin()
            n = len(self.ilerleme.sira)
            d = yerlesim_hesapla(h, w, self.duzen, n, self._yerlesim_secenekleri(gosterge))
            if d is None and gosterge:
                gosterge = False
                d = yerlesim_hesapla(h, w, self.duzen, n, self._yerlesim_secenekleri(False))
            self.yerlesim = d
            self._ciz_ust_cubuk(w)
            if d:
                self._satir_maks_guncelle(min(SATIR_KARAKTER, d["x1"] - 8))
                self._ciz_kartlar(d)
                if gosterge:
                    self._ciz_gostergeler(h, w, d["gosterge_y"])
            else:
                self._satir_maks_guncelle(min(SATIR_KARAKTER, w - 6))
                self._ciz_sade(h, w)
        getattr(self, "_ciz_" + self.mod, lambda h, w: None)(h, w)
        e.refresh()
        self.rgb_guncelle()

    def _ciz_yaz(self, h, w):
        pass

    def _satir_maks_guncelle(self, maks):
        maks = max(20, maks)
        if maks != self.satir_maks:
            self.satir_maks = maks
            if self.konum == 0 and len(self.satir) > maks:
                self.yeni_satir(tazele=True)
            elif len(self.sonraki) > maks:
                self.sonraki = self._satir_uret(self.satir.split()[-1] if self.satir else None)

    def _ciz_ust_cubuk(self, w):
        m = self.m
        zemin = self.cift("ust_yazi", "ust_zemin")
        self.yaz(0, 0, " " * w, zemin)
        x = 1
        ad = f" {UYGULAMA_ADI} "
        self.yaz(0, x, ad, self.cift("vurgu_yazi", "vurgu") | curses.A_BOLD)
        x += len(ad) + 1
        mod_metni = m["modlar"][self.alistirma_modu]
        if self.alistirma_modu == "metin" and self.metin:
            mod_metni += f": {self.metin['ad']}"
        cip = f" {mod_metni} ▾ "
        self.yaz(0, x, cip, self.cift("yazi", "t:notr") | curses.A_BOLD)
        if self.mod == "yaz":
            self.bolge(0, x, x + len(cip), self.mod_listesi)
        x += len(cip) + 1
        if self.ayarlar["rgb_isik"] == "openrgb":
            bagli = self.rgb is not None and self.rgb.bagli
            self.yaz(0, x, " RGB ", self.cift("vurgu_yazi", "dogru" if bagli else "hata") | curses.A_BOLD)
            x += 6
        fiz = {"iso": "ISO", "ansi": "ANSI", "ansi102": "ANSI 102"}[self.duzen.fiziksel]
        profil = (f"{DUZENLER[self.duzen.kimlik]['ad'][self.arayuz]} · {fiz} · "
                  f"{self.dil['ad'][self.arayuz]}")
        dugmeler = [("Esc", m["d_menu"], self.menu_ac), ("F2", m["d_ayarlar"], self._ayarlari_ac),
                    ("F4", m["d_istatistik"], self.istatistik_ac),
                    ("F11", m["d_tam"], self.tam_ekran_degistir), ("F1", m["d_yardim"], self.yardim_ac)]
        sag = w - 1
        for tus, etiket, eylem in dugmeler:
            parca = len(tus) + len(etiket) + 4
            if sag - parca < x + len(profil) + 2:
                break
            sag -= parca
            self.yaz(0, sag, f" {tus} ", self.cift("ust_yazi", "t:notr") | curses.A_BOLD)
            self.yaz(0, sag + len(tus) + 2, f" {etiket} ", zemin)
            if self.mod == "yaz":
                self.bolge(0, sag, sag + parca, eylem)
        if x + len(profil) < sag:
            self.yaz(0, x, profil, self.cift("soluk", "ust_zemin"))

    # -- kartlar -------------------------------------------------------------------------

    def _ciz_kartlar(self, d):
        self._ciz_ozet(d["ozet"], d["oz"])
        self._ciz_yazi_karti(d)
        if d["klavye"]:
            self._ciz_klavye_karti(d)
        if d["grafik"]:
            self._ciz_grafik_karti(d["grafik"])
        if d["panel"]:
            self._ciz_panel(d)

    # özet (keybr tarzı)
    def _degisim(self, simdi, onceki, ondalik=1, yuzde=False):
        if onceki is None:
            return []
        fark = simdi - onceki
        if abs(fark) < 10 ** -ondalik / 2:
            return []
        ok = "↑" if fark > 0 else "↓"
        metin = f"{fark:+.{ondalik}f}"
        if yuzde:
            metin = self.m["yuzde"].format(v=metin)
        return [(f" ({ok}{metin})", "dogru" if fark > 0 else "hata", 0)]

    def _ciz_ozet(self, kutu, oz):
        m = self.m
        x0, y0, x1, y1 = kutu
        self.kart(kutu, m["k_ozet"])
        etiketler = ["e_metrikler", "e_harfler"] + (["e_guncel", "e_dogruluk"] if oz >= 5 else []) \
            + ["e_gunluk"]
        genislik = max(len(m[e]) for e in etiketler) + 1
        icx = x0 + 2 + genislik + 1
        sinir = x1 - 1
        for i, e in enumerate(etiketler):
            y = y0 + 1 + i
            etiket = m[e] + ":"
            self.yaz(y, x0 + 2 + genislik - len(etiket), etiket, self.cift("soluk"))
            getattr(self, "_ozet_" + e[2:])(y, icx, sinir)

    def _ozet_metrikler(self, y, x, sinir):
        m, il = self.m, self.ilerleme
        turlar = il.turlar
        son = turlar[-1] if turlar else None
        once = turlar[-2] if len(turlar) > 1 else None
        if son:
            puan = son.get("puan", puan_hesapla(son["dbk"], son["dogruluk"], il.acik_sayisi))
            puan_once = (once.get("puan", puan_hesapla(once["dbk"], once["dogruluk"], il.acik_sayisi))
                         if once else None)
            p = ([(f"{m['m_hiz']}: ", "soluk", 0), (f"{son['dbk']:.1f} {m['dbk']}", "baslik", curses.A_BOLD)]
                 + self._degisim(son["dbk"], once and once["dbk"])
                 + [("  ·  ", "cizgi", 0), (f"{m['m_dogruluk']}: ", "soluk", 0),
                    (self.yuzde(son["dogruluk"], 2), "baslik", curses.A_BOLD)]
                 + self._degisim(son["dogruluk"], once and once["dogruluk"], 2)
                 + [("  ·  ", "cizgi", 0), (f"{m['m_puan']}: ", "soluk", 0),
                    (f"{puan}", "baslik", curses.A_BOLD)]
                 + self._degisim(puan, puan_once, 0))
        else:
            p = [(f"{m['m_hiz']}: ", "soluk", 0), (m["yok"], "baslik", 0), ("  ·  ", "cizgi", 0),
                 (f"{m['m_dogruluk']}: ", "soluk", 0), (m["yok"], "baslik", 0), ("  ·  ", "cizgi", 0),
                 (f"{m['m_puan']}: ", "soluk", 0), (m["yok"], "baslik", 0)]
        son_x = self.parcalar(y, x, p, sinir)
        # sağda seviye ve XP
        xp = self.depo.genel["xp"]
        seviye, alt, ust = seviye_hesapla(xp)
        seviye_metni = m["seviye"].format(n=seviye)
        xp_metni = m["xp"].format(x=xp)
        cubuk = 10
        toplam = len(seviye_metni) + 1 + cubuk + 1 + len(xp_metni)
        sx = sinir - toplam
        if sx > son_x + 3:
            dolu, bos = cizgi_cubugu((xp - alt) / max(1, ust - alt), cubuk)
            self.parcalar(y, sx, [(seviye_metni + " ", "baslik", curses.A_BOLD),
                                  ("━" * dolu, "vurgu", 0), ("━" * bos, "cizgi", 0),
                                  (" " + xp_metni, "soluk", 0)])

    def _cip_rengi(self, harf, acik_mi):
        il = self.ilerleme
        if not acik_mi:
            return "t:notr", "soluk"
        if harf == il.guncel_harf and not il.ustalasti_mi(harf):
            return "t:vurgu2", "yt:vurgu2"
        if not il.gecmis[harf]:
            return "t:notr", "yt:notr"
        seviye = 5 if il.ustalasti_mi(harf) else min(4, int(il.guven(harf) * 5))
        return f"cip:{seviye}", f"ycip:{seviye}"

    def _ozet_harfler(self, y, x, sinir):
        il = self.ilerleme
        n = len(il.sira)
        alan = sinir - x
        adim = 4 if n * 4 - 1 <= alan else (3 if n * 3 - 1 <= alan else 2)
        for j, harf in enumerate(il.sira):
            cx = x + j * adim
            if cx + adim - 1 > sinir:
                break
            dolgu, yazi = self._cip_rengi(harf, j < il.acik_sayisi)
            etiket = buyuk_harf(harf, self.dil_kodu)
            metin = f" {etiket} " if adim == 4 else (f" {etiket}" if adim == 3 else etiket)
            self.yaz(y, cx, metin, self.cift(yazi, dolgu) | curses.A_BOLD)
            if self.mod == "yaz":
                self.bolge(y, cx, cx + adim, lambda h=harf: self.harf_detay(h))

    def _ozet_guncel(self, y, x, sinir):
        m, il = self.m, self.ilerleme
        harf = il.guncel_harf
        dolgu, yazi = self._cip_rengi(harf, True)
        cip = f" {buyuk_harf(harf, self.dil_kodu)} "
        self.yaz(y, x, cip, self.cift(yazi, dolgu) | curses.A_BOLD)
        if self.mod == "yaz":
            self.bolge(y, x, x + 3, lambda: self.harf_detay(harf))
        turlar = il.harf_turlari.get(harf, [])
        hedef = self.ayarlar["hedef_hiz"]
        if not turlar:
            self.parcalar(y, x + 4, [(m["veri_yok"], "soluk", 0)], sinir)
            return
        son, en_iyi = turlar[-1], max(turlar)
        p = [(f"{m['son_hiz']}: ", "soluk", 0), (f"{son:.1f} {m['dbk']}", "baslik", curses.A_BOLD),
             (f" ({self.yuzde(100 * son / hedef)})", "soluk", 0), ("  ·  ", "cizgi", 0),
             (f"{m['en_iyi']}: ", "soluk", 0), (f"{en_iyi:.1f} {m['dbk']}", "baslik", curses.A_BOLD),
             (f" ({self.yuzde(100 * en_iyi / hedef)})", "soluk", 0)]
        oran = il.ogrenme_hizi(harf)
        if oran is not None:
            p += [("  ·  ", "cizgi", 0), (f"{m['ogrenme']}: ", "soluk", 0),
                  (f"{oran:+.1f} {m['tur_basina']}", "dogru" if oran >= 0 else "hata", curses.A_BOLD)]
        self.parcalar(y, x + 4, p, sinir)

    def _ozet_dogruluk(self, y, x, sinir):
        m, il = self.m, self.ilerleme
        seri = il.dogruluk_serisi()
        if seri >= 2:
            p = [("✦ ", "vurgu", curses.A_BOLD),
                 (m["seri_var"].format(n=seri, e=DOGRULUK_SERISI_ESIGI), "yazi", 0)]
        else:
            p = [(m["seri_yok"], "soluk", 0)]
        son_x = self.parcalar(y, x, p, sinir)
        gun = gun_serisi(self.depo.genel["gunluk"], self.ayarlar["gunluk_hedef_dk"] * 60)
        metin = m["gun_serisi"].format(n=gun)
        if sinir - len(metin) > son_x + 3:
            self.yaz(y, sinir - len(metin), metin,
                     self.cift("uyari" if gun else "soluk") | (curses.A_BOLD if gun else 0))

    def _ozet_gunluk(self, y, x, sinir):
        m = self.m
        hedef = self.ayarlar["gunluk_hedef_dk"]
        dakika = self._bugun_sn() / 60
        if not hedef:
            self.parcalar(y, x, [(m["gunluk_kapali"].format(d=round(dakika)), "yazi", 0)], sinir)
            return
        oran = min(1.0, dakika / hedef)
        metin = m["gunluk_metin"].format(y=round(100 * oran), d=round(dakika), h=hedef)
        son_x = self.parcalar(y, x, [(metin, "baslik" if oran >= 1 else "yazi", 0)], sinir)
        cubuk = min(40, sinir - son_x - 3)
        if cubuk >= 6:
            dolu, bos = cizgi_cubugu(oran, cubuk)
            self.parcalar(y, son_x + 2, [("━" * dolu, "dogru" if oran >= 1 else "vurgu", 0),
                                         ("━" * bos, "cizgi", 0)])

    # yazı kartı
    def _ciz_yazi_karti(self, d):
        m = self.m
        x0, y0, x1, y1 = d["yazi"]
        baslik = f"{m['k_yazi']} · {m['modlar'][self.alistirma_modu]}"
        t = self.test
        sag = []
        if t:
            kalan = t["sure"] if t["bas"] is None else max(0, t["sure"] - (time.monotonic() - t["bas"]))
            if self.duraklama is not None and t["bas"] is not None:
                kalan = max(0, t["sure"] - (self.duraklama - t["bas"]))
            sure = f"{int(kalan) // 60}:{int(kalan) % 60:02d}"
            baslik += f" · {sure}"
        sag = [("A−", lambda: self.yazi_boyutu_degistir(-1), "yazi"),
               (self.deger_adi(d["yb"]), None, "soluk"),
               ("A+", lambda: self.yazi_boyutu_degistir(1), "yazi")]
        self.kart(d["yazi"], baslik, sag)
        genislik = x1 - x0 - 1
        y = y0 + 1
        if t and t["bas"] is None and not self.mesaj:
            metin = m["test_hazir"]
            self.yaz(y, x0 + 1 + (genislik - len(metin)) // 2, metin, self.cift("uyari") | curses.A_BOLD)
        else:
            self._ciz_mesaj(y, x0 + 1, genislik)
        y += 2 + d["yazi_a"]
        if d["yb"] in ("buyuk", "dev"):
            self._ciz_buyuk_satir(y, x0 + 1, genislik, 1 if d["yb"] == "buyuk" else 2)
        else:
            self._ciz_calisma(y, x0 + 1, genislik, aralikli=d["yb"] == "normal")
        y += YAZI_SATIRLARI[d["yb"]]
        if d["sonraki"]:
            if self.ayarlar["sonraki_satir"]:
                self._ciz_sonraki(y, x0 + 1, genislik, aralikli=d["yb"] != "kucuk")
            y += 1
        if d["parmak"] == "cip":
            self._ciz_el_cipleri(y + 1, x0 + 1, genislik)
        elif d["parmak"] == "gosterge":
            konumlar = yazi_gosterge_konumlari(self.duzen, genislik)
            self._ciz_gosterge_seridi(y + 1, {p: x0 + 1 + x for p, x in konumlar.items()})
        y += YAZI_PARMAK_SATIRI[d["parmak"]]
        y += 1 + d["yazi_b"]
        self._ciz_ipucu(y, x0 + 1, genislik)
        if t and t["bas"] is not None:            # test ilerleme çizgisi alt kenarda
            gecen = (self.duraklama or time.monotonic()) - t["bas"]
            dolu, _ = cizgi_cubugu(gecen / t["sure"], x1 - x0 - 3)
            self.yaz(y1, x0 + 2, "━" * dolu, self.cift("vurgu"))

    def _ciz_mesaj(self, y, x, genislik):
        if self.mesaj:
            renk = {"hata": "hata", "bilgi": "dogru", "uyari": "uyari"}.get(self.mesaj_tur, "yazi")
            metin, attr = self.mesaj, self.cift(renk) | curses.A_BOLD
        else:
            metin, attr = self._durum_mesaji(), self.cift("soluk")
        metin = metin[:genislik - 2]
        self.yaz(y, x + max(0, (genislik - len(metin)) // 2), metin, attr)

    def _karakter_rengi(self, i):
        c = self.satir[i]
        if i < self.konum:
            if c == " ":
                return "cizgi", None, 0
            return ("hata" if i in self.hatalar else "dogru"), None, 0
        if i == self.konum:
            if self.konumda_hata:
                return "hata_yazi", "hata", curses.A_BOLD
            return "vurgu_yazi", "vurgu", curses.A_BOLD
        return ("soluk", None, 0) if c == " " else ("baslik", None, curses.A_BOLD)

    def _ciz_calisma(self, y, sol, genislik, aralikli=True):
        """Satırı ortalar; istenirse ve yer varsa harfler arasına boşluk koyar."""
        n = len(self.satir)
        adim = 2 if aralikli and 2 * n + 2 <= genislik - 4 else 1
        alan = (genislik - 4) // adim
        bas = 0
        if n > alan:
            bas = min(max(0, self.konum - alan // 2), n - alan)
        gorunen = min(n, alan)
        x0 = sol + (genislik - (gorunen * adim - (adim - 1))) // 2
        for i in range(bas, bas + gorunen):
            c = self.satir[i]
            on, arka, ek = self._karakter_rengi(i)
            attr = (self.cift(on, arka) if arka else self.cift(on)) | ek
            self.yaz(y, x0 + (i - bas) * adim, "·" if c == " " else c, attr)

    def _ciz_buyuk_satir(self, y, sol, genislik, olcek):
        """Piksel yazı tipiyle büyük satır: imleç çevresindeki pencere görünür."""
        adim = (GLIF_G + 1) * olcek
        alan = max(1, (genislik - 2) // adim)
        n = len(self.satir)
        bas = 0
        if n > alan:
            bas = min(max(0, self.konum - alan // 3), n - alan)
        gorunen = min(n, alan)
        x0 = sol + (genislik - gorunen * adim) // 2
        for i in range(bas, bas + gorunen):
            c = self.satir[i]
            on, arka, ek = self._karakter_rengi(i)
            cx = x0 + (i - bas) * adim
            if arka:                                    # imleç: glifin çevresi dolu
                self.dolgu(y, y + YAZI_SATIRLARI["buyuk" if olcek == 1 else "dev"], cx - 1,
                           cx + GLIF_G * olcek + 1, self.cift(on, arka))
            attr = (self.cift(on, arka) if arka else self.cift(on)) | ek
            hucreler = glif_hucreleri(c, olcek)
            if c == " ":
                attr = self.cift("cizgi", arka) if arka else self.cift("cizgi")
            for r, satir in enumerate(hucreler):
                for k, ch in enumerate(satir):
                    if ch != " ":
                        self.yaz(y + r, cx + k, ch, attr)

    def _ciz_sonraki(self, y, sol, genislik, aralikli=True):
        metin = self.sonraki.replace(" ", "·")
        if aralikli and 2 * len(metin) + 2 <= genislik - 4:
            metin = " ".join(metin)
        metin = metin[:genislik - 4]
        self.yaz(y, sol + (genislik - len(metin)) // 2, metin, self.cift("cizgi"))

    def _ciz_ipucu(self, y, x, genislik):
        hedef = self.hedef
        if hedef is None:
            return
        m = self.m
        parmak = self.duzen.parmak(hedef)
        tus = f" {self.tus_adi(hedef)} "
        tarif = self.parmak_tarifi(parmak) if parmak else ""
        shift = ""
        if self.hedef_shift:
            shift_parmak = self.duzen.tus_adi(self.hedef_shift).parmak
            shift = "  ·  " + m["shift_ile"].format(parmak=self.parmak_adi(shift_parmak))
        toplam = len(m["siradaki_tus"]) + 1 + len(tus) + 3 + len(tarif) + len(shift)
        x += max(0, (genislik - toplam) // 2)
        x = self.parcalar(y, x, [(m["siradaki_tus"] + " ", "soluk", 0)])
        self.yaz(y, x, tus, self.cift("yt:" + parmak[1], "t:" + parmak[1]) | curses.A_BOLD
                 if parmak else self.cift("vurgu_yazi", "vurgu"))
        x += len(tus)
        self.parcalar(y, x, [(" → ", "soluk", 0),
                             (tarif, "p:" + parmak[1] if parmak else "yazi", curses.A_BOLD),
                             (shift, "uyari", 0)])

    # klavye kartı: tuş başlığı görünümü (çizgisiz, yumuşak renkler)
    def _ciz_klavye_karti(self, d):
        m = self.m
        x0, y0, x1, y1 = d["klavye"]
        isi = self.ayarlar["klavye_gorunumu"] == "isi"
        sag = [(m["k_isi"].split(" · ")[1] if isi else m["degerler"]["parmak"],
                self.isi_haritasi_degistir, "soluk"),
               (self.deger_adi(self.ayarlar["klavye_boyutu"]), self.klavye_boyutu_degistir, "soluk")]
        self.kart(d["klavye"], m["k_isi"] if isi else m["k_klavye"], sag)
        genislik = x1 - x0 - 1
        kx = x0 + 1 + (genislik - d["kb_w"]) // 2
        ky = y0 + 1 + d["kl_ust"]
        self._ciz_klavye(kx, ky, d["u"], d["hk"], d["ek"])
        self._ciz_el_cipleri(ky + d["kb_h"] + 1 + d["kl_alt"], x0 + 1, genislik)

    def _tus_renk(self, tus, acik):
        """(dolgu, yazı, öznitelik) renk adları."""
        c = tus.karakter
        if self.flas_tus is not None and c == self.flas_tus and not tus.numpad:
            return "hata", "hata_yazi", curses.A_BOLD
        if c is not None and c == self.hedef_taban and not tus.numpad:
            return "vurgu", "vurgu_yazi", curses.A_BOLD
        if self.hedef_shift and tus.ad == self.hedef_shift:
            return "t:vurgu2", "yt:vurgu2", curses.A_BOLD
        parmak = tus.parmak
        if c is not None and (c == " " or c in acik) and not tus.numpad:
            if self.ayarlar["klavye_gorunumu"] == "isi" and c != " ":
                son = self.ilerleme.son_pencere(c)
                if not son:
                    return "t:notr", "yt:notr", 0
                oran = sum(son) / len(son)
                ad = "dogru" if oran >= 0.95 else ("uyari" if oran >= 0.8 else "hata")
                return "isi:" + ad, "yisi:" + ad, curses.A_BOLD
            return "t:" + parmak[1], "yt:" + parmak[1], curses.A_BOLD
        if c is not None and c in self.ilerleme.gecmis and parmak:
            return "t:notr", "p:" + parmak[1], 0          # kilitli harf: parmak renginde yazı
        return "t:notr", "yt:notr", 0

    def _tus_etiketi(self, tus, ic):
        if tus.karakter and tus.ad not in TUS_ETIKETLERI:
            return buyuk_harf(tus.karakter, self.duzen.dil)
        secenekler = TUS_ETIKETLERI.get(tus.ad, {})
        liste = secenekler.get(self.arayuz) or secenekler.get("*") or [tus.ad]
        for etiket in liste:
            if len(etiket) <= ic:
                return etiket
        return ""

    def _kenar_yaz(self, y, x0, x1, renk, sekizde):
        """Tuşun alt kenarının bir satırı: üstten sekizde-birlik kısım renkli.

        Yalnızca üst bloklar (▔ ▀ █) kullanılır: ters renkli alt bloklar bazı
        terminallerde (ör. Konsole) hücrenin altında ince bir renk şeridi bırakır.
        """
        if sekizde <= 0 or x1 <= x0:
            return
        if sekizde >= 8:                          # tam satır: arka planla doldur (█ iz bırakabilir)
            self.yaz(y, x0, " " * (x1 - x0), self.cift("yazi", renk))
            return
        self.yaz(y, x0, ("▀" if sekizde >= 4 else "▔") * (x1 - x0), self.cift(renk, "zemin"))

    def _ciz_klavye(self, kx, ky, u, hk, ek=1):
        acik = set(self.ilerleme.acik_harfler)
        stil = self.ayarlar["tus_stili"]
        kenar = 0 if stil == "yuzen" else self.ayarlar["tus_kenar"]
        kutular = self.duzen.tus_kutulari(kx, ky, u, hk, ek)
        alt_enter = None
        if self.duzen.iso:
            alt_enter = next(((x0, y0, x1, y1) for k, x0, y0, x1, y1 in kutular
                              if k.ad == "enter" and k.satir == 2), None)
        for k, x0, y0, x1, y1 in kutular:
            dolgu, yazi, ozn = self._tus_renk(k, acik)
            govde = self.cift(yazi, dolgu) | ozn
            self.dolgu(y0, y1, x0, x1, govde)
            kenar_rengi = self.dudak(dolgu) if stil == "derinlik" else dolgu
            birlesik = alt_enter and k.ad == "enter" and k.satir == 1
            kenar_sonu = alt_enter[0] if birlesik else x1
            for r in range(ek):
                if birlesik:                      # ISO Enter'ın iki parçası arasında gövde
                    self.dolgu(y1 + r, y1 + r + 1, kenar_sonu, x1, govde)
                self._kenar_yaz(y1 + r, x0, kenar_sonu, kenar_rengi, kenar - 8 * r)
            if alt_enter and k.ad == "enter" and k.satir == 2:
                continue                                # etiket üst parçada
            ic = x1 - x0
            orta = x0 + (ic - 1) // 2
            yuk = y1 - y0
            if k.karakter and k.ad not in TUS_ETIKETLERI:
                etiket = self._tus_etiketi(k, ic)
                ust = self.duzen.shift_tersi.get(k.karakter) if not k.numpad else None
                if ust and not ust.isalpha() and yuk >= 2:
                    self.yaz(y0, orta, ust, self.cift("soluk" if dolgu == "t:notr" else yazi, dolgu))
                    self.yaz(y0 + 1, orta, etiket, govde)
                else:
                    ly = y0 + (yuk - 1) // 2
                    cikinti = k.karakter in self.duzen.cikintilar and not k.numpad
                    self.yaz(ly, orta, etiket, govde | (curses.A_UNDERLINE if cikinti and yuk == 1 else 0))
                    if cikinti and yuk >= 2:
                        self.yaz(y1 - 1, orta, "•", govde)
            else:
                etiket = self._tus_etiketi(k, ic - 2)
                ly = y0 + (yuk - 1) // 2
                self.yaz(ly, x0 + (ic - len(etiket)) // 2, etiket, govde)

    def _ciz_el_cipleri(self, y, x, genislik):
        m = self.m
        hedef = self.hedef
        aktif = self.duzen.parmak(hedef) if hedef is not None else None
        shift_parmak = (self.duzen.tus_adi(self.hedef_shift).parmak if self.hedef_shift else None)
        tamlar = [m[a.lower()] if p is None else m["parmak_adlari"][p[1]] for a, p in EL_CIPLERI]
        metinler = tamlar
        if sum(len(t) + 3 for t in tamlar) > genislik:
            metinler = [m[a.lower()][:1] if p is None else m["parmak_kisa"][p[1]][:4]
                        for a, p in EL_CIPLERI]
        for (ad, parmak), metin, (cx, cg) in zip(EL_CIPLERI, metinler, el_cipleri(genislik, metinler)):
            cx += x
            if parmak is None:
                self.yaz(y, cx + 1, metin, self.cift("soluk") | curses.A_BOLD)
                continue
            if parmak == aktif:
                attr = self.cift("tus_yazi", "p:" + parmak[1]) | curses.A_BOLD
            elif parmak == shift_parmak:
                attr = self.cift("yt:vurgu2", "t:vurgu2") | curses.A_BOLD
            else:
                attr = self.cift("yt:" + parmak[1], "t:" + parmak[1])
            self.yaz(y, cx, f" {metin} ", attr)

    def _ciz_grafik_karti(self, kutu):
        m = self.m
        x0, y0, x1, y1 = kutu
        self.kart(kutu, m["k_grafik"].format(n=len(self.ilerleme.turlar)),
                  [(m["grafik_aciklama"], None, "soluk")])
        self._ciz_grafik(y0 + 1, x0 + 1, x1 - x0 - 1, y1 - y0 - 1)

    def _ciz_grafik(self, y, x, genislik, yukseklik):
        """Son turların hızı (çubuk yüksekliği) ve doğruluğu (çubuk rengi)."""
        turlar = self.ilerleme.turlar
        if not turlar:
            metin = self.m["grafik_bos"]
            self.yaz(y + yukseklik // 2, x + max(0, (genislik - len(metin)) // 2), metin,
                     self.cift("soluk"))
            return
        eksen = 6
        alan = genislik - eksen - 3
        adim = 3 if len(turlar) * 3 <= alan else (2 if len(turlar) * 2 <= alan else 1)
        goster = turlar[-(alan // adim):]
        ust = max(10, max(t["dbk"] for t in goster) * 1.1)
        for i, etiket in ((0, ust), (yukseklik - 1, 0)):
            self.yaz(y + i, x + 1, f"{etiket:>4.0f}", self.cift("soluk"))
        for i in range(yukseklik):
            self.yaz(y + i, x + eksen, "┤" if i in (0, yukseklik - 1) else "│", self.cift("cizgi"))
        bas = x + eksen + 2
        for j, t in enumerate(goster):
            renk = ("dogru" if t["dogruluk"] >= 97 else
                    "uyari" if t["dogruluk"] >= 90 else "hata")
            sekizde = round(t["dbk"] / ust * yukseklik * 8)
            cx = bas + j * adim
            for i in range(yukseklik):
                dolu = sekizde - (yukseklik - 1 - i) * 8
                if dolu <= 0:
                    continue
                ch = "█" if dolu >= 8 else "▁▂▃▄▅▆▇"[dolu - 1]
                self.yaz(y + i, cx, ch * max(1, adim - 1), self.cift(renk))

    def _ciz_panel(self, d):
        """Sağ kart: tüm harfler açılış sırasıyla; kilitliler sönük, yüzdeler sağa hizalı."""
        il, m = self.ilerleme, self.m
        x0, y0, x1, y1 = d["panel"]
        self.kart(d["panel"], m["k_guven"], alt=m["son_n"].format(n=il.pencere))
        cubuk, satir_say = d["cubuk"], d["satir_say"]
        sutun_g = cubuk + 11 + 1
        for i in range(1, d["alt_sutun"]):
            sx = x0 + i * sutun_g
            for yy in range(y0 + 1, y1):
                self.yaz(yy, sx, "│", self.cift("cizgi"))
        if d["tek"] and il.acik_sayisi < len(il.sira):
            self.yaz(y0 + 1 + il.acik_sayisi, x0 + 2, "╌" * (x1 - x0 - 3), self.cift("cizgi"))
        for j, harf in enumerate(il.sira):
            acik = j < il.acik_sayisi
            satir = j % satir_say
            if d["tek"] and not acik:
                satir += 1                                   # ayırıcı çizginin altı
            sx = x0 + 2 + (j // satir_say) * sutun_g
            sy = y0 + 1 + satir
            p = self.duzen.parmak(harf)
            harf_rengi = self.cift("p:" + p[1]) if p else self.cift("yazi")
            if self.mod == "yaz":
                self.bolge(sy, sx, sx + cubuk + 10, lambda h=harf: self.harf_detay(h))
            if not acik:
                siradaki = j == il.acik_sayisi
                self.yaz(sy, sx, harf, harf_rengi | (curses.A_BOLD if siradaki else curses.A_DIM))
                self.yaz(sy, sx + 2, "·" * cubuk, self.cift("cizgi"))
                self.yaz(sy, sx + 3 + cubuk, m["yok"].rjust(4), self.cift("cizgi"))
                if siradaki:
                    self.yaz(sy, sx + 8 + cubuk, "›", self.cift("uyari") | curses.A_BOLD)
                continue
            guven = il.guven(harf)
            usta = il.ustalasti_mi(harf)
            renk = "dogru" if usta else ("uyari" if guven >= 0.5 else "hata")
            dolu, kalan = cizgi_cubugu(guven, cubuk)
            self.yaz(sy, sx, harf, harf_rengi | curses.A_BOLD)
            self.yaz(sy, sx + 2, "━" * dolu, self.cift(renk))
            self.yaz(sy, sx + 2 + dolu, "━" * kalan, self.cift("cizgi"))
            self.yaz(sy, sx + 3 + cubuk, self.yuzde(guven * 100).rjust(4),
                     self.cift("dogru") | curses.A_BOLD if usta else self.cift("yazi"))
            if usta:
                self.yaz(sy, sx + 8 + cubuk, "✓", self.cift("dogru") | curses.A_BOLD)

    def _ciz_gostergeler(self, h, w, y):
        """Ekranın en altında, parmakların fiziksel hizasında göstergeler."""
        self._ciz_gosterge_seridi(y, gosterge_konumlari(self.duzen, w, self.ayarlar,
                                                        self.pencere_bilgisi, self.ekran_mm))

    def _ciz_gosterge_seridi(self, y, konumlar):
        """Üç satırlık şerit: yön ve harf, parmak adı, parmak çubuğu (basılacak parmak vurgulu)."""
        hedef = self.hedef
        aktif = self.duzen.parmak(hedef) if hedef is not None else None
        hedef_tus = self.duzen.tus(self.hedef_taban) if self.hedef_taban not in (None, " ") else None
        shift_parmak = (self.duzen.tus_adi(self.hedef_shift).parmak if self.hedef_shift else None)
        ana_parmaklar = [PARMAK_ORTA[i] for i in ANA_SIRA_INDEKSLERI]
        for parmak, x in konumlar.items():
            tur = parmak[1]
            etkin = (aktif == parmak) or (aktif == BASPARMAK and tur == "basparmak")
            genislik = 5
            if etkin:
                blok = self.cift("p:" + tur) | curses.A_BOLD
                self.yaz(y + 2, x - 3, "▀" * (genislik + 2), self.cift("vurgu") | curses.A_BOLD)
                kisa = self.m["parmak_kisa"][tur]
                self.yaz(y + 1, x - len(kisa) // 2, kisa, blok)
                if hedef_tus is not None and parmak in ana_parmaklar:
                    ana = self.duzen.tus(self.duzen.ana_tuslar[ana_parmaklar.index(parmak)])
                    ok = ok_isareti(hedef_tus.merkez - ana.merkez, hedef_tus.satir - ana.satir)
                    self.yaz(y, x - 1, f"{ok} {hedef}", self.cift("vurgu") | curses.A_BOLD)
                elif hedef == " ":
                    etiket = self.m["bosluk"]
                    self.yaz(y, x - len(etiket) // 2, etiket, self.cift("vurgu") | curses.A_BOLD)
            elif parmak == shift_parmak:
                self.yaz(y + 2, x - genislik // 2, "▀" * genislik, self.cift("t:vurgu2"))
                self.yaz(y + 1, x - 2, "⇧ Shift", self.cift("uyari") | curses.A_BOLD)
            else:
                self.yaz(y + 2, x - genislik // 2, "▄" * genislik, self.cift("t:" + tur))
                if tur != "basparmak":                    # işaret parmaklarına çok yakın
                    kisa = self.m["parmak_kisa"][tur]
                    self.yaz(y + 1, x - len(kisa) // 2, kisa, self.cift("soluk"))

    # -- sade düzen (küçük terminaller) ---------------------------------------------------

    def _ciz_sade(self, h, w):
        il, m = self.ilerleme, self.m
        y = 1
        t = il.turlar[-1] if il.turlar else None
        s = il.siradaki_harf
        sira = f"{s} ({self.parmak_adi(self.duzen.parmak(s))})" if s else m["yok"]
        self.yaz(y, 1, f"{m['e_harfler']}: {il.acik_sayisi}/{len(il.sira)} · {sira}",
                 self.cift("yazi"))
        metin = (f"{m['m_hiz']} {t['dbk']:.0f} {m['dbk']} · {m['m_dogruluk']} "
                 f"{self.yuzde(t['dogruluk'])}") if t else ""
        self.yaz(y + 1, 1, metin, self.cift("soluk"))
        self._ciz_mesaj(y + 2, 0, w)
        self.cizgiler(kutu_cizgileri([(1, y + 3, w - 2, y + 5)]))
        self._ciz_calisma(y + 4, 2, w - 4)
        self._ciz_ipucu(y + 6, 0, w)
        satirlar, kaymalar = self.duzen.harf_satirlari()
        acik = set(il.acik_harfler)
        kx = (w - 51) // 2
        ky = y + 8
        for r, (tuslar, kayma) in enumerate(zip(satirlar, kaymalar)):
            for i, c in enumerate(tuslar):
                k = self.duzen.tus(c)
                dolgu, yazi, ek = self._tus_renk(k, acik)
                self.yaz(ky + r, kx + kayma + i * 4, f" {buyuk_harf(c, self.duzen.dil)} ",
                         self.cift(yazi, dolgu) | ek)
        bosluk = self.duzen.tus(" ")
        dolgu, yazi, ek = self._tus_renk(bosluk, acik)
        self.yaz(ky + 3, kx + 13, m["bosluk"].center(20), self.cift(yazi, dolgu) | ek)
        y0 = ky + 5
        harfler = il.acik_harfler
        satir_max = max(1, h - y0)
        sutun = max(1, (w - 2) // 19)
        if math.ceil(len(harfler) / sutun) > satir_max:
            sutun = math.ceil(len(harfler) / satir_max)
        sutun = max(1, min(sutun, len(harfler)))
        genislik = (w - 2) // sutun
        cubuk = max(2, min(10, genislik - 9))
        satir_say = math.ceil(len(harfler) / sutun)
        for j, harf in enumerate(harfler):
            sy, sx = y0 + j % satir_say, 1 + (j // satir_say) * genislik
            guven = il.guven(harf)
            usta = il.ustalasti_mi(harf)
            dolu, kalan = cizgi_cubugu(guven, cubuk)
            renk = "dogru" if usta else ("uyari" if guven >= 0.5 else "hata")
            p = self.duzen.parmak(harf)
            self.yaz(sy, sx, harf, self.cift("p:" + p[1]) | curses.A_BOLD)
            self.yaz(sy, sx + 2, "━" * dolu, self.cift(renk))
            self.yaz(sy, sx + 2 + dolu, "━" * kalan, self.cift("cizgi"))
            self.yaz(sy, sx + 3 + cubuk, self.yuzde(guven * 100).rjust(4) + ("✓" if usta else ""),
                     self.cift("dogru" if usta else "yazi"))

    # -- pencereler ------------------------------------------------------------------------

    def _ciz_pencere(self, h, w, gen, yuk, baslik, kapat, disari=True):
        """Ortada gölgeli, ✕ düğmeli pencere; (x0, y0, gen, yuk) döndürür."""
        gen, yuk = min(gen, w - 2), min(yuk, h - 2)
        x0, y0 = (w - gen) // 2, (h - yuk) // 2
        if self.tema.get("golge") is not None:
            golge = self.cift("golge", "golge")
            self.dolgu(y0 + 1, y0 + yuk + 1, x0 + gen, x0 + gen + 2, golge)
            self.yaz(y0 + yuk, x0 + 2, " " * gen, golge)
        self.dolgu(y0, y0 + yuk, x0, x0 + gen, self.cift("yazi", "yuzey"))
        self.cizgiler(kutu_cizgileri([(x0, y0, x0 + gen - 1, y0 + yuk - 1)]),
                      attr=self.cift("cizgi", "yuzey"))
        self.yaz(y0, x0 + 2, f" {baslik} ", self.cift("vurgu", "yuzey") | curses.A_BOLD)
        self.yaz(y0, x0 + gen - 5, " ✕ ", self.cift("yazi", "yuzey") | curses.A_BOLD)
        self.bolge(y0, x0 + gen - 5, x0 + gen - 2, kapat)
        self.kutu = (x0, y0, x0 + gen - 1, y0 + yuk - 1)
        self.disari = kapat if disari else None
        return x0, y0, gen, yuk

    def _dugmeler(self, y, x, dugmeler, secili=None):
        for i, (ad, eylem, renk) in enumerate(dugmeler):
            etiket = f"  {ad}  "
            attr = (self.cift(*renk) | curses.A_BOLD if secili is None or secili == i
                    else self.cift("yazi", "t:notr"))
            self.yaz(y, x, etiket, attr)
            self.bolge(y, x, x + len(etiket), eylem)
            x += len(etiket) + 2
        return x

    def _ciz_liste(self, h, w):
        L = self.liste
        ogeler = L["ogeler"]
        sol = max(len(e) for e, _, _ in ogeler)
        sag = max(len(a) for _, a, _ in ogeler)
        gen = max(40, sol + sag + 14, len(L["ipucu"]) + 6)
        x0, y0, gen, yuk = self._ciz_pencere(h, w, gen, len(ogeler) + 6, L["baslik"], self.kapat)
        for i, (etiket, aciklama, eylem) in enumerate(ogeler):
            y = y0 + 2 + i
            secili = i == L["secim"]
            attr = (self.cift("vurgu_yazi", "vurgu") | curses.A_BOLD if secili
                    else self.cift("yazi", "yuzey"))
            self.yaz(y, x0 + 2, " " * (gen - 4), attr)
            self.yaz(y, x0 + 3, f"{'›' if secili else ' '} {etiket}", attr)
            self.yaz(y, x0 + gen - 3 - len(aciklama), aciklama,
                     attr if secili else self.cift("soluk", "yuzey"))

            def tikla(i=i, eylem=eylem):
                L["secim"] = i
                eylem()
            self.bolge(y, x0 + 2, x0 + gen - 2, tikla)
        self.yaz(y0 + yuk - 2, x0 + 3, L["ipucu"][:gen - 6], self.cift("soluk", "yuzey"))

    def _ciz_bilgi(self, h, w):
        b = self.bilgi_d
        satirlar = b["satirlar"]
        gen = b["genislik"] or min(w - 4, max(50, max((sum(len(p[0]) for p in s) for s in satirlar),
                                                     default=0) + 8))
        yuk = min(h - 2, len(satirlar) + 4 + (2 if b["dugmeler"] else 0))
        x0, y0, gen, yuk = self._ciz_pencere(h, w, gen, yuk, b["baslik"], self.kapat)
        gorunur = yuk - 3 - (2 if b["dugmeler"] else 0)
        b["kaydirma"] = max(0, min(b["kaydirma"], len(satirlar) - gorunur))
        for i, parcalar in enumerate(satirlar[b["kaydirma"]:b["kaydirma"] + gorunur]):
            self.parcalar(y0 + 2 + i, x0 + 3,
                          [(t, self.cift(r, "yuzey") if isinstance(r, str) else r, ek)
                           for t, r, ek in parcalar], sinir=x0 + gen - 3)
        if len(satirlar) > gorunur:
            oran = b["kaydirma"] / max(1, len(satirlar) - gorunur)
            self.yaz(y0 + 2 + round(oran * (gorunur - 1)), x0 + gen - 2, "┃",
                     self.cift("soluk", "yuzey"))
        if b["dugmeler"]:
            self._dugmeler(y0 + yuk - 3, x0 + 3,
                           [(ad, e, ("vurgu_yazi", "vurgu") if i == 0 else ("yazi", "t:notr"))
                            for i, (ad, e) in enumerate(b["dugmeler"])])

    def _ciz_cikis(self, h, w):
        m = self.m
        gen = max(42, len(m["cikis_ipucu"]) + 6)
        x0, y0, gen, yuk = self._ciz_pencere(h, w, gen, 8, m["cikis_baslik"], self.cikis_iptal)
        self.yaz(y0 + 2, x0 + 3, m["cikis_metin"], self.cift("yazi", "yuzey"))
        self._dugmeler(y0 + 4, x0 + 3, [(m["evet"], self.cik, ("hata_yazi", "hata")),
                                        (m["hayir"], self.cikis_iptal, ("vurgu_yazi", "vurgu"))],
                       self.cikis_secim)
        self.yaz(y0 + yuk - 2, x0 + 3, m["cikis_ipucu"], self.cift("soluk", "yuzey"))

    def _ciz_sifirla(self, h, w):
        m = self.m
        metin = [s.format(profil=self.profil_adi(), yedek=os.path.basename(self.depo.yol) + ".yedek")
                 for s in m["sifirla_metin"]]
        dugmeler = self._sifirla_dugmeleri()
        dugme_gen = sum(len(ad) + 6 for ad, _, _ in dugmeler)
        gen = max(max(len(s) for s in metin), dugme_gen, len(m["sifirla_ipucu"])) + 6
        x0, y0, gen, yuk = self._ciz_pencere(h, w, gen, len(metin) + 7, m["sifirla_baslik"],
                                             self.sifirla_iptal)
        for i, s in enumerate(metin):
            self.yaz(y0 + 2 + i, x0 + 3, s[:gen - 6], self.cift("yazi", "yuzey"))
        self._dugmeler(y0 + 3 + len(metin), x0 + 3, dugmeler, self.sifirla_secim)
        self.yaz(y0 + yuk - 2, x0 + 3, m["sifirla_ipucu"], self.cift("soluk", "yuzey"))

    def _ayar_degeri(self, anahtar):
        m, v = self.m, self.ayarlar[anahtar]
        if anahtar == "tema":
            return self.temalar.get(v, {}).get("ad", v)
        if anahtar == "klavye":
            return DUZENLER[v]["ad"][self.arayuz]
        if anahtar == "dil":
            return DILLER[v]["ad"][self.arayuz]
        if anahtar == "arayuz":
            return {"tr": "Türkçe", "en": "English"}[v]
        if anahtar == "ustalik_penceresi":
            return m["birim_deneme"].format(v=v)
        if anahtar == "hedef_hiz":
            return m["birim_dbk"].format(v=v)
        if anahtar == "gunluk_hedef_dk":
            return m["birim_dk"].format(v=v) if v else m["degerler"][False]
        if anahtar == "test_suresi_sn":
            return m["birim_sn"].format(v=v)
        if anahtar == "rgb_parlaklik":
            return self.yuzde(v)
        if anahtar == "rgb_adres":
            return v
        if anahtar == "tus_kenar":
            satir = {1: "⅛", 4: "½", 8: "1", 12: "1½", 16: "2"}.get(v, f"{v / 8:g}")
            return m["birim_satir"].format(v=satir)
        if anahtar == "gosterge_kaydirma_mm":
            return m["birim_mm"].format(v=f"{v:+d}")
        if anahtar == "gosterge_olcek":
            return self.yuzde(v)
        if anahtar == "tus_araligi_mm":
            return m["birim_mm"].format(v=f"{v:.1f}")
        if anahtar == "ekran_genisligi_mm":
            if v:
                return m["birim_mm"].format(v=v)
            return (m["birim_otomatik"].format(v=self.ekran_mm) if self.ekran_mm
                    else m["birim_bilinmiyor"])
        return self.deger_adi(v)

    def _ciz_ayarlar(self, h, w):
        m = self.m
        satirlar = self._ayar_satirlari()
        gen = min(w - 4, 78)
        yuk = min(h - 2, len(satirlar) + 6)
        x0, y0, gen, yuk = self._ciz_pencere(h, w, gen, yuk, m["ayar_baslik"], self.ayar_vazgec,
                                             disari=False)
        gorunur = yuk - 5
        if self.ayar_secim < self.ayar_kaydirma:
            self.ayar_kaydirma = self.ayar_secim
        elif self.ayar_secim >= self.ayar_kaydirma + gorunur:
            self.ayar_kaydirma = self.ayar_secim - gorunur + 1
        self.ayar_kaydirma = max(0, min(self.ayar_kaydirma, len(satirlar) - gorunur))
        deger_x = x0 + gen - 3 - 28
        for i in range(self.ayar_kaydirma, min(len(satirlar), self.ayar_kaydirma + gorunur)):
            tur, anahtar = satirlar[i]
            y = y0 + 2 + i - self.ayar_kaydirma
            secili = i == self.ayar_secim
            if tur == "grup":
                self.yaz(y, x0 + 3, buyuk_harf(m["gruplar"][anahtar], self.arayuz),
                         self.cift("soluk", "yuzey") | curses.A_BOLD)
                continue
            if tur == "dugmeler":
                self._dugmeler(y, x0 + 3, [(m["kaydet"], self.ayar_kaydet, ("vurgu_yazi", "vurgu")),
                                           (m["vazgec"], self.ayar_vazgec, ("yazi", "t:notr"))],
                               0 if secili else -1)
                continue
            if tur == "eylem":
                satir_attr = (self.cift("vurgu_yazi", "vurgu") if secili
                              else self.cift("yazi", "yuzey"))
                self.yaz(y, x0 + 2, " " * (gen - 4), satir_attr)
                self.yaz(y, x0 + 3, m["eylem_adlari"][anahtar],
                         satir_attr | (curses.A_BOLD if secili else 0))
                self.yaz(y, deger_x + 2, m["eylem_deger"].center(24), satir_attr | curses.A_BOLD)

                def eyle(i=i, anahtar=anahtar):
                    self.ayar_secim = i
                    self._ayar_eylemi(anahtar)
                self.bolge(y, x0 + 2, x0 + gen - 2, eyle)
                continue
            if tur != "ayar":
                continue
            satir_attr = self.cift("vurgu_yazi", "vurgu") if secili else self.cift("yazi", "yuzey")
            self.yaz(y, x0 + 2, " " * (gen - 4), satir_attr)
            self.yaz(y, x0 + 3, m["ayar_adlari"][anahtar], satir_attr | (curses.A_BOLD if secili else 0))
            deger = self._ayar_degeri(anahtar)[:24]
            self.yaz(y, deger_x, "‹", satir_attr | curses.A_BOLD)
            self.yaz(y, deger_x + 2, deger.center(24), satir_attr | curses.A_BOLD)
            self.yaz(y, deger_x + 27, "›", satir_attr | curses.A_BOLD)

            def sec(i=i):
                self.ayar_secim = i

            def geri(i=i):
                self.ayar_secim = i
                self._ayar_oynat(-1)

            def ileri(i=i):
                self.ayar_secim = i
                self._ayar_oynat(1)
            self.bolge(y, x0 + 2, x0 + gen - 2, sec)
            self.bolge(y, deger_x, deger_x + 13, geri)
            self.bolge(y, deger_x + 14, deger_x + 28, ileri)
        if len(satirlar) > gorunur:
            oran = self.ayar_kaydirma / max(1, len(satirlar) - gorunur)
            self.yaz(y0 + 2 + round(oran * (gorunur - 1)), x0 + gen - 2, "┃",
                     self.cift("soluk", "yuzey"))
        alt = self.ayar_hata or self.ayar_bilgi or m["ayar_ipucu"]
        self.yaz(y0 + yuk - 2, x0 + 3, alt[:gen - 6],
                 self.cift("hata", "yuzey") | curses.A_BOLD if self.ayar_hata
                 else self.cift("dogru", "yuzey") | curses.A_BOLD if self.ayar_bilgi
                 else self.cift("soluk", "yuzey"))
        if self.ayarlar["gosterge"] != "kapali" and self._ayar_satirlari()[self.ayar_secim][1] in (
                "gosterge_kaydirma_mm", "gosterge_olcek", "tus_araligi_mm",
                "ekran_genisligi_mm", "gosterge"):
            self._ciz_gostergeler(h, w, h - GOSTERGE_Y)
            self.yaz(h - GOSTERGE_Y - 1, max(0, (w - len(m["gosterge_bilgi"])) // 2),
                     m["gosterge_bilgi"], self.cift("uyari") | curses.A_BOLD)

    # -- bilgi pencereleri: yardım, harf ayrıntısı, istatistik ----------------------------------

    def yardim_ac(self):
        m = self.m
        yollar = {"ayar": AYAR_DOSYASI, "tema": TEMA_DIZINI, "metin": METIN_DIZINI,
                  "kayit": self.depo.yol}
        satirlar = []
        for sol, sag in m["yardim"]:
            if not sag:
                if satirlar:
                    satirlar.append([])
                satirlar.append([(buyuk_harf(sol, self.arayuz), "soluk", curses.A_BOLD)])
            else:
                satirlar.append([(f"{sol:<20}", "baslik", curses.A_BOLD),
                                 (sag.format(**yollar), "yazi", 0)])
        self.bilgi_ac(m["yardim_baslik"], satirlar)

    def harf_detay(self, harf):
        m, il = self.m, self.ilerleme
        acik = harf in il.acik_harfler
        durum = (m["harf_durum_kilit"] if not acik else
                 m["harf_durum_usta"] if il.ustalasti_mi(harf) else m["harf_durum_calis"])
        hiz = il.hiz(harf)
        turlar = il.harf_turlari.get(harf, [])
        oran = il.ogrenme_hizi(harf)
        dolu, bos = cizgi_cubugu(il.dogruluk_orani(harf), 20)

        def satir(etiket, *parcalar):
            return [(f"{etiket:<22}", "soluk", 0), *parcalar]
        satirlar = [
            satir(m["h_parmak"], (self.parmak_tarifi(self.duzen.parmak(harf)), "p:" +
                                  self.duzen.parmak(harf)[1], curses.A_BOLD)),
            satir(m["h_durum"], (durum, "baslik", curses.A_BOLD)),
            satir(m["h_dogruluk"].format(n=il.pencere), ("━" * dolu, "dogru", 0), ("━" * bos, "cizgi", 0),
                  (" " + self.yuzde(100 * il.dogruluk_orani(harf)), "baslik", curses.A_BOLD)),
            satir(m["h_deneme"], (f"{il.deneme[harf]} / {il.hata[harf]}", "yazi", 0)),
            satir(m["h_hiz"], (f"{hiz:.1f} {m['dbk']}" if hiz else m["yok"], "yazi", 0)),
            satir(m["h_son"], (f"{turlar[-1]:.1f} {m['dbk']}" if turlar else m["yok"], "yazi", 0)),
            satir(m["h_en_iyi"], (f"{max(turlar):.1f} {m['dbk']}" if turlar else m["yok"], "yazi", 0)),
            satir(m["ogrenme"], (f"{oran:+.1f} {m['tur_basina']}" if oran is not None else m["yok"],
                                 "yazi", 0)),
        ]
        if turlar:
            satirlar.append(satir("", (kivilcim(turlar, 30), "dogru", 0)))
        self.bilgi_ac(m["harf_baslik"].format(h=buyuk_harf(harf, self.dil_kodu)), satirlar, genislik=60)

    def _sure_metni(self, saniye):
        dk = int(saniye // 60)
        return self.m["saat_dk"].format(s=dk // 60, d=dk % 60) if dk >= 60 else self.m["dk"].format(d=dk)

    def istatistik_ac(self):
        m, il, g = self.m, self.ilerleme, self.depo.genel
        B = curses.A_BOLD

        def baslik(metin):
            return [(buyuk_harf(metin, self.arayuz), "vurgu", B)]

        def satir(etiket, *parcalar):
            return [(f"{etiket:<22}", "soluk", 0), *parcalar]
        seviye, alt, ust = seviye_hesapla(g["xp"])
        dolu, bos = cizgi_cubugu((g["xp"] - alt) / max(1, ust - alt), 20)
        hedef_sn = self.ayarlar["gunluk_hedef_dk"] * 60
        son10 = il.turlar[-10:]
        satirlar = [baslik(m["ist_genel"]),
                    satir(m["ist_seviye"], (f"{seviye}  ", "baslik", B), ("━" * dolu, "vurgu", 0),
                          ("━" * bos, "cizgi", 0), (f"  {g['xp']}/{ust} XP", "soluk", 0)),
                    satir(m["ist_sure"], (self._sure_metni(g.get("saniye", 0)), "yazi", 0)),
                    satir(m["ist_satir"], (str(g["satir"]), "yazi", 0)),
                    satir(m["ist_vurus"], (str(g["vurus"]), "yazi", 0)),
                    satir(m["ist_en_iyi"], (f"{self.depo.en_iyi('turlar'):.1f} {m['dbk']}", "yazi", 0)),
                    satir(m["ist_ortalama"], (
                        f"{statistics.fmean(t['dbk'] for t in son10):.1f} {m['dbk']} · "
                        f"{self.yuzde(statistics.fmean(t['dogruluk'] for t in son10), 1)}"
                        if son10 else m["ist_yok"], "yazi", 0)),
                    satir(m["ist_seri"], (m["gun"].format(n=gun_serisi(g["gunluk"], hedef_sn)), "yazi", 0),
                          (f"  ({m['ist_en_uzun']}: {m['gun'].format(n=g.get('en_uzun_seri', 0))})",
                           "soluk", 0)),
                    [], baslik(m["ist_gunler"])]
        bugun = datetime.date.today()
        gunler = [bugun - datetime.timedelta(days=i) for i in range(13, -1, -1)]
        dakikalar = [g["gunluk"].get(gun.isoformat(), 0) / 60 for gun in gunler]
        olcek = max(max(dakikalar), self.ayarlar["gunluk_hedef_dk"], 1)
        for gun, dk in zip(gunler, dakikalar):
            dolu, bos = cizgi_cubugu(dk / olcek, 24)
            tuttu = hedef_sn and dk * 60 >= hedef_sn
            satirlar.append([(f"{GUN_ADLARI[self.arayuz][gun.weekday()]} {gun:%d.%m}   ", "soluk", 0),
                             ("━" * dolu, "dogru" if tuttu else "vurgu", 0), ("━" * bos, "cizgi", 0),
                             (f"  {m['dk'].format(d=round(dk))}", "yazi", 0)])
        satirlar += [[], baslik(m["ist_parmaklar"])]
        for parmak in TUM_PARMAKLAR:
            if parmak == BASPARMAK:
                continue
            harfler = [h for h in il.acik_harfler if self.duzen.parmak(h) == parmak]
            denemeler = [x for h in harfler for x in il.son_pencere(h)]
            hizlar = [il.hiz(h) for h in harfler if il.hiz(h)]
            oran = sum(denemeler) / len(denemeler) if denemeler else 0
            dolu, bos = cizgi_cubugu(oran, 16)
            satirlar.append([(f"{self.parmak_adi(parmak):<14}", "p:" + parmak[1], B),
                             ("━" * dolu, "dogru" if oran >= 0.95 else "uyari", 0), ("━" * bos, "cizgi", 0),
                             (f"  {self.yuzde(100 * oran) if denemeler else m['yok']:>5}", "yazi", 0),
                             (f"   {statistics.fmean(hizlar):5.1f} {m['dbk']}" if hizlar else "", "soluk", 0),
                             (f"   {''.join(harfler)}", "soluk", 0)])
        satirlar += [[], baslik(m["ist_harfler"])]
        satir_parca = []
        for h in il.acik_harfler:
            hiz = il.hiz(h)
            satir_parca.append([(f"{h} ", "p:" + self.duzen.parmak(h)[1], B),
                                (f"{self.yuzde(100 * il.dogruluk_orani(h)):>5}", "yazi", 0),
                                (f" {hiz:5.1f}" if hiz else "     —", "soluk", 0), ("     ", "yazi", 0)])
            if len(satir_parca) == 3:
                satirlar.append([p for s in satir_parca for p in s])
                satir_parca = []
        if satir_parca:
            satirlar.append([p for s in satir_parca for p in s])
        satirlar += [[], baslik(m["ist_testler"])]
        if il.testler:
            for t in il.testler[-5:][::-1]:
                zaman = datetime.datetime.fromtimestamp(t.get("t", 0)).strftime("%d.%m %H:%M")
                satirlar.append([(f"{zaman}   ", "soluk", 0), (f"{t['dbk']:5.1f} {m['dbk']}", "baslik", B),
                                 (f"   {self.yuzde(t['dogruluk'], 1)}", "yazi", 0)])
        else:
            satirlar.append([(m["ist_yok"], "soluk", 0)])
        satirlar += [[], baslik(m["ist_rozetler"] + f"  {len(g['rozetler'])}/{len(ROZETLER)}")]
        for kimlik, ad_tr, ad_en, ac_tr, ac_en, _ in ROZETLER:
            kazanildi = kimlik in g["rozetler"]
            ad, aciklama = (ad_tr, ac_tr) if self.arayuz == "tr" else (ad_en, ac_en)
            satirlar.append([("✓ " if kazanildi else "· ", "dogru" if kazanildi else "cizgi", B),
                             (f"{ad:<20}", "baslik" if kazanildi else "soluk", B if kazanildi else 0),
                             (aciklama, "yazi" if kazanildi else "soluk", 0)])
        self.bilgi_ac(m["ist_baslik"], satirlar, genislik=78)


EL_CIPLERI = [("Sol", None), ("serce", _s("serce")), ("yuzuk", _s("yuzuk")), ("orta", _s("orta")),
              ("isaret", _s("isaret")), ("basparmak", BASPARMAK), ("isaret", _g("isaret")),
              ("orta", _g("orta")), ("yuzuk", _g("yuzuk")), ("serce", _g("serce")), ("Sag", None)]


# ---------------------------------------------------------------------------
# Başlatma
# ---------------------------------------------------------------------------


ACILIS_PENCERELERI = {"ayarlar": "_ayarlari_ac", "istatistik": "istatistik_ac",
                      "yardim": "yardim_ac", "menu": "menu_ac", "mod": "mod_listesi"}


def _calistir(ekran, ayarlar, temalar, depo, pencere, uyarilar, pencere_cli, ac=None):
    if hasattr(curses, "set_escdelay"):
        curses.set_escdelay(25)
    curses.raw()                       # Ctrl-C bir tuş olarak gelsin (onay penceresi için)
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    ekran.keypad(True)
    uygulama = Uygulama(ekran, ayarlar, temalar, depo, pencere, uyarilar, pencere_cli)
    if ac:
        getattr(uygulama, ACILIS_PENCERELERI[ac])()
    try:
        uygulama.dongu()
    finally:
        uygulama.kaydet()
        uygulama.rgb_kapat()


def _sinyal_isleyici(sinyal, _cerceve):
    raise SystemExit(128 + sinyal)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog=KIMLIK, description=f"{UYGULAMA_ADI} — terminalde kademeli on parmak klavye eğitimi.")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    ap.add_argument("--pencere", type=int, metavar="N",
                    help="bu oturum için ustalık penceresi (varsayılan: ayarlardaki değer)")
    ap.add_argument("--sifirla", action="store_true", help="tüm ilerlemeyi sıfırla")
    ap.add_argument("--temalar", action="store_true", help="temaları ve dosya yollarını listele")
    ap.add_argument("--ac", choices=list(ACILIS_PENCERELERI), metavar="PENCERE",
                    help="açılışta bu pencereyi aç: " + ", ".join(ACILIS_PENCERELERI))
    ap.add_argument("--kayit", default=KAYIT_DOSYASI, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if args.pencere is not None and args.pencere < 1:
        ap.error("--pencere en az 1 olmalı")

    try:
        for yol in eski_dizinleri_tasi():
            print(f"Önceki sürümün dosyaları taşındı: {yol}")
        yapilandirma_hazirla()
    except OSError as hata:
        print(f"Uyarı: yapılandırma dizini hazırlanamadı: {hata}", file=sys.stderr)
    temalar, tema_uyarilari = temalari_yukle()
    ayarlar, ayar_uyarilari, _ = ayarlari_yukle(temalar=temalar)

    if args.temalar:
        print(f"Ayar dosyası : {AYAR_DOSYASI}")
        print(f"Tema dizini  : {TEMA_DIZINI}")
        print(f"Metin dizini : {METIN_DIZINI}")
        print(f"İlerleme     : {args.kayit}")
        for kimlik, tema in temalar.items():
            isaret = "*" if kimlik == ayarlar["tema"] else " "
            print(f" {isaret} {kimlik:12} {tema.get('ad', '')}")
        for u in tema_uyarilari + ayar_uyarilari:
            print(f"Uyarı: {u}")
        return 0

    if args.sifirla:
        try:
            os.remove(args.kayit)
            print("İlerleme sıfırlandı.")
        except FileNotFoundError:
            print("Sıfırlanacak kayıt yok; baştan başlanıyor.")

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("Bu uygulama bir terminalde çalışmalı.", file=sys.stderr)
        return 1

    locale.setlocale(locale.LC_ALL, "")
    os.environ.setdefault("ESCDELAY", "25")      # set_escdelay olmayan Python'lar için
    depo = IlerlemeDeposu(args.kayit)
    uyarilar = [u for u in (depo.uyari,) if u] + tema_uyarilari + ayar_uyarilari

    pencere = PencereYoneticisi()
    kip = ayarlar["acilis_boyutu"]
    if kip != "dokunma":
        try:
            duzen = Duzen(ayarlar["klavye"], ayarlar["fiziksel"], ayarlar["numpad"])
            n = len(mufredat(ayarlar["dil"], duzen))
        except (KeyError, UyumsuzDuzen):
            duzen, n = Duzen(), len(SIRA)
        secenek = {"panel": ayarlar["harf_paneli"], "yazi_boyutu": ayarlar["yazi_boyutu"],
                   "klavye_boyutu": ayarlar["klavye_boyutu"], "sonraki": ayarlar["sonraki_satir"],
                   "yazi_parmak": ayarlar["yazi_parmak"],
                   "tus_stili": ayarlar["tus_stili"], "tus_kenar": ayarlar["tus_kenar"]}
        pencere.uygula(kip, gereken_boyut(duzen, n, secenek))

    for s in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(s, _sinyal_isleyici)
    try:
        curses.wrapper(_calistir, ayarlar, temalar, depo, pencere, uyarilar, args.pencere, args.ac)
    finally:
        pencere.geri_al()
    print(f"İlerleme kaydedildi: {args.kayit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
