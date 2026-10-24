"""Harfiyen Mola: medya oynarken (ör. dizi izlerken) belli aralıklarla ekranın
üstüne kısa bir on parmak alıştırması çıkarır.

Akış: IzlemeSayaci MPRIS oynatma süresini biriktirir (kısa duraklatma ve sarma
sayacı bozmaz) → süre dolunca oynayan medya duraklatılır → Harfiyen'in açık
harflerinden birkaç kelime yazdırılır → bitince (ya da Esc ile) medya sürdürülür.
Vuruşlar Harfiyen ilerlemesine (progress.json) işlenir.
"""

import argparse
import json
import os
import random
import shutil
import signal
import socket
import subprocess
import sys
import time

KOK = os.path.dirname(os.path.realpath(__file__))


def _harfiyen_bul():
    try:
        import harfiyen
        return harfiyen
    except ImportError:
        pass
    adaylar = [os.path.dirname(os.path.dirname(KOK))]     # depodan çalıştırma
    yol = shutil.which("harfiyen")
    if yol:
        adaylar.insert(0, os.path.dirname(os.path.realpath(yol)))
    for dizin in adaylar:
        if os.path.exists(os.path.join(dizin, "harfiyen.py")):
            sys.path.insert(0, dizin)
            import harfiyen
            return harfiyen
    sys.exit("harfiyen modülü bulunamadı (harfiyen kurulu mu?)")


hf = _harfiyen_bul()

import dbus                                                         # noqa: E402
from PySide6.QtCore import (QObject, QSocketNotifier, QTimer, QUrl,  # noqa: E402
                            Property, Signal, Slot)
from PySide6.QtDBus import QDBusConnection, QDBusMessage, QDBusServiceWatcher  # noqa: E402
from PySide6.QtGui import QGuiApplication                            # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine                       # noqa: E402

AYAR_DOSYASI = os.path.join(hf.AYAR_DIZINI, "mola.json")
REKOR_DOSYASI = os.path.join(hf.VERI_DIZINI, "mola-rekor.json")
VARSAYILAN = {
    "aralik_dk": 10,                 # bu kadar dakika medya oynayınca çıkar
    "ara_sifirla_dk": 5,             # bundan uzun süre hiçbir şey oynamazsa sayaç baştan başlar
    "kelime": 10,                    # yazdırılacak kelime sayısı
    "parmak_goster": False,          # yazının altında "Sağ işaret parmak" gibi parmak tarifi
    "haric_oynaticilar": ["kdeconnect"],   # bu adları içeren MPRIS oynatıcılarına dokunma
    "ilerlemeye_kaydet": True,       # vuruşları Harfiyen ilerlemesine işle
    "sonuc_suresi_sn": 1.6,          # bitince sonucun ekranda kalma süresi
    "rekor_en_az_dogruluk": 90,      # bu doğruluğun altındaki tur rekor sayılmaz
}
REKOR_EK_SURE_SN = 1.4               # yeni rekorda sonuç biraz daha uzun kalır
MPRIS = "org.mpris.MediaPlayer2."
MPRIS_YOL = "/org/mpris/MediaPlayer2"
OYNATICI = "org.mpris.MediaPlayer2.Player"
SERVIS = "harfiyen-mola.service"
SATIR_GENISLIGI = 40                 # bundan uzun yazı birden çok satıra bölünür
PARMAK_SIRASI = ("serce", "yuzuk", "orta", "isaret")   # sol elde soldan sağa
KELIME_KARAKTER = 12                 # kelime başına ayrılan en fazla karakter


def ayarlari_yukle():
    ayar = dict(VARSAYILAN)
    try:
        with open(AYAR_DOSYASI, encoding="utf-8") as f:
            ham = json.load(f)
        for k, v in ham.items():
            if k not in VARSAYILAN:
                continue
            ornek = VARSAYILAN[k]
            if isinstance(ornek, bool):
                uygun = isinstance(v, bool)
            elif isinstance(ornek, (int, float)):
                uygun = isinstance(v, (int, float)) and not isinstance(v, bool)
            else:
                uygun = isinstance(v, type(ornek))
            if uygun:
                ayar[k] = v
        eksik = {k: v for k, v in VARSAYILAN.items() if k not in ham}
        if eksik:                    # yeni eklenen ayarlar dosyada görünsün
            hf.json_yaz(AYAR_DOSYASI, {**ham, **eksik})
    except FileNotFoundError:
        hf.json_yaz(AYAR_DOSYASI, VARSAYILAN)
    except (OSError, ValueError) as hata:
        print(f"mola.json okunamadı ({hata}); varsayılanlar kullanılıyor", file=sys.stderr)
    ayar["aralik_dk"] = min(max(float(ayar["aralik_dk"]), 0.05), 600)
    ayar["ara_sifirla_dk"] = min(max(float(ayar["ara_sifirla_dk"]), 0.01), 600)
    ayar["kelime"] = min(max(int(ayar["kelime"]), 1), 20)
    ayar["rekor_en_az_dogruluk"] = min(max(float(ayar["rekor_en_az_dogruluk"]), 0), 100)
    return ayar


def rekor_yukle(yol=None):
    """Kayıtlı en iyi mola turu ({"dbk", "dogruluk", "tarih"}) ya da None."""
    try:
        with open(yol or REKOR_DOSYASI, encoding="utf-8") as f:
            veri = json.load(f)
        dbk = veri.get("dbk")
        if isinstance(dbk, (int, float)) and not isinstance(dbk, bool) and dbk > 0:
            return veri
    except (OSError, ValueError, AttributeError):
        pass
    return None


def rekor_isle(ist, en_az_dogruluk, yol=None, kaydet=True):
    """Biten turu rekorla karşılaştırır; (önceki rekor ya da None, yeni rekor mu) döner.

    Önceki kayıt yoksa ilk tur rekor olarak yazılır ama "yeni rekor" sayılmaz.
    """
    onceki = rekor_yukle(yol)
    if ist["dogruluk"] < en_az_dogruluk:
        return onceki, False
    if onceki is not None and ist["dbk"] <= onceki["dbk"]:
        return onceki, False
    if kaydet:
        try:
            hf.json_yaz(yol or REKOR_DOSYASI,
                        {"dbk": round(ist["dbk"], 2), "dogruluk": round(ist["dogruluk"], 1),
                         "tarih": hf.bugun_anahtari()})
        except OSError as hata:
            print(f"rekor kaydedilemedi: {hata}", file=sys.stderr)
    return onceki, onceki is not None


def satirlara_bol(metin, en_fazla=SATIR_GENISLIGI):
    """Metni kelime sınırlarından, birbirine yakın uzunlukta satırlara böler.

    (başlangıç, bitiş) aralıkları döner; kelimeden sonraki boşluk o satırda kalır,
    böylece imleç satır sonundaki boşlukta da görünür.
    """
    if len(metin) <= en_fazla:
        return [(0, len(metin))]
    kelimeler, i = [], 0
    for k in metin.split(" "):
        kelimeler.append((i, i + len(k)))
        i += len(k) + 1
    adet = -(-len(metin) // en_fazla)
    genislik = max(-(-len(metin) // adet), max(b - a for a, b in kelimeler))
    while True:
        satirlar, bas = [], 0
        for a, b in kelimeler:
            if b - bas > genislik and a > bas:
                satirlar.append((bas, a))
                bas = a
        satirlar.append((bas, len(metin)))
        if len(satirlar) <= adet:
            return satirlar
        genislik += 1


# ---------------------------------------------------------------------------
# MPRIS ve oturum
# ---------------------------------------------------------------------------


class Medya:
    def __init__(self, haric, yalnizca=None):
        self.bus = dbus.SessionBus()
        self.haric = [h.lower() for h in haric]
        self.yalnizca = yalnizca            # testlerde gerçek oynatıcılara dokunmamak için

    def _oynaticilar(self):
        try:
            adlar = self.bus.list_names()
        except dbus.DBusException:
            return []
        return [str(a) for a in adlar if a.startswith(MPRIS)
                and not any(h in a.lower() for h in self.haric)
                and (self.yalnizca is None or self.yalnizca in a)]

    def _ozellik(self, ad, arayuz, ozellik):
        nesne = self.bus.get_object(ad, MPRIS_YOL, introspect=False)
        return nesne.Get(arayuz, ozellik, dbus_interface="org.freedesktop.DBus.Properties",
                         timeout=1.0)

    def oynayanlar(self):
        sonuc = []
        for ad in self._oynaticilar():
            try:
                if str(self._ozellik(ad, OYNATICI, "PlaybackStatus")) == "Playing":
                    sonuc.append(ad)
            except dbus.DBusException:
                pass
        return sonuc

    def kimlik(self, ad):
        try:
            return str(self._ozellik(ad, "org.mpris.MediaPlayer2", "Identity"))
        except dbus.DBusException:
            return ad[len(MPRIS):].split(".")[0]

    def _cagir(self, ad, yontem):
        try:
            nesne = self.bus.get_object(ad, MPRIS_YOL, introspect=False)
            getattr(nesne, yontem)(dbus_interface=OYNATICI, timeout=1.0)
            return True
        except dbus.DBusException as hata:
            print(f"{ad} {yontem}: {hata.get_dbus_name()}", file=sys.stderr)
            return False

    def duraklat(self, adlar):
        return [ad for ad in adlar if self._cagir(ad, "Pause")]

    def surdur(self, adlar):
        mevcut = set(self._oynaticilar())
        for ad in adlar:
            if ad in mevcut:
                self._cagir(ad, "Play")

    def ekran_kilitli(self):
        try:
            nesne = self.bus.get_object("org.freedesktop.ScreenSaver", "/ScreenSaver",
                                        introspect=False)
            return bool(nesne.GetActive(dbus_interface="org.freedesktop.ScreenSaver",
                                        timeout=1.0))
        except dbus.DBusException:
            return False


HARFIYEN_SURECLERI = (b"harfiyen", b"harfiyen.py",              # terminal
                      b"harfiyen-masaustu", b"harfiyen_masaustu")   # masaüstü (betik / -m)


def harfiyen_acik_mi():
    """Harfiyen (terminal ya da masaüstü) çalışıyorsa ilerlemeyi o yazar; üstüne yazmamak için."""
    benim = os.getpid()
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or int(pid) == benim:
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                arglar = f.read().split(b"\0")[:3]
        except OSError:
            continue
        if any(os.path.basename(a) in HARFIYEN_SURECLERI for a in arglar):
            return True
    return False


# ---------------------------------------------------------------------------
# Alıştırma
# ---------------------------------------------------------------------------


class Alistirma:
    """Harfiyen'in ders modu satır üreticisiyle kısa bir yazı ve vuruş kaydı."""

    def __init__(self, kelime_sayisi, rng=None):
        self.rng = rng or random.Random()
        temalar, _ = hf.temalari_yukle()
        self.ayar, _, _ = hf.ayarlari_yukle(temalar=temalar)
        a = self.ayar
        self.tema = temalar.get(a["tema"]) or temalar["gece"]
        self.m = hf.METINLER.get(a["arayuz"], hf.METINLER["tr"])
        self.duzen = hf.Duzen(a["klavye"], a["fiziksel"], a["numpad"])
        dil = a["dil"]
        try:
            sira = hf.mufredat(dil, self.duzen)
        except hf.UyumsuzDuzen:
            dil = hf.DUZENLER[a["klavye"]]["dil"]
            sira = hf.mufredat(dil, self.duzen)
        self.dil = dil
        self.anahtar = hf.profil_anahtari(dil, a["klavye"])
        self.depo = hf.IlerlemeDeposu()
        self.ilerleme = self.depo.profil(self.anahtar, a["ustalik_penceresi"], sira,
                                         a["ustalik_olcutu"], a["hedef_hiz"])
        d = hf.DILLER[dil]
        en_fazla = max(hf.SATIR_KARAKTER, kelime_sayisi * KELIME_KARAKTER)
        satir = hf.satir_uret(self.ilerleme, self.rng, en_fazla, kelime_sayisi,
                              kelimeler=d["kelimeler"], sesliler=frozenset(d["sesliler"]))
        self.metin = hf.susle(satir, self.rng, self.duzen, dil, a["buyuk_harf"],
                              a["noktalama"], a["rakamlar"], max_karakter=en_fazla)
        self.satirlar = satirlara_bol(self.metin)
        self.konum = 0
        self.hatalar = set()
        self.konumda_hata = False
        self.hatali_basis = 0
        self.zamanlar = []
        self.son_vurus = None
        self.sure = 0.0

    @property
    def hedef(self):
        return self.metin[self.konum] if self.konum < len(self.metin) else None

    @property
    def bitti(self):
        return self.konum >= len(self.metin)

    def tus(self, c):
        """True: doğru, False: yanlış, None: yok sayıldı."""
        hedef = self.hedef
        if hedef is None:
            return None
        simdi = time.monotonic()
        ara = simdi - self.son_vurus if self.son_vurus is not None else None
        self.son_vurus = simdi
        harf = hf.kucuk_harf(hedef, self.dil)
        izli = harf in self.ilerleme.gecmis
        onceki = hf.kucuk_harf(self.metin[self.konum - 1], self.dil) if self.konum else None
        il = self.ilerleme
        if c == hedef:
            kisa = ara is not None and ara < hf.EN_UZUN_ARA
            if kisa:
                self.sure += ara
            if not self.konumda_hata and izli:
                il.deneme_kaydet(harf, True, 12 / ara if kisa and ara else None)
                if onceki:
                    il.cift_kaydet(onceki, harf, True)
            if not self.konumda_hata:
                self.depo.genel["vurus"] += 1
                self.depo.genel["xp"] += 1
            self.zamanlar.append(simdi)
            self.konum += 1
            self.konumda_hata = False
            return True
        self.hatali_basis += 1
        if not self.konumda_hata:
            self.konumda_hata = True
            self.hatalar.add(self.konum)
            if izli:
                il.deneme_kaydet(harf, False)
                if onceki:
                    il.cift_kaydet(onceki, harf, False)
        return False

    def istatistik(self):
        return hf.tur_istatistikleri(self.zamanlar, self.hatali_basis)

    def kaydet(self):
        g = self.depo.genel
        gun = hf.bugun_anahtari()
        g["gunluk"][gun] = g["gunluk"].get(gun, 0.0) + self.sure
        g["saniye"] = g.get("saniye", 0.0) + self.sure
        self.depo.kaydet(self.anahtar, self.ilerleme)

    def parmak(self):
        """(tarif, renk) — sıradaki karakterin parmağı."""
        hedef = self.hedef
        p = self.duzen.parmak(hedef) if hedef is not None else None
        if p is None:
            return "", self.tema["soluk"]
        taraf, tur = p
        if not taraf:
            tarif = self.m["Basparmak"]
        else:
            tarif = f"{self.m[taraf]} {self.m['parmak_adlari'][tur]} {self.m['parmak_ek']}"
        return tarif, self.tema["parmak"].get(tur, self.tema["yazi"])

    def parmak_sirasi(self):
        """0-7 — alttaki sekiz göstergeden sıradakine düşeni (sol serçe → sağ serçe);
        başparmak (boşluk) ya da bilinmeyen karakter için -1."""
        hedef = self.hedef
        p = self.duzen.parmak(hedef) if hedef is not None else None
        if not p or p[1] not in PARMAK_SIRASI:
            return -1
        i = PARMAK_SIRASI.index(p[1])
        return i if p[0] == "sol" else (7 - i if p[0] == "sag" else -1)


def tema_renkleri(tema):
    sonuc = {}
    for alan in hf.TEMA_ALANLARI:
        deger = tema.get(alan)
        if deger is None:
            continue
        try:
            sonuc[alan] = "#%02x%02x%02x" % hf.renk_rgb(deger)
        except (TypeError, ValueError):
            pass
    sonuc.setdefault("zemin", "#000000")
    sonuc.setdefault("yuzey", sonuc["zemin"])
    for alan, yedek in (("yazi", "#d0d0d0"), ("soluk", "#6c6c6c"), ("cizgi", "#4e4e4e"),
                        ("baslik", "#ffffff"), ("vurgu", "#ffd75f"), ("vurgu_yazi", "#000000"),
                        ("dogru", "#87d787"), ("hata", "#ff5f5f")):
        sonuc.setdefault(alan, yedek)
    return sonuc


# ---------------------------------------------------------------------------
# Denetleyici (QML'e açılan nesne)
# ---------------------------------------------------------------------------


class Mola(QObject):
    degisti = Signal()
    gorunurDegisti = Signal()
    yanlis = Signal()

    def __init__(self, ayar, secenek):
        super().__init__()
        self.ayar = ayar
        self.secenek = secenek
        self.medya = Medya(ayar["haric_oynaticilar"], secenek.yalnizca_oynatici)
        self.alistirma = None
        self.duraklatilan = []
        self.duraklatilan_ad = ""
        self._gorunur = False
        self._asama = "yaziyor"
        self._sonuc = ""
        self._rekor = False
        self._rekor_bilgisi = ""
        self._renkler = tema_renkleri(hf.YERLESIK_TEMALAR["gece"])
        self.kapat_zamanlayici = QTimer(self, singleShot=True)
        self.kapat_zamanlayici.timeout.connect(self.kapat)

    # -- QML özellikleri -------------------------------------------------------

    def _get_gorunur(self):
        return self._gorunur

    gorunur = Property(bool, _get_gorunur, notify=gorunurDegisti)

    @Property("QVariantList", notify=degisti)
    def satirlar(self):
        """Her satır bir karakter listesi: [{"c": ..., "durum": ...}, ...]."""
        a = self.alistirma
        if a is None:
            return []
        sonuc = []
        for bas, son in a.satirlar:
            liste = []
            for i in range(bas, son):
                if i < a.konum:
                    durum = "hatali" if i in a.hatalar else "dogru"
                elif i == a.konum:
                    durum = "simdi"
                else:
                    durum = "bekliyor"
                liste.append({"c": a.metin[i], "durum": durum})
            sonuc.append(liste)
        return sonuc

    @Property(bool, notify=degisti)
    def parmakGoster(self):
        return bool(self.ayar["parmak_goster"])

    @Property(str, notify=degisti)
    def asama(self):
        return self._asama

    @Property(str, notify=degisti)
    def sonuc(self):
        return self._sonuc

    @Property(bool, notify=degisti)
    def rekor(self):
        return self._rekor

    @Property(str, notify=degisti)
    def rekorBilgisi(self):
        return self._rekor_bilgisi

    @Property(str, notify=degisti)
    def parmakTarifi(self):
        if self.alistirma is None or self.alistirma.hedef is None:
            return ""
        tarif, _ = self.alistirma.parmak()
        hedef = self.alistirma.hedef
        return f"{'boşluk' if hedef == ' ' else hedef}  ·  {tarif}"

    @Property(str, notify=degisti)
    def parmakRengi(self):
        if self.alistirma is None:
            return self._renkler["soluk"]
        return self.alistirma.parmak()[1]

    @Property(int, notify=degisti)
    def parmakSirasi(self):
        return -1 if self.alistirma is None else self.alistirma.parmak_sirasi()

    @Property(float, notify=degisti)
    def oran(self):
        a = self.alistirma
        return a.konum / len(a.metin) if a and a.metin else 0.0

    @Property(str, notify=degisti)
    def sayac(self):
        a = self.alistirma
        if a is None:
            return ""
        toplam = len(a.metin.split())
        yazilan = a.metin[:a.konum].count(" ") + (1 if a.bitti else 0)
        return f"{yazilan}/{toplam} kelime"

    @Property(int, notify=degisti)
    def hataSayisi(self):
        return self.alistirma.hatali_basis if self.alistirma else 0

    @Property(str, notify=degisti)
    def medyaBilgisi(self):
        return self.duraklatilan_ad

    @Property("QVariantMap", notify=degisti)
    def renk(self):
        return self._renkler

    # -- akış ------------------------------------------------------------------

    def vakit(self):
        """İzleme süresi doldu: hâlâ bir şey oynuyorsa çık."""
        if self._gorunur or self.medya.ekran_kilitli():
            return
        oynayan = self.medya.oynayanlar()
        if oynayan or self.secenek.her_zaman:
            self.goster(oynayan)

    def simdi(self):
        """Uygulamalar listesinden açıldı: medya olsun olmasın hemen çık."""
        if not self._gorunur:
            self.goster(self.medya.oynayanlar())

    def goster(self, oynayan=()):
        try:
            self.alistirma = Alistirma(self.ayar["kelime"])
        except Exception as hata:                       # bozuk ayar/kayıt mola'yı öldürmesin
            print(f"alıştırma hazırlanamadı: {hata}", file=sys.stderr)
            return
        self._renkler = tema_renkleri(self.alistirma.tema)
        self.duraklatilan = self.medya.duraklat(oynayan)
        adlar = []
        for ad in self.duraklatilan:
            k = self.medya.kimlik(ad)
            if k not in adlar:
                adlar.append(k)
        self.duraklatilan_ad = ", ".join(adlar)
        self._asama, self._sonuc = "yaziyor", ""
        self._rekor, self._rekor_bilgisi = False, ""
        self._gorunur = True
        self.degisti.emit()
        self.gorunurDegisti.emit()
        if self.secenek.otomatik_yaz:
            self._otomatik = list(self.alistirma.metin)
            hata_yeri = len(self._otomatik) // 3
            self._otomatik.insert(hata_yeri, "q" if self._otomatik[hata_yeri] != "q" else "w")
            QTimer.singleShot(int(self.secenek.otomatik_yaz * 1000), self._otomatik_adim)

    def _otomatik_adim(self):
        if not self._gorunur or self._asama != "yaziyor" or not self._otomatik:
            return
        self.tus(self._otomatik.pop(0))
        QTimer.singleShot(260, self._otomatik_adim)

    @Slot(str)
    def tus(self, c):
        a = self.alistirma
        if a is None or self._asama != "yaziyor" or len(c) != 1:
            return
        dogru = a.tus(c)
        if dogru is False:
            self.yanlis.emit()
        if a.bitti:
            ist = a.istatistik()
            if ist:
                self._sonuc = (f"{ist['dbk']:.0f} DBK   ·   %{ist['dogruluk']:.0f} "
                               f"doğruluk")
                self._rekor_degerlendir(ist)
            else:
                self._sonuc = "Tamam"
            self._asama = "bitti"
            self._kaydet()
            sure = self.ayar["sonuc_suresi_sn"] + (REKOR_EK_SURE_SN if self._rekor else 0)
            self.kapat_zamanlayici.start(int(sure * 1000))
        self.degisti.emit()

    def _rekor_degerlendir(self, ist):
        esik = self.ayar["rekor_en_az_dogruluk"]
        onceki, yeni = rekor_isle(ist, esik, kaydet=not self.secenek.kaydetme)
        self._rekor = yeni
        if yeni:
            fark = ist["dbk"] - onceki["dbk"]
            artis = f"{fark:.0f}" if fark >= 1 else f"{fark:.1f}"
            self._rekor_bilgisi = f"önceki en iyi {onceki['dbk']:.0f} DBK   (+{artis})"
        elif onceki is None:
            self._rekor_bilgisi = "ilk kayıt" if ist["dogruluk"] >= esik else ""
        elif ist["dogruluk"] < esik and ist["dbk"] > onceki["dbk"]:
            self._rekor_bilgisi = (f"en iyi {onceki['dbk']:.0f} DBK   ·   "
                                   f"rekor için %{esik:.0f} doğruluk")
        else:
            self._rekor_bilgisi = f"en iyi {onceki['dbk']:.0f} DBK"

    def _kaydet(self):
        if not self.ayar["ilerlemeye_kaydet"] or self.secenek.kaydetme:
            return
        if harfiyen_acik_mi():
            print("Harfiyen açık; ilerleme kaydedilmedi", file=sys.stderr)
            return
        try:
            self.alistirma.kaydet()
        except OSError as hata:
            print(f"ilerleme kaydedilemedi: {hata}", file=sys.stderr)

    @Slot()
    def atla(self):
        if self._gorunur:
            self.kapat()

    @Slot()
    def kapat(self):
        if not self._gorunur:
            return
        self.kapat_zamanlayici.stop()
        self._gorunur = False
        self.gorunurDegisti.emit()
        self.medya.surdur(self.duraklatilan)
        self.duraklatilan = []
        self.alistirma = None
        if self.secenek.bir_kez:
            QTimer.singleShot(300, QGuiApplication.quit)


# ---------------------------------------------------------------------------
# İzleme sayacı
# ---------------------------------------------------------------------------


class IzlemeSayaci(QObject):
    """Medya oynarken geçen süreyi biriktirir; `aralik` saniye dolunca `vakit` yayar.

    Yoklama yok: durum yalnızca MPRIS PropertiesChanged sinyalinde ve bir oynatıcı
    açılıp kapandığında yeniden okunur. Duraklatılan süre sayılmaz ama birikeni de
    silmez; ileri/geri sarma oynatma durumunu değiştirmediği için etkisizdir. Ancak
    `ara` saniyeden uzun süre hiçbir şey oynamazsa sayaç baştan başlar.
    """
    vakit = Signal()

    def __init__(self, medya, aralik, ara):
        super().__init__()
        self.medya = medya
        self.aralik = aralik
        self.birikmis = 0.0
        self.baslangic = None               # oynuyorsa oynamanın başladığı an
        self.dolum = QTimer(self, singleShot=True)
        self.dolum.timeout.connect(self._doldu)
        self.ara_zamanlayici = QTimer(self, singleShot=True)
        self.ara_zamanlayici.setInterval(int(ara * 1000))
        self.ara_zamanlayici.timeout.connect(self._ara_bitti)
        bus = QDBusConnection.sessionBus()
        if not bus.connect("", MPRIS_YOL, "org.freedesktop.DBus.Properties",
                           "PropertiesChanged", self, "1ozellikDegisti(QDBusMessage)"):
            print("MPRIS sinyallerine bağlanılamadı", file=sys.stderr)
        self.izleyici = QDBusServiceWatcher(MPRIS + "*", bus,
                                            QDBusServiceWatcher.WatchForOwnerChange, self)
        self.izleyici.serviceOwnerChanged.connect(self.degerlendir)
        self.degerlendir()

    @Slot(QDBusMessage)
    def ozellikDegisti(self, mesaj):
        arg = mesaj.arguments()
        if arg and arg[0] == OYNATICI:
            self.degerlendir()

    @property
    def oynuyor(self):
        return self.baslangic is not None

    def gecen(self):
        if self.oynuyor:
            return self.birikmis + time.monotonic() - self.baslangic
        return self.birikmis

    def degerlendir(self, *_):
        oynuyor = bool(self.medya.oynayanlar())
        if oynuyor == self.oynuyor:
            return
        if oynuyor:
            self.ara_zamanlayici.stop()
            self.baslangic = time.monotonic()
            self.dolum.start(max(0, int((self.aralik - self.birikmis) * 1000)))
        else:
            self.birikmis = self.gecen()
            self.baslangic = None
            self.dolum.stop()
            self.ara_zamanlayici.start()

    def _ara_bitti(self):
        self.birikmis = 0.0

    def sifirla(self):
        self.birikmis = 0.0
        if self.oynuyor:
            self.baslangic = time.monotonic()
            self.dolum.start(int(self.aralik * 1000))

    def _doldu(self):
        self.sifirla()          # gösterilemese de (ekran kilitli) yeni tur başlar
        self.vakit.emit()


def servise_ilet():
    """Servis çalışıyorsa ona "şimdi göster" de (sayacı da o sıfırlar)."""
    try:
        return subprocess.run(["systemctl", "--user", "kill", "-s", "USR1",
                               "--kill-whom=main", SERVIS],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=5).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def main(argv=None):
    p = argparse.ArgumentParser(prog="harfiyen-mola", description=__doc__.splitlines()[0])
    p.add_argument("--ac", action="store_true",
                   help="servis çalışıyorsa ona hemen göstermesini söyle, yoksa --simdi --her-zaman")
    p.add_argument("--simdi", action="store_true",
                   help="beklemeden hemen bir alıştırma göster ve çık")
    p.add_argument("--aralik", type=float, metavar="DK", help="kaç dakika izlemede bir çıkacağı")
    p.add_argument("--her-zaman", action="store_true",
                   help="medya oynamıyorken de göster")
    p.add_argument("--kaydetme", action="store_true", help="ilerlemeye yazma")
    p.add_argument("--klavyesiz", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--yalnizca-oynatici", metavar="AD", help=argparse.SUPPRESS)
    p.add_argument("--otomatik-yaz", type=float, metavar="SN", help=argparse.SUPPRESS)
    secenek = p.parse_args(argv)
    if secenek.ac:
        if servise_ilet():
            return 0
        secenek.simdi = secenek.her_zaman = True
    secenek.bir_kez = secenek.simdi

    ayar = ayarlari_yukle()
    if secenek.aralik:
        ayar["aralik_dk"] = secenek.aralik

    os.environ.setdefault("QT_QPA_PLATFORM", "wayland")
    uygulama = QGuiApplication(sys.argv[:1])
    uygulama.setApplicationName("harfiyen-mola")
    uygulama.setDesktopFileName("harfiyen-mola")
    uygulama.setQuitOnLastWindowClosed(False)

    mola = Mola(ayar, secenek)
    motor = QQmlApplicationEngine()
    motor.rootContext().setContextProperty("mola", mola)
    motor.rootContext().setContextProperty("klavyeAl", not secenek.klavyesiz)
    motor.load(QUrl.fromLocalFile(os.path.join(KOK, "mola.qml")))
    if not motor.rootObjects():
        return 1
    if secenek.otomatik_yaz:
        pencere = motor.rootObjects()[0]
        pencere.activeChanged.connect(
            lambda: print(f"klavye odağı: {pencere.isActive()}", file=sys.stderr, flush=True))

    # Sinyalleri olay döngüsüne soket üzerinden taşı (yoklama zamanlayıcısı yok).
    # SIGUSR1: uygulamalar listesinden açıldı (--ac) → hemen göster.
    okuyan, yazan = socket.socketpair()
    okuyan.setblocking(False)
    yazan.setblocking(False)
    signal.set_wakeup_fd(yazan.fileno())
    for s in (signal.SIGINT, signal.SIGTERM, signal.SIGUSR1):
        signal.signal(s, lambda *_: None)

    def sinyal_geldi(*_):
        for numara in okuyan.recv(64):
            if numara == signal.SIGUSR1:
                mola.simdi()
            else:
                uygulama.quit()

    bildirici = QSocketNotifier(okuyan.fileno(), QSocketNotifier.Read)
    bildirici.activated.connect(sinyal_geldi)

    if secenek.simdi:
        QTimer.singleShot(0, mola.simdi)
    else:
        sayac = IzlemeSayaci(mola.medya, ayar["aralik_dk"] * 60, ayar["ara_sifirla_dk"] * 60)
        sayac.vakit.connect(mola.vakit)
        # elle açılan mola da sayacı sıfırlar; ardından 10 dk daha rahat izlenir
        mola.gorunurDegisti.connect(lambda: mola._gorunur and sayac.sifirla())
    kod = uygulama.exec()
    mola.kapat()
    del motor                    # QML, `mola` silinmeden önce kapansın (kapanışta null uyarıları)
    return kod


if __name__ == "__main__":
    sys.exit(main())
