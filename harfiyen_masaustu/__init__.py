"""Harfiyen masaüstü arayüzü (Qt Quick).

Terminal arayüzüyle aynı çekirdeği (harfiyen.Oturum) kullanır: aynı ilerleme dosyası,
aynı ayarlar ve temalar. Gerekenler: PySide6 ve tercihen JetBrains Mono yazı tipi.
"""

import argparse
import json
import os
import sys
import time
import unicodedata

try:
    import harfiyen as hf
except ImportError:                                  # depo içinden çalıştırılınca
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    import harfiyen as hf

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QTimer, QUrl, Property, Signal, Slot
from PySide6.QtGui import QFontDatabase, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine

KOK = os.path.dirname(os.path.realpath(__file__))
AYAR_DOSYASI = os.path.join(hf.AYAR_DIZINI, "masaustu.json")
VARSAYILAN = {
    "zen": False,                     # yalnızca yazı ve parmak çizgileri
    "harf_paneli": False,             # sağdaki harf güveni çekmecesi
    "satir_karakter": 46,             # bir alıştırma satırının en fazla karakteri
}
PARMAK_SIRASI = ("serce", "yuzuk", "orta", "isaret")   # sol elde soldan sağa
BILDIRIM_TURU = {"hata": "hata", "bilgi": "dogru", "uyari": "uyari"}

# Masaüstüne özgü metinler (geri kalanı harfiyen.METINLER'den)
YAZILAR = {
    "tr": {
        "zen": "zen", "tam_gorunum": "tam görünüm", "harfler": "harfler", "menu": "menü",
        "atla": "atla", "bugun": "bugün", "dk": "dk", "gun_seri": "{n} gün seri",
        "seviye_kisa": "sv {n}", "zen_ac": "Zen modu", "panel": "Harf güveni",
        "cikis": "Çık", "son_turlar": "son {n} tur", "kalan": "kalan",
        "basla": "yazmaya başlayınca süre işler", "test_bitti": "HIZ TESTİ",
        "yeni_rekor": "★  YENİ REKOR", "tekrar": "Tekrar", "derse_don": "Derse dön",
        "onceki_en_iyi": "önceki en iyi {d:.0f} DBK", "en_iyi": "en iyi {d:.0f} DBK",
        "dogru_hata": "{d} doğru  ·  {h} hata  ·  {s} sn",
        "acik_harf": "{n}/{m} harf açık", "usta": "usta", "henuz": "henüz yok",
        "tui_acik": "Harfiyen terminalde de açık — ilerleme kayıtları çakışabilir",
        "metin_yok": "Metin bulunamadı", "yeni_harf_kisa": "YENİ HARF",
        "kelime_n": "{n} kelime", "hazir_kisa": "hazır {n}/{m}",
    },
    "en": {
        "zen": "zen", "tam_gorunum": "full view", "harfler": "letters", "menu": "menu",
        "atla": "skip", "bugun": "today", "dk": "min", "gun_seri": "{n} day streak",
        "seviye_kisa": "lv {n}", "zen_ac": "Zen mode", "panel": "Letter confidence",
        "cikis": "Quit", "son_turlar": "last {n} lines", "kalan": "left",
        "basla": "the clock starts when you type", "test_bitti": "SPEED TEST",
        "yeni_rekor": "★  NEW BEST", "tekrar": "Again", "derse_don": "Back to lesson",
        "onceki_en_iyi": "previous best {d:.0f} WPM", "en_iyi": "best {d:.0f} WPM",
        "dogru_hata": "{d} correct  ·  {h} errors  ·  {s} s",
        "acik_harf": "{n}/{m} letters open", "usta": "mastered", "henuz": "no data yet",
        "tui_acik": "Harfiyen is also open in a terminal — progress saves may collide",
        "metin_yok": "No texts found", "yeni_harf_kisa": "NEW LETTER",
        "kelime_n": "{n} words", "hazir_kisa": "ready {n}/{m}",
    },
}


def ayarlari_yukle(yol=AYAR_DOSYASI):
    ayar = dict(VARSAYILAN)
    try:
        with open(yol, encoding="utf-8") as f:
            ham = json.load(f)
        if isinstance(ham, dict):
            for k, v in ham.items():
                if k in VARSAYILAN and type(v) is type(VARSAYILAN[k]):
                    ayar[k] = v
    except (OSError, ValueError):
        pass
    ayar["satir_karakter"] = min(max(ayar["satir_karakter"], 20), 80)
    return ayar


def tema_renkleri(tema):
    """Harfiyen temasını QML'in anlayacağı #rrggbb renklere çevirir (terminal renkleri
    gibi boş alanlar için okunaklı yedekler)."""
    sonuc = {}
    for alan in hf.TEMA_ALANLARI:
        try:
            rgb = hf.renk_rgb(tema.get(alan))
        except (TypeError, ValueError):
            rgb = None
        if rgb:
            sonuc[alan] = "#%02x%02x%02x" % rgb
    sonuc.setdefault("zemin", "#101010")
    acik = hf.parlaklik(hf.renk_rgb(sonuc["zemin"])) > 0.5
    yedek = {"yuzey": sonuc["zemin"], "yazi": "#303030" if acik else "#d0d0d0",
             "soluk": "#8a8a8a" if acik else "#6c6c6c", "cizgi": "#c8c8c8" if acik else "#3a3a3a",
             "baslik": "#000000" if acik else "#ffffff", "vurgu": "#ffd75f",
             "vurgu_yazi": "#000000", "dogru": "#5faf5f", "hata": "#ff5f5f",
             "hata_yazi": "#000000", "uyari": "#ffaf5f"}
    for alan, deger in yedek.items():
        sonuc.setdefault(alan, deger)
    for p in hf.PARMAK_TURLERI:
        try:
            rgb = hf.renk_rgb(tema["parmak"][p])
        except (KeyError, TypeError, ValueError):
            rgb = None
        sonuc["p_" + p] = "#%02x%02x%02x" % rgb if rgb else sonuc["soluk"]
    sonuc["karisim"] = float(tema.get("tus_karisim", 0.6))
    sonuc["acik"] = acik
    return sonuc


def tui_acik_mi():
    """Terminal arayüzü çalışıyorsa ikisi aynı ilerleme dosyasına yazar."""
    benim = os.getpid()
    try:
        pidler = os.listdir("/proc")
    except OSError:
        return False
    for pid in pidler:
        if not pid.isdigit() or int(pid) == benim:
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                arglar = f.read().split(b"\0")[:3]
        except OSError:
            continue
        if any(os.path.basename(a) in (b"harfiyen", b"harfiyen.py") for a in arglar):
            return True
    return False


def parmak_sirasi(parmak):
    """0-7: sol serçe → sağ serçe; başparmak ya da bilinmeyen için -1."""
    if not parmak or parmak[1] not in PARMAK_SIRASI:
        return -1
    i = PARMAK_SIRASI.index(parmak[1])
    return i if parmak[0] == "sol" else (7 - i if parmak[0] == "sag" else -1)


class Masaustu(QObject):
    """QML'e açılan denetleyici; asıl iş harfiyen.Oturum'da."""

    degisti = Signal()           # satır, konum, mesaj — her vuruşta
    ozetDegisti = Signal()       # metrikler, harfler, günlük — satır bitince
    duzenDegisti = Signal()      # klavye, tema, profil
    gorunumDegisti = Signal()    # zen, panel, katmanlar
    yanlis = Signal()
    yeniHarf = Signal(str)

    def __init__(self, oturum, ayar, ayar_yolu=AYAR_DOSYASI, kaydet=True):
        super().__init__()
        self.o = oturum
        self.ayar = ayar
        self.ayar_yolu = ayar_yolu
        self.kaydetme_izni = kaydet
        self.o.satir_maks = ayar["satir_karakter"]
        self.o.yeni_satir(tazele=True)
        self._renk = tema_renkleri(self.o.temalar.get(self.o.ayarlar["tema"])
                                   or self.o.temalar["gece"])
        self._katman = ""            # "", "menu", "mod", "metin", "sonuc"
        self._sonuc = {}
        self.zamanlayici = QTimer(self, interval=200)
        self.zamanlayici.timeout.connect(self._tik)
        self.zamanlayici.start()
        if not kaydet:
            self.o.kaydet = lambda: None
            self.o.depo.kaydet = lambda *_: None

    # -- yardımcılar ----------------------------------------------------------------

    @property
    def y(self):
        return YAZILAR.get(self.o.arayuz, YAZILAR["tr"])

    def _ayar_yaz(self):
        try:
            hf.json_yaz(self.ayar_yolu, self.ayar)
        except OSError as hata:
            print(f"masaustu.json yazılamadı: {hata}", file=sys.stderr)

    def _tik(self):
        o = self.o
        simdi = time.monotonic()
        degisti = False
        if o.mesaj and o.mesaj_bitis and simdi >= o.mesaj_bitis:
            o.mesaj = None
            degisti = True
        if o.flas_tus is not None and simdi >= o.flas_bitis:
            o.flas_tus = None
            degisti = True
        t = o.test
        if t and t["bas"] is not None and o.duraklama is None:
            if simdi - t["bas"] >= t["sure"]:
                self._test_bitti()
                return
            degisti = True
        if degisti:
            self.degisti.emit()

    # -- yazı ---------------------------------------------------------------------------

    @Property(str, notify=degisti)
    def satir(self):
        return self.o.satir

    @Property(str, notify=degisti)
    def sonraki(self):
        return self.o.sonraki if self.o.ayarlar.get("sonraki_satir", True) else ""

    @Property(int, notify=degisti)
    def konum(self):
        return self.o.konum

    @Property(str, notify=degisti)
    def hataMaskesi(self):
        """satir uzunluğunda "0"/"1" dizisi — QML'de konum başına ucuz bakış."""
        h = self.o.hatalar
        return "".join("1" if i in h else "0" for i in range(len(self.o.satir)))

    @Property(bool, notify=degisti)
    def konumdaHata(self):
        return self.o.konumda_hata

    @Property(int, notify=degisti)
    def parmakSirasi(self):
        h = self.o.hedef
        return -1 if h is None else parmak_sirasi(self.o.duzen.parmak(h))

    @Property(str, notify=degisti)
    def parmakTuru(self):
        h = self.o.hedef
        p = self.o.duzen.parmak(h) if h is not None else None
        return p[1] if p else ""

    @Property(str, notify=degisti)
    def hedefTus(self):
        """Basılacak tuşun adı (Duzen.tuslar'daki ad)."""
        h = self.o.hedef
        if h is None:
            return ""
        if h == " ":
            return " "
        cozum = self.o.duzen.cozumle(h)
        return cozum[0] if cozum else ""

    @Property(str, notify=degisti)
    def shiftTus(self):
        h = self.o.hedef
        return (self.o.duzen.shift_tusu(h) or "") if h not in (None, " ") else ""

    @Property(str, notify=degisti)
    def flasTus(self):
        return self.o.flas_tus or ""

    @Property(str, notify=degisti)
    def mesaj(self):
        return self.o.mesaj or ""

    @Property(str, notify=degisti)
    def mesajTuru(self):
        return BILDIRIM_TURU.get(self.o.mesaj_tur, "yazi") if self.o.mesaj else ""

    @Property(str, notify=degisti)
    def durum(self):
        """Kartın altında soldaki kısa durum: hazır harfler, test süresi ya da metin."""
        o = self.o
        if o.test is not None:
            kalan = o.test_kalan()
            return f"{int(kalan) // 60}:{int(kalan) % 60:02d}"
        if o.alistirma_modu == "metin" and o.metin:
            return o.metin["ad"]
        il = o.ilerleme
        if il.siradaki_harf is None:
            return o._durum_mesaji()
        return self.y["hazir_kisa"].format(n=il.hazir_sayisi(), m=len(il.acik_harfler))

    @Property(str, notify=degisti)
    def durumUzun(self):
        o = self.o
        if o.test is not None and o.test["bas"] is None:
            return self.y["basla"]
        return o._durum_mesaji() if o.alistirma_modu in ("ders", "zayif") else ""

    @Property(float, notify=degisti)
    def testOrani(self):
        """Hız testinde geçen sürenin oranı (test yoksa -1)."""
        o = self.o
        if o.test is None:
            return -1.0
        return 1.0 - o.test_kalan() / max(1, o.test["sure"])

    @Slot(str)
    def tus(self, metin):
        if self._katman or not metin:
            return
        o = self.o
        for c in unicodedata.normalize("NFC", metin):
            if not c.isprintable():
                continue
            onceki_acik = o.ilerleme.acik_sayisi
            satir_once = o.satir
            hata_once = o.hatali_basis
            o.tus_isle(c)
            if o.hatali_basis > hata_once:
                self.yanlis.emit()
            if o.satir is not satir_once:          # satır bitti: özet değişti
                self.ozetDegisti.emit()
                if o.ilerleme.acik_sayisi > onceki_acik:
                    self.yeniHarf.emit(o.ilerleme.acik_harfler[-1])
        self.degisti.emit()

    @Slot()
    def satirAtla(self):
        if self._katman:
            return
        o = self.o
        onceki_acik = o.ilerleme.acik_sayisi
        o.satir_bitti(tamamlandi=False)
        if o.ilerleme.acik_sayisi > onceki_acik:
            self.yeniHarf.emit(o.ilerleme.acik_harfler[-1])
        self.ozetDegisti.emit()
        self.degisti.emit()

    # -- özet --------------------------------------------------------------------------

    def _degisim(self, simdi, onceki, ondalik):
        if onceki is None:
            return ""
        fark = simdi - onceki
        if abs(fark) < 10 ** -ondalik / 2:
            return ""
        return f"{'↑' if fark > 0 else '↓'}{abs(fark):.{ondalik}f}"

    @Property("QVariantList", notify=ozetDegisti)
    def metrikler(self):
        """[{etiket, deger, degisim, iyi}] — hız, doğruluk, puan (son satır)."""
        o, m = self.o, self.o.m
        il = o.ilerleme
        son = il.turlar[-1] if il.turlar else None
        once = il.turlar[-2] if len(il.turlar) > 1 else None

        def puan(t):
            return t.get("puan", hf.puan_hesapla(t["dbk"], t["dogruluk"], il.acik_sayisi))
        if not son:
            return [{"etiket": m["m_hiz"], "deger": m["yok"], "degisim": "", "iyi": True},
                    {"etiket": m["m_dogruluk"], "deger": m["yok"], "degisim": "", "iyi": True},
                    {"etiket": m["m_puan"], "deger": m["yok"], "degisim": "", "iyi": True}]
        sonuc = []
        for etiket, deger, onceki, ondalik, bicim in (
                (m["m_hiz"], son["dbk"], once and once["dbk"], 1, f"{son['dbk']:.1f}"),
                (m["m_dogruluk"], son["dogruluk"], once and once["dogruluk"], 1,
                 o.yuzde(son["dogruluk"], 1)),
                (m["m_puan"], puan(son), once and puan(once), 0, str(puan(son)))):
            d = self._degisim(deger, onceki, ondalik)
            sonuc.append({"etiket": etiket, "deger": bicim, "degisim": d,
                          "iyi": d.startswith("↑")})
        return sonuc

    @Property(str, notify=ozetDegisti)
    def hizKisa(self):
        il = self.o.ilerleme
        return f"{il.turlar[-1]['dbk']:.0f} {self.o.m['dbk']}" if il.turlar else ""

    @Property("QVariantList", notify=ozetDegisti)
    def harfler(self):
        """[{h, etiket, acik, guncel, usta, guven, veri}] — müfredat sırasıyla."""
        o = self.o
        il = o.ilerleme
        sonuc = []
        for j, harf in enumerate(il.sira):
            acik = j < il.acik_sayisi
            veri = bool(il.gecmis.get(harf))
            sonuc.append({"h": harf, "etiket": hf.buyuk_harf(harf, o.dil_kodu), "acik": acik,
                          "guncel": acik and harf == il.guncel_harf and not il.ustalasti_mi(harf),
                          "usta": acik and il.ustalasti_mi(harf),
                          "guven": il.guven(harf) if acik and veri else 0.0, "veri": veri})
        return sonuc

    @Property(str, notify=ozetDegisti)
    def harfOzeti(self):
        il = self.o.ilerleme
        return self.y["acik_harf"].format(n=il.acik_sayisi, m=len(il.sira))

    @Property(float, notify=ozetDegisti)
    def gunlukOran(self):
        hedef = self.o.ayarlar["gunluk_hedef_dk"]
        if not hedef:
            return 0.0
        return min(1.0, self.o._bugun_sn() / 60 / hedef)

    @Property(str, notify=ozetDegisti)
    def gunlukMetin(self):
        hedef = self.o.ayarlar["gunluk_hedef_dk"]
        dk = round(self.o._bugun_sn() / 60)
        y = self.y
        return f"{y['bugun']} {dk}/{hedef} {y['dk']}" if hedef else f"{y['bugun']} {dk} {y['dk']}"

    @Property(str, notify=ozetDegisti)
    def seriMetin(self):
        n = hf.gun_serisi(self.o.depo.genel["gunluk"], self.o.ayarlar["gunluk_hedef_dk"] * 60)
        return self.y["gun_seri"].format(n=n) if n else ""

    @Property(str, notify=ozetDegisti)
    def seviyeMetin(self):
        return self.y["seviye_kisa"].format(n=hf.seviye_hesapla(self.o.depo.genel["xp"])[0])

    @Property(float, notify=ozetDegisti)
    def xpOrani(self):
        xp = self.o.depo.genel["xp"]
        _, alt, ust = hf.seviye_hesapla(xp)
        return (xp - alt) / max(1, ust - alt)

    @Property(str, notify=ozetDegisti)
    def xpMetin(self):
        return self.o.m["xp"].format(x=self.o.depo.genel["xp"])

    @Property("QVariantList", notify=ozetDegisti)
    def sonTurlar(self):
        """Son satırların hızı ve doğruluğu (çekmecedeki küçük grafik için)."""
        return [{"dbk": t["dbk"], "dogruluk": t["dogruluk"]}
                for t in self.o.ilerleme.turlar[-30:]]

    # -- düzen, tema, metinler --------------------------------------------------------

    @Property("QVariantMap", notify=duzenDegisti)
    def renk(self):
        return self._renk

    @Property("QVariantMap", notify=duzenDegisti)
    def metinler(self):
        """harfiyen.METINLER + masaüstü yazıları (QML'de m.anahtar)."""
        return {**{k: v for k, v in self.o.m.items() if isinstance(v, str)},
                **self.y, "modlar": self.o.m["modlar"],
                "mod_aciklama": {k: v.format(s=self.o.ayarlar["test_suresi_sn"])
                                 for k, v in self.o.m["mod_aciklama"].items()}}

    @Property(str, notify=degisti)
    def modAdi(self):
        o = self.o
        ad = o.m["modlar"][o.alistirma_modu]
        return ad

    @Property(str, notify=degisti)
    def alistirmaModu(self):
        return self.o.alistirma_modu

    @Property(str, notify=duzenDegisti)
    def profil(self):
        o = self.o
        fiz = {"iso": "ISO", "ansi": "ANSI", "ansi102": "ANSI 102"}[o.duzen.fiziksel]
        return f"{hf.DUZENLER[o.duzen.kimlik]['ad'][o.arayuz]} · {fiz} · {o.dil['ad'][o.arayuz]}"

    @Property(float, notify=duzenDegisti)
    def klavyeGenislik(self):
        return float(self.o.duzen.genislik_birim)

    @Property("QVariantList", notify=ozetDegisti)
    def tuslar(self):
        """Klavyenin tuşları: konum (tuş birimi), etiket, parmak ve açık olup olmadığı."""
        o = self.o
        d = o.duzen
        acik = set(o.ilerleme.acik_harfler)
        sonuc = []
        for k in d.tuslar:
            if k.karakter and k.ad not in hf.TUS_ETIKETLERI:
                etiket = hf.buyuk_harf(k.karakter, d.dil)
                ust = d.shift_tersi.get(k.karakter, "")
                if ust and ust == etiket:
                    ust = ""
            else:
                secenek = hf.TUS_ETIKETLERI.get(k.ad, {})
                liste = secenek.get(o.arayuz) or secenek.get("*") or [k.ad]
                etiket, ust = liste[min(1, len(liste) - 1)] if k.ad != " " else "", ""
            harf = k.karakter is not None and (k.karakter.isalpha() or k.karakter in o.ilerleme.sira)
            sonuc.append({
                "ad": k.ad, "etiket": etiket, "ust": ust, "x": k.x, "g": k.g, "satir": k.satir,
                "yuk": k.yuk, "parmak": k.parmak[1] if k.parmak else "",
                "acik": (k.karakter in acik) if harf else (k.karakter is not None),
                "harf": harf, "cikinti": k.karakter in d.cikintilar, "numpad": k.numpad,
            })
        return sonuc

    @Slot(result="QVariantList")
    def metinListesi(self):
        return [{"ad": ad, "ipucu": self.y["kelime_n"].format(n=len(icerik.split()))}
                for ad, icerik in hf.metinleri_listele(self.o.dil_kodu)]

    # -- görünüm ----------------------------------------------------------------------

    @Property(bool, notify=gorunumDegisti)
    def zen(self):
        return self.ayar["zen"]

    @Property(bool, notify=gorunumDegisti)
    def panel(self):
        return self.ayar["harf_paneli"]

    @Property(str, notify=gorunumDegisti)
    def katman(self):
        return self._katman

    @Property("QVariantMap", notify=gorunumDegisti)
    def sonuc(self):
        return self._sonuc

    @Slot()
    def zenDegistir(self):
        self.ayar["zen"] = not self.ayar["zen"]
        self._ayar_yaz()
        self.gorunumDegisti.emit()

    @Slot()
    def panelDegistir(self):
        self.ayar["harf_paneli"] = not self.ayar["harf_paneli"]
        self._ayar_yaz()
        self.gorunumDegisti.emit()

    @Slot(str)
    def katmanAc(self, ad):
        if ad:
            self.o.duraklat()
        self._katman = ad
        if not ad:
            self.o.surdur()
        self.gorunumDegisti.emit()
        self.degisti.emit()

    @Slot(str)
    def modSec(self, mod):
        self.o.alistirma_modu_sec(mod)
        self._sonuc = {}
        self.katmanAc("")
        self.ozetDegisti.emit()

    @Slot(str)
    def metinSec(self, ad):
        for metin_ad, icerik in hf.metinleri_listele(self.o.dil_kodu):
            if metin_ad == ad:
                self.o.alistirma_modu_sec("metin", (metin_ad, icerik))
                break
        self.katmanAc("")

    def _test_bitti(self):
        sonuc, onceki, bildirimler = self.o.test_sonucu_kaydet()
        y, m = self.y, self.o.m
        self._sonuc = {
            "baslik": y["test_bitti"],
            "dbk": f"{sonuc['dbk']:.1f}", "birim": m["dbk"],
            "dogruluk": self.o.yuzde(sonuc["dogruluk"], 1),
            "ayrinti": y["dogru_hata"].format(d=sonuc["dogru"], h=sonuc["hata"], s=sonuc["sure"]),
            "rekor": bool(onceki) and sonuc["dbk"] > onceki,
            "onceki": (y["onceki_en_iyi"] if sonuc["dbk"] > onceki else y["en_iyi"]).format(d=onceki)
            if onceki else "",
            "bildirimler": bildirimler,
        }
        self.katmanAc("sonuc")
        self.ozetDegisti.emit()

    @Slot()
    def kapat(self):
        self.o.kaydet()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="harfiyen-masaustu",
                                 description="Harfiyen'in masaüstü (Qt Quick) arayüzü")
    ap.add_argument("--version", action="version", version=f"%(prog)s {hf.__version__}")
    ap.add_argument("--kaydetme", action="store_true", help="ilerlemeyi ve ayarları yazma (deneme)")
    ap.add_argument("--zen", action="store_true", default=None, help="zen modunda aç")
    ap.add_argument("--panel", action="store_true", default=None, help="harf güveni paneli açık")
    ap.add_argument("--goruntu", metavar="PNG",
                    help="pencereyi çizip ekran görüntüsünü kaydet ve çık (deneme/belgeleme)")
    ap.add_argument("--yaz", metavar="METIN", default="",
                    help="--goruntu ile: görüntüden önce bu tuşları gönder")
    ap.add_argument("--katman", default="", help="--goruntu ile: menu/mod/sonuc katmanını aç")
    ap.add_argument("--boyut", default="1280x800", help="--goruntu ile: pencere boyutu")
    sec = ap.parse_args(argv)

    try:
        hf.yapilandirma_hazirla()
    except OSError as hata:
        print(f"Uyarı: yapılandırma dizini hazırlanamadı: {hata}", file=sys.stderr)
    temalar, tema_uyarilari = hf.temalari_yukle()
    ayarlar, ayar_uyarilari, _ = hf.ayarlari_yukle(temalar=temalar)
    depo = hf.IlerlemeDeposu()
    ayar = ayarlari_yukle()
    if sec.zen is not None:
        ayar["zen"] = sec.zen
    if sec.panel is not None:
        ayar["harf_paneli"] = sec.panel
    oturum = hf.Oturum(ayarlar, temalar, depo)
    uyarilar = list(tema_uyarilari) + list(ayar_uyarilari) + ([depo.uyari] if depo.uyari else [])

    QGuiApplication.setApplicationName("Harfiyen")
    QGuiApplication.setDesktopFileName("harfiyen-masaustu")
    uygulama = QGuiApplication(sys.argv[:1])
    uygulama.setWindowIcon(QIcon.fromTheme("input-keyboard"))
    if "JetBrains Mono" not in QFontDatabase.families():
        print("JetBrains Mono bulunamadı; sistemin eş aralıklı yazı tipi kullanılacak",
              file=sys.stderr)
    denetci = Masaustu(oturum, ayar, kaydet=not (sec.kaydetme or sec.goruntu))
    if sec.kaydetme or sec.goruntu:
        denetci._ayar_yaz = lambda: None
    if tui_acik_mi():
        uyarilar.append(denetci.y["tui_acik"])
    if uyarilar:
        oturum.mesaj_ver(" · ".join(uyarilar)[:220], "uyari", 10)

    motor = QQmlApplicationEngine()
    motor.warnings.connect(lambda uyarilar: [print(u.toString(), file=sys.stderr) for u in uyarilar])
    motor.rootContext().setContextProperty("ana", denetci)
    motor.rootContext().setContextProperty("yaziTipiVar",
                                           "JetBrains Mono" in QFontDatabase.families())
    motor.load(QUrl.fromLocalFile(os.path.join(KOK, "qml", "Ana.qml")))
    if not motor.rootObjects():
        return 1
    pencere = motor.rootObjects()[0]
    uygulama.aboutToQuit.connect(denetci.kapat)

    if sec.goruntu:
        g, y = (int(v) for v in sec.boyut.lower().split("x"))
        pencere.setWidth(g)
        pencere.setHeight(y)
        if sec.yaz:
            denetci.tus(sec.yaz)
        if sec.katman == "sonuc":
            oturum.alistirma_modu_sec("test")
            oturum.test["bas"] = time.monotonic() - 61
            oturum.test["dogru"], oturum.test["hata"] = 212, 6
            denetci._test_bitti()
        elif sec.katman:
            islev = {"menu": "menuAc", "mod": "modListesi", "metin": "metinListesi"}[sec.katman]
            QMetaObject.invokeMethod(pencere, islev)

        def cek():
            QMetaObject.invokeMethod(pencere, "goruntuKaydet", Q_ARG("QVariant", sec.goruntu))
        QTimer.singleShot(900, cek)
    kod = uygulama.exec()
    del motor                        # QML, denetleyiciden önce kapansın
    return kod


if __name__ == "__main__":
    sys.exit(main())
