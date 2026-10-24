#!/usr/bin/env python3
"""Harfiyen birim testleri:  python3 -m unittest discover -s tests -t . -v"""

import datetime
import json
import os
import random
import socket
import struct
import tempfile
import threading
import unittest
from unittest import mock

import harfiyen as op

ANA_SIRA_KELIMELERI = ("ak al aş dal fal kal sal şal kaş laf saf kas ada aşk sakla "
                       "kasa kafa dalak salla kalas şaka kalk").split()


def ustalastir(il, harfler=None, hiz=None):
    for h in harfler or il.acik_harfler:
        for _ in range(il.pencere):
            il.deneme_kaydet(h, True, hiz)


class KelimeListesi(unittest.TestCase):
    def test_yalnizca_29_turkce_harf(self):
        for k in op.KELIMELER:
            with self.subTest(kelime=k):
                self.assertTrue(k, "boş kelime")
                self.assertLessEqual(set(k), op.HARFLER, f"izinsiz harf: {set(k) - op.HARFLER}")

    def test_ingilizce_yalnizca_26_harf(self):
        izinli = set(op.DILLER["en"]["harfler"])
        for k in op.KELIMELER_EN:
            with self.subTest(kelime=k):
                self.assertLessEqual(set(k), izinli)

    def test_en_az_300_tekil_kelime(self):
        for liste in (op.KELIMELER, op.KELIMELER_EN):
            self.assertGreaterEqual(len(liste), 300)
            self.assertEqual(len(liste), len(set(liste)))

    def test_ana_sira_kelimeleri_var_ve_yazilabilir(self):
        ana = op.SIRA[:op.BASLANGIC_ACIK]
        for k in ANA_SIRA_KELIMELERI:
            with self.subTest(kelime=k):
                self.assertIn(k, op.KELIMELER)
                self.assertTrue(op.yazilabilir_mi(k, ana))

    def test_sira_29_farkli_harf(self):
        self.assertEqual(len(op.SIRA), 29)
        self.assertEqual(set(op.SIRA), set(op.DILLER["tr"]["harfler"]))

    def test_hazir_metinler_yazilabilir(self):
        for dil, duzen in (("tr", op.Duzen("tr-q")), ("en", op.Duzen("us"))):
            for ad, metin in op.HAZIR_METINLER[dil]:
                kelimeler = op.metin_hazirla(metin, duzen)
                self.assertEqual(" ".join(kelimeler), " ".join(metin.split()), ad)


class YaziTipi(unittest.TestCase):
    def test_glifler_5x8(self):
        for c, glif in op.YAZI_TIPI.items():
            with self.subTest(c=c):
                self.assertEqual(len(glif), op.GLIF_Y)
                self.assertTrue(all(len(r) == op.GLIF_G for r in glif))

    def test_tum_harfler_ve_rakamlar_var(self):
        gerekli = set(op.DILLER["tr"]["harfler"] + op.DILLER["en"]["harfler"] + "0123456789.,;:!?'\"-")
        gerekli |= {op.buyuk_harf(c, "tr") for c in op.DILLER["tr"]["harfler"]}
        gerekli |= {c.upper() for c in op.DILLER["en"]["harfler"]}
        self.assertLessEqual(gerekli, set(op.YAZI_TIPI))

    def test_hucreler(self):
        kucuk = op.glif_hucreleri("a", 1)
        self.assertEqual((len(kucuk), len(kucuk[0])), (4, 5))
        buyuk = op.glif_hucreleri("a", 2)
        self.assertEqual((len(buyuk), len(buyuk[0])), (8, 10))
        self.assertEqual(op.glif_hucreleri("☃"), op.glif_hucreleri("☄"))  # bilinmeyen


class Duzenler(unittest.TestCase):
    def test_tr_q_parmak_haritasi_spec_ile_ayni(self):
        d = op.Duzen("tr-q")
        beklenen = {("sol", "serce"): "qaz<", ("sol", "yuzuk"): "wsx", ("sol", "orta"): "edc",
                    ("sol", "isaret"): "rtfgvb", ("sag", "isaret"): "yuhjnm",
                    ("sag", "orta"): "ıkö", ("sag", "yuzuk"): "olç", ("sag", "serce"): "pğüşi,."}
        for parmak, harfler in beklenen.items():
            for c in harfler:
                self.assertEqual(d.parmak(c), parmak, c)
        self.assertEqual(d.parmak(" "), op.BASPARMAK)

    def test_her_duzen_her_bicimde_dikdortgen(self):
        for kimlik in op.DUZENLER:
            for fiziksel in op.FIZIKSEL_DUZENLER:
                for numpad in (False, True):
                    d = op.Duzen(kimlik, fiziksel, numpad)
                    for sira in range(5):
                        ana = [k for k in d.tuslar if k.satir == sira and not k.numpad]
                        self.assertAlmostEqual(sum(k.g for k in ana), 15,
                                               msg=(kimlik, fiziksel, sira))
                    for u, hk in ((4, 1), (6, 2), (8, 3)):
                        kutular = d.tus_kutulari(0, 0, u, hk)
                        w, h = d.boyut(u, hk)
                        self.assertEqual(max(x1 for _, _, _, x1, _ in kutular), w)
                        self.assertEqual(max(y1 for *_, y1 in kutular), h - 1)
                        for _, x0, y0, x1, y1 in kutular:
                            self.assertLess(x0, x1)
                            self.assertLess(y0, y1)

    def test_fiziksel_duzenler(self):
        iso, ansi, ansi102 = (op.Duzen("tr-q", f) for f in op.FIZIKSEL_DUZENLER)
        self.assertEqual([k.satir for k in iso.tuslar if k.ad == "enter"], [1, 2])
        self.assertEqual([k.satir for k in ansi.tuslar if k.ad == "enter"], [2])
        self.assertEqual([k.satir for k in ansi102.tuslar if k.ad == "enter"], [2])
        self.assertIn("<", iso.karakterler)
        self.assertNotIn("<", ansi.karakterler)          # 101 tuşlu ANSI'de 102. tuş yok
        self.assertIn("<", ansi102.karakterler)           # 102 tuşlu ANSI'de var
        self.assertEqual(ansi102.tus("<").satir, 3)
        self.assertEqual(ansi102.tus(",").satir, 1)       # ek1 üst sıranın sonunda
        self.assertEqual(ansi.parmak(","), ("sag", "serce"))

    def test_numpad(self):
        d = op.Duzen("tr-q", "iso", True)
        self.assertEqual(len([k for k in d.tuslar if k.numpad]), 17)
        self.assertGreater(d.boyut(4, 1)[0], op.Duzen("tr-q").boyut(4, 1)[0])
        self.assertEqual(d.parmak("7"), ("sag", "isaret"))   # ana bloktaki 7, numpad değil

    def test_shift_cozumleme(self):
        d = op.Duzen("tr-q")
        self.assertEqual(d.cozumle("a"), ("a", False))
        self.assertEqual(d.cozumle("A"), ("a", True))
        self.assertEqual(d.cozumle("İ"), ("i", True))
        self.assertEqual(d.cozumle("I"), ("ı", True))
        self.assertEqual(d.cozumle(":"), (".", True))
        self.assertEqual(d.cozumle("?"), ("*", True))
        self.assertIsNone(d.cozumle("@"))                # AltGr gerektirir
        self.assertEqual(d.shift_tusu("A"), "shift_r")   # sol eldeki harf → sağ Shift
        self.assertEqual(d.shift_tusu("L"), "shift_s")
        self.assertIsNone(d.shift_tusu("a"))
        self.assertEqual(d.parmak("K"), ("sag", "orta"))
        us = op.Duzen("us")
        self.assertEqual(us.cozumle("I"), ("i", True))
        self.assertEqual(us.cozumle('"'), ("'", True))

    def test_mufredat(self):
        self.assertEqual(op.mufredat("tr", op.Duzen("tr-q")), op.SIRA)
        f = op.mufredat("tr", op.Duzen("tr-f"))
        self.assertEqual(f[:8], "akemiluy")
        self.assertEqual(sorted(f), sorted(op.DILLER["tr"]["harfler"]))
        en = op.mufredat("en", op.Duzen("us"))
        self.assertEqual(en[:7], "fjdksla")
        self.assertEqual(len(en), 26)
        with self.assertRaises(op.UyumsuzDuzen):
            op.mufredat("tr", op.Duzen("us"))


class Ustalik(unittest.TestCase):
    def test_pencere_dolmadan_ustalasmaz(self):
        il = op.Ilerleme()
        for _ in range(19):
            il.deneme_kaydet("f", True)
        self.assertFalse(il.ustalasti_mi("f"))
        il.deneme_kaydet("f", True)
        self.assertTrue(il.ustalasti_mi("f"))

    def test_tek_hata_ustaligi_bozar_ve_pencereden_cikinca_duzelir(self):
        il = op.Ilerleme()
        ustalastir(il, "f")
        il.deneme_kaydet("f", False)
        self.assertFalse(il.ustalasti_mi("f"))
        self.assertAlmostEqual(il.guven("f"), 19 / 20)
        for _ in range(19):
            il.deneme_kaydet("f", True)
        self.assertFalse(il.ustalasti_mi("f"))
        il.deneme_kaydet("f", True)
        self.assertTrue(il.ustalasti_mi("f"))

    def test_hiz_olcutu(self):
        il = op.Ilerleme(olcut="dogruluk_hiz", hedef_hiz=40)
        ustalastir(il, "f", hiz=30)
        self.assertFalse(il.ustalasti_mi("f"))
        self.assertAlmostEqual(il.guven("f"), 0.75)
        ustalastir(il, "f", hiz=45)
        self.assertTrue(il.ustalasti_mi("f"))
        self.assertAlmostEqual(il.hiz("f"), 45)

    def test_sayaclar(self):
        il = op.Ilerleme()
        il.deneme_kaydet("a", True)
        il.deneme_kaydet("a", False)
        self.assertEqual((il.deneme["a"], il.hata["a"]), (2, 1))

    def test_ozel_pencere(self):
        il = op.Ilerleme(pencere=5)
        for _ in range(5):
            il.deneme_kaydet("j", True)
        self.assertTrue(il.ustalasti_mi("j"))

    def test_gecersiz_pencere(self):
        with self.assertRaises(ValueError):
            op.Ilerleme(pencere=0)

    def test_ciftler_ve_ogrenme_hizi(self):
        il = op.Ilerleme()
        for _ in range(4):
            il.cift_kaydet("a", "k", False)
            il.cift_kaydet("a", "l", True)
        il.cift_kaydet("a", "x", False)                   # bilinmeyen harf yok sayılır
        self.assertEqual(il.zayif_ciftler(), ["ak"])
        for hiz in (20, 22, 24, 26):
            il.harf_tur_kaydet("f", hiz)
        self.assertAlmostEqual(il.ogrenme_hizi("f"), 2.0)
        self.assertIsNone(il.ogrenme_hizi("j"))

    def test_dogruluk_serisi(self):
        il = op.Ilerleme()
        for d in (90, 98, 99, 100):
            il.tur_kaydet({"dbk": 30, "dogruluk": d, "tutarlilik": 50})
        self.assertEqual(il.dogruluk_serisi(), 3)


class HarfAcilma(unittest.TestCase):
    def test_ana_sira_acik_baslar(self):
        il = op.Ilerleme()
        self.assertEqual(il.acik_harfler, "fjdkslaş")
        self.assertEqual(il.siradaki_harf, "e")
        self.assertEqual(il.guncel_harf, "ş")

    def test_hepsi_ustalasmadan_acilmaz(self):
        il = op.Ilerleme()
        ustalastir(il, "fjdksla")
        self.assertEqual(il.hazir_sayisi(), 7)
        self.assertIsNone(il.yeni_harf_dene())
        self.assertEqual(il.acik_sayisi, 8)

    def test_hepsi_ustalasinca_tek_harf_acilir(self):
        il = op.Ilerleme()
        ustalastir(il)
        self.assertEqual(il.yeni_harf_dene(), "e")
        self.assertEqual(il.acik_sayisi, 9)
        self.assertIsNone(il.yeni_harf_dene())
        ustalastir(il, "e")
        self.assertEqual(il.yeni_harf_dene(), "i")

    def test_son_harften_sonra_acilmaz(self):
        il = op.Ilerleme()
        il.acik_sayisi = 29
        ustalastir(il)
        self.assertIsNone(il.yeni_harf_dene())
        self.assertIsNone(il.siradaki_harf)

    def test_baska_mufredat(self):
        sira = op.mufredat("en", op.Duzen("us"))
        il = op.Ilerleme(sira=sira)
        self.assertEqual(il.acik_harfler, sira[:8])
        ustalastir(il)
        self.assertEqual(il.yeni_harf_dene(), sira[8])


class KelimeUretimi(unittest.TestCase):
    def test_uydurma_kelime(self):
        rng = random.Random(1)
        acik = "fjdkslaş"
        for odak in acik:
            for _ in range(50):
                k = op.uydurma_kelime(odak, acik, rng)
                self.assertIn(odak, k)
                self.assertTrue(3 <= len(k) <= 6)
                self.assertTrue(op.yazilabilir_mi(k, acik))
                sinif = [c in op.SESLILER for c in k]
                self.assertTrue(all(a != b for a, b in zip(sinif, sinif[1:])), k)

    def test_satirlar_yalnizca_acik_harfler(self):
        rng = random.Random(42)
        for acik_sayisi in (8, 12, 20, 29):
            il = op.Ilerleme()
            il.acik_sayisi = acik_sayisi
            izinli = set(il.acik_harfler) | {" "}
            for _ in range(200):
                satir = op.satir_uret(il, rng)
                kelimeler = satir.split(" ")
                self.assertLessEqual(set(satir), izinli)
                self.assertLessEqual(len(satir), op.SATIR_KARAKTER)
                self.assertTrue(1 <= len(kelimeler) <= op.SATIR_KELIME)
                self.assertTrue(all(kelimeler), satir)
                for a, b in zip(kelimeler, kelimeler[1:]):
                    self.assertNotEqual(a, b, satir)

    def test_zayif_mod_ciftleri_kullanir(self):
        il = op.Ilerleme()
        rng = random.Random(4)
        metin = " ".join(op.satir_uret(il, rng, agirlik=op.zayif_agirliklari(il), ciftler=["kş"])
                         for _ in range(50))
        self.assertGreater(metin.count("kş"), 20)
        self.assertLessEqual(set(metin), set(il.acik_harfler) | {" "})

    def test_zayif_agirliklari_zayif_harfi_one_cikarir(self):
        il = op.Ilerleme()
        ustalastir(il, "fjdklaş", hiz=40)
        for _ in range(10):
            il.deneme_kaydet("s", False)
        w = op.zayif_agirliklari(il)
        self.assertEqual(max(w, key=w.get), "s")

    def test_susle(self):
        duzen, rng = op.Duzen("tr-q"), random.Random(2)
        satir = "kal şal ak kalfa salsa kalas laja aksa"
        self.assertEqual(op.susle(satir, rng, duzen, "tr"), satir)
        for _ in range(100):
            s = op.susle(satir, rng, duzen, "tr", buyuk=True, noktalama=True, rakam=True)
            self.assertLessEqual(len(s), op.SATIR_KARAKTER)
            self.assertTrue(all(duzen.yazilabilir_mi(c) for c in s), s)
        s = op.susle(satir, random.Random(5), duzen, "tr", buyuk=True)
        self.assertTrue(s[0].isupper())                   # cümle başı büyük

    def test_metin_satirlari(self):
        duzen = op.Duzen("tr-q")
        kelimeler = op.metin_hazirla("“Merhaba” — dünya… Şâir\tgeldi.", duzen)
        self.assertEqual(kelimeler, ['"Merhaba"', "-", "dünya...", "Şair", "geldi."])
        satir, son, sarildi = op.metin_satiri(kelimeler, 0, 20)
        self.assertEqual((satir, son, sarildi), ('"Merhaba" - dünya...', 3, False))
        satir, son, sarildi = op.metin_satiri(kelimeler, 5, 20)
        self.assertTrue(sarildi)
        self.assertTrue(satir.startswith('"Merhaba"'))

    def test_ingilizce_satirlar(self):
        sira = op.mufredat("en", op.Duzen("us"))
        il = op.Ilerleme(sira=sira)
        rng = random.Random(9)
        for _ in range(100):
            satir = op.satir_uret(il, rng, kelimeler=op.KELIMELER_EN,
                                  sesliler=frozenset(op.DILLER["en"]["sesliler"]))
            self.assertLessEqual(set(satir), set(il.acik_harfler) | {" "})

    def test_dar_satir(self):
        self.assertLessEqual(len(op.satir_uret(op.Ilerleme(), random.Random(3), max_karakter=20)), 20)

    def test_odak_agirliklari(self):
        il = op.Ilerleme()
        ustalastir(il, "fjdksla")
        w = op.odak_agirliklari(il)
        self.assertAlmostEqual(w["f"], op.TABAN_AGIRLIK)
        self.assertAlmostEqual(w["ş"], op.TABAN_AGIRLIK + 1 + op.YENI_HARF_AGIRLIGI)


class TurVeOyun(unittest.TestCase):
    def test_tur_istatistikleri(self):
        t = op.tur_istatistikleri([i * 1.0 for i in range(11)], 0)
        self.assertAlmostEqual(t["dbk"], 12.0)
        self.assertAlmostEqual(t["dogruluk"], 100.0)
        self.assertAlmostEqual(t["tutarlilik"], 100.0)
        self.assertEqual(op.tur_istatistikleri([0, 0.01, 0.02, 0.03, 10], 0)["tutarlilik"], 0.0)
        self.assertIsNone(op.tur_istatistikleri([1.0], 0))

    def test_seviye(self):
        self.assertEqual(op.seviye_hesapla(0), (1, 0, 250))
        self.assertEqual(op.seviye_hesapla(249)[0], 1)
        self.assertEqual(op.seviye_hesapla(250), (2, 250, 750))
        self.assertEqual(op.seviye_hesapla(1500)[0], 4)

    def test_gun_serisi(self):
        bugun = datetime.date(2026, 9, 30)
        gunler = {(bugun - datetime.timedelta(days=i)).isoformat(): 1800 for i in range(1, 4)}
        self.assertEqual(op.gun_serisi(gunler, 1800, bugun.isoformat()), 3)   # bugün henüz yok
        gunler[bugun.isoformat()] = 1800
        self.assertEqual(op.gun_serisi(gunler, 1800, bugun.isoformat()), 4)
        gunler[(bugun - datetime.timedelta(days=2)).isoformat()] = 100      # kopukluk
        self.assertEqual(op.gun_serisi(gunler, 1800, bugun.isoformat()), 2)
        self.assertEqual(op.gun_serisi(gunler, 0, bugun.isoformat()), 4)      # hedef yok: 1 dk

    def test_puan(self):
        self.assertGreater(op.puan_hesapla(50, 100, 10), op.puan_hesapla(50, 90, 10))
        self.assertGreater(op.puan_hesapla(50, 95, 20), op.puan_hesapla(50, 95, 10))

    def test_rozet_kosullari(self):
        durum = {"satir": 1, "acik": 9, "toplam": 29, "kusursuz": False, "dogruluk_serisi": 0,
                 "en_iyi_dbk": 31, "hedef_bugun": False, "seri": 0, "bugun_dk": 5,
                 "test_sayisi": 0, "en_iyi_test": 0, "gece": False}
        kazanilan = {k for k, *_, kosul in op.ROZETLER if kosul(durum)}
        self.assertEqual(kazanilan, {"ilk_satir", "ana_sira", "hiz_30"})
        self.assertEqual(len({r[0] for r in op.ROZETLER}), len(op.ROZETLER))


class Temalar(unittest.TestCase):
    def test_yerlesik_temalar_gecerli(self):
        temalar, uyarilar = op.temalari_yukle("/olmayan/dizin")
        self.assertEqual(uyarilar, [])
        for kimlik, tema in temalar.items():
            self.assertEqual(op.tema_dogrula(kimlik, tema), [])

    def test_kullanici_temasi_miras_ve_hata(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "benim.json"), "w") as f:
                json.dump({"ad": "Benim", "miras": "gunduz", "vurgu": "#123456",
                           "parmak": {"serce": "red"}, "tus_karisim": 0.3}, f)
            with open(os.path.join(d, "bozuk.json"), "w") as f:
                json.dump({"vurgu": "mavimsi", "parmak": {"orta": "yok-renk"}, "tus_karisim": 3}, f)
            with open(os.path.join(d, "json-degil.json"), "w") as f:
                f.write("{")
            temalar, uyarilar = op.temalari_yukle(d)
        self.assertEqual(temalar["benim"]["vurgu"], "#123456")
        self.assertEqual(temalar["benim"]["zemin"], op.YERLESIK_TEMALAR["gunduz"]["zemin"])
        self.assertEqual(temalar["benim"]["parmak"]["serce"], "red")
        self.assertEqual(op.tema_dogrula("bozuk", temalar["bozuk"]), [])
        self.assertTrue(any("bozuk" in u for u in uyarilar))
        self.assertTrue(any("json-degil" in u for u in uyarilar))

    def test_renk_cozme_ve_karistirma(self):
        self.assertEqual(op.renk_coz("#fff"), ("rgb", (255, 255, 255)))
        self.assertEqual(op.renk_coz("red"), ("indeks", 1))
        self.assertEqual(op.renk_coz(None), ("yok",))
        for kotu in ("#12", "turuncu", 300, True):
            with self.assertRaises(ValueError):
                op.renk_coz(kotu)
        self.assertEqual(op.karistir((200, 100, 0), (0, 0, 0), 0.5), (100, 50, 0))
        self.assertEqual(op.renk_rgb(196), op.xterm_rgb(196))
        self.assertIsNone(op.renk_rgb(None))
        self.assertLess(op.parlaklik((0, 0, 0)), op.parlaklik((255, 255, 255)))
        self.assertEqual(op.renk_numarasi("#000000", 256), 16)
        self.assertEqual(op.renk_numarasi("#ff0000", 8), 1)


class Ayarlar(unittest.TestCase):
    def test_dogrulama(self):
        ham = {"tema": "gece", "klavye": "tr-f", "numpad": "evet", "ustalik_penceresi": 500,
               "tus_araligi_mm": 18, "fiziksel": "ansi102", "bilinmeyen": 1,
               "klavye_boyutu": "otomatik", "_not": "yok sayılır"}
        ayarlar, uyarilar = op.ayar_dogrula(ham, op.YERLESIK_TEMALAR)
        self.assertEqual(ayarlar["tema"], "gece")
        self.assertEqual(ayarlar["fiziksel"], "ansi102")
        self.assertEqual(ayarlar["klavye_boyutu"], "otomatik_k")   # eski yazım
        self.assertEqual(ayarlar["numpad"], op.VARSAYILAN_AYARLAR["numpad"])
        self.assertEqual(ayarlar["ustalik_penceresi"], op.PENCERE)
        self.assertEqual(ayarlar["tus_araligi_mm"], 18.0)
        self.assertEqual(len(uyarilar), 3)

    def test_degistirme(self):
        a = dict(op.VARSAYILAN_AYARLAR)
        op.ayar_degistir(a, "klavye", 1, op.YERLESIK_TEMALAR)
        self.assertEqual(a["klavye"], "tr-f")
        op.ayar_degistir(a, "fiziksel", -1, op.YERLESIK_TEMALAR)
        self.assertEqual(a["fiziksel"], "ansi102")
        op.ayar_degistir(a, "ustalik_penceresi", 10, op.YERLESIK_TEMALAR)
        self.assertEqual(a["ustalik_penceresi"], 50)
        op.ayar_degistir(a, "tus_araligi_mm", -1, op.YERLESIK_TEMALAR)
        self.assertEqual(a["tus_araligi_mm"], 18.9)

    def test_her_ayar_sayfada_ve_adli(self):
        sayfadaki = [a for _, liste in op.AYAR_SAYFASI for a in liste]
        self.assertEqual(sorted(sayfadaki), sorted(op.VARSAYILAN_AYARLAR))
        self.assertEqual(set(op.AYAR_KURALLARI), set(op.VARSAYILAN_AYARLAR))
        for dil in op.METINLER:
            self.assertEqual(set(op.METINLER[dil]["ayar_adlari"]), set(op.VARSAYILAN_AYARLAR))
            for kural in op.AYAR_KURALLARI.values():
                if kural[0] == "secim":
                    for deger in kural[1]:
                        if isinstance(deger, str) and deger not in op.DUZENLER \
                                and deger not in op.DILLER and deger not in ("tr", "en"):
                            self.assertIn(deger, op.METINLER[dil]["degerler"], (dil, deger))

    def test_metin_anahtarlari_ayni(self):
        self.assertEqual(set(op.METINLER["tr"]), set(op.METINLER["en"]))
        self.assertEqual(len(op.METINLER["tr"]["yardim"]), len(op.METINLER["en"]["yardim"]))

    def test_eski_dizinler_tasinir(self):
        with tempfile.TemporaryDirectory() as d:
            eski, yeni = os.path.join(d, "eski"), os.path.join(d, "yeni")
            os.makedirs(eski)
            with open(os.path.join(eski, "ayarlar.json"), "w") as f:
                f.write("{}")
            with mock.patch.multiple(op, ESKI_AYAR_DIZINI=eski, AYAR_DIZINI=yeni,
                                     ESKI_VERI_DIZINI=os.path.join(d, "yok"),
                                     VERI_DIZINI=os.path.join(d, "veri")):
                self.assertEqual(op.eski_dizinleri_tasi(), [yeni])
                self.assertTrue(os.path.exists(os.path.join(yeni, "ayarlar.json")))
                self.assertEqual(op.eski_dizinleri_tasi(), [])      # ikinci kez dokunmaz


class KutuCizimi(unittest.TestCase):
    def test_tek_kutu(self):
        c = op.kutu_cizgileri([(0, 0, 2, 2)])
        self.assertEqual(["".join(c.get((x, y), " ") for x in range(3)) for y in range(3)],
                         ["╭─╮", "│ │", "╰─╯"])

    def test_silinen_cizgi(self):
        c = op.Cizim()
        c.kutu(0, 0, 2, 2)
        c.kutu(0, 2, 2, 4)
        c.yatay_sil(0, 2, 2)
        self.assertEqual([c.karakterler()[(0, y)] for y in range(5)], list("╭│││╰"))

    def test_cubuk_ve_kivilcim(self):
        self.assertEqual(op.cizgi_cubugu(0.85, 20), (17, 3))
        self.assertEqual(op.cizgi_cubugu(1.5, 4), (4, 0))
        self.assertEqual(op.kivilcim([1, 2, 3], 10), "▁▄█")


class Yerlesim(unittest.TestCase):
    SECENEK = {"panel": True, "yazi_boyutu": "normal", "klavye_boyutu": "otomatik_k",
               "sonraki": True}

    def dogrula(self, d, h, w):
        kartlar = [d[k] for k in ("ozet", "yazi", "klavye", "grafik") if d[k]]
        for a, b in zip(kartlar, kartlar[1:]):
            self.assertLess(a[3], b[1])                      # üst üste binmez
        self.assertEqual(kartlar[-1][3], h - 1 - (op.GOSTERGE_Y if d["gosterge_y"] else 0))
        if d["panel"]:
            self.assertLess(d["x1"], d["panel"][0])
            self.assertEqual(d["panel"][2], w - 1)
        if d["klavye"]:
            x0, y0, x1, y1 = d["klavye"]
            self.assertLessEqual(d["kb_w"] + 2, x1 - x0 - 1)
            self.assertLessEqual(d["kb_h"] + 2, y1 - y0 - 1)

    def test_boyutlar(self):
        d = op.Duzen()
        for h, w in ((24, 100), (32, 114), (38, 125), (50, 180), (70, 239)):
            for numpad in (False, True):
                for gosterge in (False, True):
                    for yb in op.YAZI_BOYUTLARI:
                        s = dict(self.SECENEK, gosterge=gosterge, yazi_boyutu=yb)
                        y = op.yerlesim_hesapla(h, w, op.Duzen("tr-q", "iso", numpad), 29, s)
                        if y:
                            with self.subTest(h=h, w=w, numpad=numpad, gosterge=gosterge, yb=yb):
                                self.dogrula(y, h, w)
        self.assertIsNone(op.yerlesim_hesapla(22, 72, d, 29, self.SECENEK))

    def test_tam_ekranda_buyur(self):
        d = op.Duzen()
        kucuk = op.yerlesim_hesapla(32, 114, d, 29, self.SECENEK)
        buyuk = op.yerlesim_hesapla(70, 239, d, 29, self.SECENEK)
        self.assertGreater(buyuk["u"], kucuk["u"])
        self.assertIsNotNone(buyuk["grafik"])
        self.assertLessEqual(buyuk["hk"], 2)               # otomatik klavye çok uzamaz
        dev = op.yerlesim_hesapla(70, 239, d, 29, dict(self.SECENEK, yazi_boyutu="dev"))
        self.assertEqual(dev["yb"], "dev")

    def test_klavye_boyutu_ayari(self):
        d = op.Duzen()
        for boyut, hk in (("kompakt", 1), ("orta", 2), ("buyuk", 3), ("gizli", 0)):
            y = op.yerlesim_hesapla(70, 239, d, 29, dict(self.SECENEK, klavye_boyutu=boyut))
            self.assertEqual(y["hk"], hk, boyut)
            self.assertEqual(y["klavye"] is None, hk == 0)

    def test_tus_kenari_ve_uzun_otomatik(self):
        self.assertEqual(op.kenar_satirlari("derinlik", 4), 1)
        self.assertEqual(op.kenar_satirlari("duz", 5), 1)
        self.assertEqual(op.kenar_satirlari("derinlik", 6), 2)      # 6/8 kenar + 3/8 boşluk
        self.assertEqual(op.kenar_satirlari("derinlik", 16), 3)
        self.assertEqual(op.kenar_satirlari("yuzen", 16), 1)        # yüzen: kenar yok
        d = op.Duzen()
        self.assertEqual(d.boyut(4, 2, 2)[1], 20)
        kutular = d.tus_kutulari(0, 0, 4, 2, 2)
        a = next(k for k in kutular if k[0].karakter == "a")
        self.assertEqual((a[2], a[4]), (8, 10))                     # 3. sıra: 2·(2+2)
        uzun = op.yerlesim_hesapla(70, 239, d, 29, dict(self.SECENEK, klavye_boyutu="otomatik_uzun"))
        self.assertEqual(uzun["hk"], 3)
        kalin = op.yerlesim_hesapla(70, 239, d, 29, dict(self.SECENEK, tus_kenar=12))
        self.assertEqual(kalin["ek"], 2)
        self.assertEqual(kalin["kb_h"], 5 * (kalin["hk"] + 2))
        self.dogrula(kalin, 70, 239)

    def test_sigmayan_istek_kuculur(self):
        y = op.yerlesim_hesapla(32, 114, op.Duzen(), 29, dict(self.SECENEK, yazi_boyutu="dev"))
        self.assertIn(y["yb"], ("normal", "buyuk"))

    def test_gereken_boyut_yeterli(self):
        for numpad in (False, True):
            d = op.Duzen("tr-q", "iso", numpad)
            w, h = op.gereken_boyut(d, 29, self.SECENEK)
            y = op.yerlesim_hesapla(h, w, d, 29, self.SECENEK)
            self.assertIsNotNone(y)
            self.assertIsNotNone(y["panel"])
            self.assertTrue(y["tek"])
            self.assertGreaterEqual(y["u"], 6)

    def test_yazi_alti_parmaklar(self):
        d = op.Duzen()
        acik = dict(self.SECENEK, yazi_parmak=True)
        kapali = op.yerlesim_hesapla(50, 180, d, 29, self.SECENEK)
        y = op.yerlesim_hesapla(50, 180, d, 29, acik)
        self.assertIsNone(kapali["parmak"])
        self.assertEqual(y["parmak"], "gosterge")
        self.dogrula(y, 50, 180)
        self.assertEqual(op.yazi_ic_yuksekligi("normal", True, "gosterge")
                         - op.yazi_ic_yuksekligi("normal", True), 1 + op.GOSTERGE_Y)
        # klavye gizliyse ayar kapalıyken de çipler yazı kartında
        gizli = op.yerlesim_hesapla(50, 180, d, 29, dict(self.SECENEK, klavye_boyutu="gizli"))
        self.assertEqual(gizli["parmak"], "cip")
        # sığmazsa düşer, kart düzeni bozulmaz
        for h in range(22, 50):
            for w in (80, 114):
                y = op.yerlesim_hesapla(h, w, d, 29, acik)
                if y:
                    with self.subTest(h=h, w=w):
                        self.dogrula(y, h, w)
        w, h = op.gereken_boyut(d, 29, acik)
        self.assertEqual(op.yerlesim_hesapla(h, w, d, 29, acik)["parmak"], "gosterge")

    def test_yazi_gosterge_konumlari(self):
        d = op.Duzen()
        sira = [("sol", "serce"), ("sol", "yuzuk"), ("sol", "orta"), ("sol", "isaret"),
                ("sol", "basparmak"), ("sag", "basparmak"), ("sag", "isaret"),
                ("sag", "orta"), ("sag", "yuzuk"), ("sag", "serce")]
        for genislik in (78, 110, 160, 300):
            k = op.yazi_gosterge_konumlari(d, genislik)
            with self.subTest(genislik=genislik):
                xs = [k[p] for p in sira]
                for a, b in zip(xs, xs[1:]):
                    self.assertGreaterEqual(b - a, 7)          # adlar ve çubuklar çakışmaz
                self.assertGreaterEqual(xs[0] - 3, 0)
                self.assertLessEqual(xs[-1] + 4, genislik)
                self.assertLessEqual(abs((xs[0] + xs[-1]) - genislik), 2)    # ortalı
        self.assertIsNone(op.yazi_gosterge_konumlari(d, 60))

    def test_el_cipleri(self):
        metinler = ["Sol", "serçe", "yüzük", "orta", "işaret", "başparmak", "işaret", "orta",
                    "yüzük", "serçe", "Sağ"]
        konumlar = op.el_cipleri(100, metinler)
        for (x, g), (x2, _) in zip(konumlar, konumlar[1:]):
            self.assertEqual(x2, x + g + 1)
        self.assertLessEqual(konumlar[-1][0] + konumlar[-1][1], 100)


class Gostergeler(unittest.TestCase):
    AYAR = {"ekran_genisligi_mm": 300, "tus_araligi_mm": 19.0, "gosterge_olcek": 100,
            "gosterge_kaydirma_mm": 0}

    def test_tam_ekran_simetrik_ve_sirali(self):
        k = op.gosterge_konumlari(op.Duzen(), 240, self.AYAR)
        sira = [("sol", "serce"), ("sol", "yuzuk"), ("sol", "orta"), ("sol", "isaret"),
                ("sol", "basparmak"), ("sag", "basparmak"), ("sag", "isaret"),
                ("sag", "orta"), ("sag", "yuzuk"), ("sag", "serce")]
        self.assertEqual([k[p] for p in sira], sorted(k[p] for p in sira))
        self.assertAlmostEqual(k[("sag", "isaret")] - k[("sol", "isaret")], 45.6, delta=1.5)

    def test_kaydirma_ve_pencere(self):
        d = op.Duzen()
        temel = op.gosterge_konumlari(d, 240, self.AYAR)
        kaymis = op.gosterge_konumlari(d, 240, dict(self.AYAR, gosterge_kaydirma_mm=10))
        for p in temel:
            self.assertAlmostEqual(kaymis[p] - temel[p], 8, delta=1)
        k = op.gosterge_konumlari(d, 120, self.AYAR, {"x": 0, "g": 960, "ex": 0, "eg": 1920})
        self.assertEqual(k[("sol", "isaret")], 86)

    def test_ok_isareti(self):
        self.assertEqual(op.ok_isareti(0, 0), "•")
        self.assertEqual(op.ok_isareti(-0.75, -1), "↖")
        self.assertEqual(op.ok_isareti(1, 0), "→")


class Kayit(unittest.TestCase):
    def test_gidis_donus(self):
        il = op.Ilerleme()
        ustalastir(il, hiz=30)
        il.yeni_harf_dene()
        il.deneme_kaydet("e", False)
        il.cift_kaydet("a", "e", False)
        il.harf_tur_kaydet("f", 33.3)
        il.tur_kaydet({"dbk": 30.0, "dogruluk": 95.0, "tutarlilik": 70.0})
        il.test_kaydet({"dbk": 41.0, "dogruluk": 97.0, "sure": 60})
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "alt", "progress.json")
            depo = op.IlerlemeDeposu(yol)
            depo.genel["xp"] = 123
            depo.kaydet("tr/tr-q", il)
            depo2 = op.IlerlemeDeposu(yol)
            geri = depo2.profil("tr/tr-q", 20, op.SIRA)
        self.assertEqual(geri.acik_sayisi, 9)
        self.assertEqual(geri.gecmis, il.gecmis)
        self.assertEqual(geri.hizlar["f"][-1], 30)
        self.assertEqual(geri.harf_turlari["f"], [33.3])
        self.assertEqual(geri.ciftler, {"ae": [1, 1]})
        self.assertEqual(geri.testler[-1]["dbk"], 41.0)
        self.assertEqual(depo2.genel["xp"], 123)
        self.assertEqual(depo2.en_iyi("testler"), 41.0)
        self.assertEqual(depo2.test_sayisi(), 1)

    def test_eski_bicimler_tasinir(self):
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "p.json")
            with open(yol, "w") as f:
                json.dump({"surum": 1, "acik_harf_sayisi": 10,
                           "harfler": {"f": {"gecmis": [1, 1], "deneme": 2, "hata": 0}}}, f)
            depo = op.IlerlemeDeposu(yol)
            il = depo.profil("tr/tr-q", 20, op.SIRA)
            self.assertEqual(il.acik_sayisi, 10)
            self.assertEqual(depo.genel["xp"], 0)
            with open(yol, "w") as f:
                json.dump({"surum": 2, "profiller": {"tr/tr-q": {"acik_harf_sayisi": 9}}}, f)
            self.assertEqual(op.IlerlemeDeposu(yol).profil("tr/tr-q", 20, op.SIRA).acik_sayisi, 9)

    def test_sifirlama(self):
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "p.json")
            depo = op.IlerlemeDeposu(yol)
            il = op.Ilerleme()
            ustalastir(il, hiz=30)
            il.yeni_harf_dene()
            depo.genel["xp"] = 50
            depo.kaydet("tr/tr-q", il)
            depo.kaydet("en/us", il)
            depo.sifirla("tr/tr-q")                       # yalnızca bu profil
            depo2 = op.IlerlemeDeposu(yol)
            self.assertEqual(depo2.profil("tr/tr-q", 20, op.SIRA).acik_sayisi, op.BASLANGIC_ACIK)
            self.assertEqual(depo2.profil("en/us", 20, op.SIRA).acik_sayisi, 9)
            self.assertEqual(depo2.genel["xp"], 50)
            yedek = op.IlerlemeDeposu(yol + ".yedek")
            self.assertEqual(yedek.profil("tr/tr-q", 20, op.SIRA).acik_sayisi, 9)
            depo2.sifirla()                               # tümü
            depo3 = op.IlerlemeDeposu(yol)
            self.assertEqual(depo3.veri["profiller"], {})
            self.assertEqual(depo3.genel, op._yeni_genel())
            self.assertEqual(op.IlerlemeDeposu(yol + ".yedek").genel["xp"], 50)

    def test_bozuk_dosya_yedeklenir(self):
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "p.json")
            with open(yol, "w") as f:
                f.write("{bozuk")
            depo = op.IlerlemeDeposu(yol)
            self.assertIsNotNone(depo.uyari)
            self.assertTrue(os.path.exists(yol + ".bozuk"))


def _dizge(metin):
    b = metin.encode() + b"\0"
    return struct.pack("<H", len(b)) + b


def denetleyici_verisi(ad, tur, ledler, renkler, modlar=("Direct", "Rainbow"), etkin=1):
    """OpenRGB denetleyici verisi (protokol 3) — sahte sunucu için."""
    g = struct.pack("<i", tur) + _dizge(ad) + b"".join(_dizge(x) for x in ("s", "a", "1", "sn", "k"))
    g += struct.pack("<Hi", len(modlar), etkin)
    for i, m in enumerate(modlar):
        g += _dizge(m) + struct.pack("<iI", i, 0) + struct.pack("<10I", *range(10)) + struct.pack("<H", 0)
    n = len(ledler)
    g += struct.pack("<H", 1) + _dizge("Tuşlar") + struct.pack("<iIII", 2, n, n, n)
    g += struct.pack("<H", 8) + struct.pack("<II", 1, 1) + struct.pack("<I", 0)   # 1×1 matris
    g += struct.pack("<H", n) + b"".join(_dizge(l) + struct.pack("<I", i) for i, l in enumerate(ledler))
    g += struct.pack("<H", n) + b"".join(bytes((*r, 0)) for r in renkler)
    return struct.pack("<I", len(g) + 4) + g


class SahteOpenRGB(threading.Thread):
    """Tek bağlantılık sahte SDK sunucusu; gelen LED ve mod paketlerini kaydeder."""

    def __init__(self, cihazlar):
        super().__init__(daemon=True)
        self.cihazlar, self.paketler = cihazlar, []
        self.dinleyici = socket.socket()
        self.dinleyici.bind(("127.0.0.1", 0))
        self.dinleyici.listen(1)
        self.port = self.dinleyici.getsockname()[1]

    def run(self):
        baglanti, _ = self.dinleyici.accept()
        with baglanti:
            while True:
                bas = b""
                while len(bas) < 16:
                    parca = baglanti.recv(16 - len(bas))
                    if not parca:
                        return
                    bas += parca
                cihaz, kimlik, boy = struct.unpack("<III", bas[4:])
                veri = b""
                while len(veri) < boy:
                    veri += baglanti.recv(boy - len(veri))
                self.paketler.append((cihaz, kimlik, veri))
                yanit = {40: struct.pack("<I", 6), 0: struct.pack("<I", len(self.cihazlar)),
                         1: self.cihazlar[cihaz] if kimlik == 1 else None}.get(kimlik)
                if yanit is not None:
                    baglanti.sendall(b"ORGB" + struct.pack("<III", cihaz, kimlik, len(yanit)) + yanit)


class TusIsiklari(unittest.TestCase):
    def test_konumlar_tam_ve_tekil(self):
        for fiziksel in op.FIZIKSEL_DUZENLER:
            konumlar = [k for t, k in op.Duzen("tr-q", fiziksel, True).led_konumlari()]
            enter = 2 if fiziksel == "iso" else 1                # ISO Enter iki parçalı
            self.assertEqual(konumlar.count("Enter"), enter)
            self.assertEqual(len(set(konumlar)), len(konumlar) - (enter - 1))
        d = dict((t.karakter, k) for t, k in op.Duzen("tr-q").led_konumlari() if t.karakter)
        self.assertEqual((d["ş"], d["i"], d[","], d["<"], d["ğ"]), (";", "'", "#", "\\ (ISO)", "["))
        f = dict((t.karakter, k) for t, k in op.Duzen("tr-f").led_konumlari() if t.karakter)
        self.assertEqual((f["a"], f["k"], f["f"]), ("F", "J", "Q"))

    def test_led_eslestirme(self):
        ledler = ["Key: A", "Key: Left Ctrl", "Key: Numpad 7", "LED: Logo", "Key: \\",
                  "Key: Spacebar", "Key: Grave"]
        e = op.led_eslestir(ledler, ["A", "Left Control", "Number Pad 7", "\\ (ANSI)", "Space",
                                     "`", "Q"])
        self.assertEqual(e, {"A": 0, "Left Control": 1, "Number Pad 7": 2, "\\ (ANSI)": 4,
                             "Space": 5, "`": 6})

    def test_denetleyici_cozumleme(self):
        veri = denetleyici_verisi("Klavye", 5, ["Key: A", "Key: B"], [(1, 2, 3), (4, 5, 6)])
        d = op.OpenRGBIstemci.denetleyici_coz(veri)
        self.assertEqual((d["tur"], d["ad"], d["etkin_mod"]), (5, "Klavye", 1))
        self.assertEqual([m[0] for m in d["modlar"]], ["Direct", "Rainbow"])
        self.assertEqual(d["ledler"], ["Key: A", "Key: B"])
        self.assertEqual(d["renkler"], [(1, 2, 3), (4, 5, 6)])

    def test_sunucuyla_bagla_gonder_geri_yukle(self):
        konumlar = [k for _, k in op.Duzen().led_konumlari()]
        ledler = ["Key: " + k for k in dict.fromkeys(konumlar)]
        ilk = [(0, 0, 90)] * len(ledler)
        sunucu = SahteOpenRGB([denetleyici_verisi("Fare", 3, ["Key: A"], [(0, 0, 0)]),
                               denetleyici_verisi("Klavye", 5, ledler, ilk)])
        sunucu.start()
        ist = op.OpenRGBIstemci(f"127.0.0.1:{sunucu.port}")
        self.assertEqual(ist.baglan(konumlar), "Klavye")
        self.assertEqual(ist.cihaz["sira"], 1)
        renkler = [(0, 0, 0)] * len(ledler)
        renkler[ist.cihaz["eslesme"]["A"]] = (255, 200, 0)
        ist.renkleri_gonder(renkler)
        ist.renkleri_gonder(renkler)                      # değişmediyse ikinci kez gitmez
        ist.geri_yukle()
        sunucu.join(2)
        kimlikler = [(c, k) for c, k, _ in sunucu.paketler]
        self.assertIn((1, 1100), kimlikler)               # doğrudan kip
        ledler_paketleri = [v for c, k, v in sunucu.paketler if k == 1050]
        self.assertEqual(len(ledler_paketleri), 2)        # bir güncelleme + geri yükleme
        boy, sayi = struct.unpack_from("<IH", ledler_paketleri[0])
        self.assertEqual((boy, sayi), (4 + 2 + 4 * len(ledler), len(ledler)))
        i = 6 + 4 * ist_eslesme_a(konumlar, ledler)
        self.assertEqual(ledler_paketleri[0][i:i + 3], bytes((255, 200, 0)))
        self.assertEqual(ledler_paketleri[1][6:9], bytes((0, 0, 90)))
        mod = [v for c, k, v in sunucu.paketler if k == 1101][0]
        self.assertEqual(struct.unpack_from("<Ii", mod), (len(mod), 1))   # etkin mod: Rainbow
        self.assertFalse(ist.bagli)

    def test_baglanti_hatasi(self):
        dinleyici = socket.socket()
        dinleyici.bind(("127.0.0.1", 0))
        port = dinleyici.getsockname()[1]
        dinleyici.close()
        with self.assertRaises(op.OpenRGBHatasi):
            op.OpenRGBIstemci(f"127.0.0.1:{port}").baglan(["A"])


def ist_eslesme_a(konumlar, ledler):
    return op.led_eslestir(ledler, konumlar)["A"]


class Saat:
    """time.monotonic yerine: her çağrıda sabit adımla ilerler."""

    def __init__(self, adim=0.2):
        self.t = 1000.0
        self.adim = adim

    def __call__(self):
        self.t += self.adim
        return self.t


class OturumTesti(unittest.TestCase):
    """Arayüzden bağımsız çekirdek (terminal ve masaüstü arayüzü bunu kullanır)."""

    def setUp(self):
        self.dizin = tempfile.TemporaryDirectory()
        self.addCleanup(self.dizin.cleanup)
        self.depo = op.IlerlemeDeposu(os.path.join(self.dizin.name, "progress.json"))
        temalar, _ = op.temalari_yukle(os.path.join(self.dizin.name, "yok"))
        self.ayarlar = dict(op.VARSAYILAN_AYARLAR)
        self.saat = Saat()
        yama = mock.patch.object(op.time, "monotonic", self.saat)
        yama.start()
        self.addCleanup(yama.stop)
        self.o = op.Oturum(self.ayarlar, temalar, self.depo, rng=random.Random(3))

    def satiri_yaz(self):
        for c in self.o.satir:
            self.o.tus_isle(c)

    def test_satir_bitince_tur_kaydedilir_ve_yeni_satira_gecilir(self):
        ilk, sonraki = self.o.satir, self.o.sonraki
        self.assertTrue(ilk)
        self.satiri_yaz()
        self.assertEqual(self.o.satir, sonraki)
        self.assertEqual(self.o.konum, 0)
        self.assertEqual(len(self.o.ilerleme.turlar), 1)
        tur = self.o.ilerleme.turlar[0]
        self.assertAlmostEqual(tur["dbk"], 12 / 0.2, places=1)       # 0,2 sn'de bir vuruş
        self.assertEqual(tur["dogruluk"], 100)
        self.assertEqual(self.depo.genel["satir"], 1)
        self.assertTrue(os.path.exists(self.depo.yol))

    def test_yanlis_tus_ilerlemez_ve_bir_kez_hata_sayilir(self):
        hedef = self.o.hedef
        yanlis = "q" if hedef != "q" else "w"
        self.o.tus_isle(yanlis)
        self.o.tus_isle(yanlis)
        self.assertEqual(self.o.konum, 0)
        self.assertEqual(self.o.hatali_basis, 2)
        self.assertEqual(self.o.hatalar, {0})
        self.assertEqual(self.o.mesaj_tur, "hata")
        self.assertEqual(self.o.flas_tus, yanlis)
        self.o.tus_isle(hedef)
        self.assertEqual(self.o.konum, 1)
        self.assertFalse(self.o.konumda_hata)

    def test_duraklama_sureyi_bozmaz(self):
        self.o.tus_isle(self.o.hedef)
        self.o.tus_isle(self.o.hedef)
        once = list(self.o.zamanlar)
        self.o.duraklat()
        self.saat.t += 100
        self.o.surdur()
        self.assertIsNone(self.o.duraklama)
        self.assertGreater(self.o.zamanlar[0], once[0] + 99)
        self.assertAlmostEqual(self.o.zamanlar[1] - self.o.zamanlar[0], once[1] - once[0])

    def test_hiz_testi_sure_ve_sonuc(self):
        self.o.alistirma_modu_sec("test")
        self.assertEqual(self.o.test_kalan(), self.ayarlar["test_suresi_sn"])
        self.o.tus_isle(self.o.hedef)                  # ilk vuruşta süre başlar
        self.assertLess(self.o.test_kalan(), self.ayarlar["test_suresi_sn"])
        self.o.test["dogru"], self.o.test["hata"] = 300, 0
        sonuc, onceki, bildirimler = self.o.test_sonucu_kaydet()
        self.assertAlmostEqual(sonuc["dbk"], 300 / 5 / (self.ayarlar["test_suresi_sn"] / 60))
        self.assertEqual(onceki, 0.0)
        self.assertEqual(len(self.o.ilerleme.testler), 1)
        self.assertIsNone(self.o.test["bas"])          # yeni test hazır
        self.assertIsInstance(bildirimler, list)

    def test_mod_secimi_satiri_yeniler(self):
        self.o.alistirma_modu_sec("zayif")
        self.assertEqual(self.o.alistirma_modu, "zayif")
        self.assertIsNone(self.o.test)
        self.assertTrue(self.o.satir)

    def test_terminal_arayuzu_oturumdan_turer(self):
        self.assertTrue(issubclass(op.Uygulama, op.Oturum))
        for ad in ("tus_isle", "satir_bitti", "yeni_satir", "profili_yukle"):
            self.assertNotIn(ad, vars(op.Uygulama), ad)


if __name__ == "__main__":
    unittest.main()
