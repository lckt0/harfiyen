import json
import os
import random
import sys
import tempfile
import time
import unittest

_GECICI = tempfile.mkdtemp()
os.environ["XDG_DATA_HOME"] = os.path.join(_GECICI, "veri")
os.environ["XDG_CONFIG_HOME"] = os.path.join(_GECICI, "ayar")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import harfiyen_mola as m  # noqa: E402


class AlistirmaTesti(unittest.TestCase):
    def test_yalnizca_acik_harfler_ve_kelime_sayisi(self):
        a = m.Alistirma(5, random.Random(1))
        acik = set(a.ilerleme.acik_harfler) | {" "}
        self.assertLessEqual(set(a.metin), acik)
        self.assertLessEqual(len(a.metin.split()), 5)

    def test_yanlis_tus_ilerletmez_ve_kayda_islenir(self):
        a = m.Alistirma(3, random.Random(2))
        ilk = a.hedef
        yanlis = "q" if ilk != "q" else "w"
        self.assertFalse(a.tus(yanlis))
        self.assertEqual(a.konum, 0)
        self.assertTrue(a.tus(ilk))
        for c in a.metin[1:]:
            self.assertTrue(a.tus(c))
        self.assertTrue(a.bitti)
        self.assertIsNone(a.tus("x"))
        self.assertEqual(a.hatalar, {0})
        a.kaydet()
        with open(m.hf.KAYIT_DOSYASI, encoding="utf-8") as f:
            veri = json.load(f)
        harf = veri["profiller"][a.anahtar]["harfler"][ilk]
        self.assertEqual(harf["hata"], 1)
        self.assertEqual(harf["gecmis"][0], 0)
        self.assertEqual(veri["genel"]["vurus"], len(a.metin) - 1)

    def test_parmak_tarifi(self):
        a = m.Alistirma(2, random.Random(3))
        tarif, renk = a.parmak()
        self.assertIn("parmak", tarif.lower())
        self.assertTrue(renk)

    def test_parmak_sirasi_sol_serceden_sag_serceye(self):
        a = m.Alistirma(3, random.Random(3))
        beklenen = {"a": 0, "s": 1, "d": 2, "f": 3, "j": 4, "k": 5, "l": 6, " ": -1}
        for c, sira in beklenen.items():
            a.metin, a.konum = c, 0
            self.assertEqual(a.parmak_sirasi(), sira, c)


class SatirTesti(unittest.TestCase):
    def test_kisa_metin_tek_satir(self):
        self.assertEqual(m.satirlara_bol("asd fgh"), [(0, 7)])

    def test_uzun_metin_kelime_sinirindan_dengeli_bolunur(self):
        rng = random.Random(4)
        for _ in range(200):
            kelimeler = ["".join(rng.choice("asdfjkl") for _ in range(rng.randint(1, 9)))
                         for _ in range(10)]
            metin = " ".join(kelimeler)
            satirlar = m.satirlara_bol(metin)
            self.assertEqual("".join(metin[a:b] for a, b in satirlar), metin)
            self.assertEqual(len(satirlar), -(-len(metin) // m.SATIR_GENISLIGI))
            for a, b in satirlar:
                self.assertTrue(a == 0 or metin[a - 1] == " ")      # kelime ortasından değil
                self.assertLessEqual(len(metin[a:b].rstrip()), m.SATIR_GENISLIGI)

    def test_on_kelime_kirpilmadan_gelir(self):
        for tohum in range(20):
            a = m.Alistirma(10, random.Random(tohum))
            self.assertEqual(len(a.metin.split()), 10)
            self.assertEqual("".join(a.metin[x:y] for x, y in a.satirlar), a.metin)


class AyarTesti(unittest.TestCase):
    def test_varsayilanlar(self):
        self.assertEqual(m.VARSAYILAN["kelime"], 10)
        self.assertIs(m.VARSAYILAN["parmak_goster"], False)

    def test_eksik_ayar_dosyaya_eklenir_mevcut_korunur(self):
        m.hf.json_yaz(m.AYAR_DOSYASI, {"kelime": 7})
        ayar = m.ayarlari_yukle()
        self.assertEqual(ayar["kelime"], 7)
        self.assertIs(ayar["parmak_goster"], False)
        with open(m.AYAR_DOSYASI, encoding="utf-8") as f:
            dosya = json.load(f)
        self.assertEqual(dosya["kelime"], 7)
        self.assertIs(dosya["parmak_goster"], False)

    def test_gecersiz_degerler_yok_sayilir(self):
        m.hf.json_yaz(m.AYAR_DOSYASI, {"aralik_dk": "çok", "kelime": 0,
                                       "ilerlemeye_kaydet": 1, "bilinmeyen": 3})
        ayar = m.ayarlari_yukle()
        self.assertEqual(ayar["aralik_dk"], 10)
        self.assertEqual(ayar["kelime"], 1)            # sınıra çekilir
        self.assertIs(ayar["ilerlemeye_kaydet"], True)
        self.assertNotIn("bilinmeyen", ayar)


class RekorTesti(unittest.TestCase):
    def setUp(self):
        self.yol = os.path.join(tempfile.mkdtemp(), "rekor.json")

    def ist(self, dbk, dogruluk=100.0):
        return {"dbk": dbk, "dogruluk": dogruluk, "tutarlilik": 80.0}

    def test_ilk_tur_kaydedilir_ama_yeni_rekor_sayilmaz(self):
        self.assertEqual(m.rekor_isle(self.ist(40), 90, self.yol), (None, False))
        self.assertEqual(m.rekor_yukle(self.yol)["dbk"], 40)

    def test_daha_hizli_tur_yeni_rekor(self):
        m.rekor_isle(self.ist(40), 90, self.yol)
        onceki, yeni = m.rekor_isle(self.ist(45.5), 90, self.yol)
        self.assertTrue(yeni)
        self.assertEqual(onceki["dbk"], 40)
        self.assertEqual(m.rekor_yukle(self.yol)["dbk"], 45.5)

    def test_esit_ya_da_yavas_tur_rekoru_degistirmez(self):
        m.rekor_isle(self.ist(40), 90, self.yol)
        self.assertFalse(m.rekor_isle(self.ist(40), 90, self.yol)[1])
        self.assertFalse(m.rekor_isle(self.ist(30), 90, self.yol)[1])
        self.assertEqual(m.rekor_yukle(self.yol)["dbk"], 40)

    def test_dusuk_dogruluk_rekor_sayilmaz(self):
        m.rekor_isle(self.ist(40), 90, self.yol)
        self.assertFalse(m.rekor_isle(self.ist(80, 85.0), 90, self.yol)[1])
        self.assertEqual(m.rekor_yukle(self.yol)["dbk"], 40)

    def test_kaydetme_kapaliyken_dosyaya_yazmaz(self):
        m.rekor_isle(self.ist(40), 90, self.yol)
        self.assertTrue(m.rekor_isle(self.ist(50), 90, self.yol, kaydet=False)[1])
        self.assertEqual(m.rekor_yukle(self.yol)["dbk"], 40)

    def test_bozuk_dosya_kayit_yok_sayilir(self):
        with open(self.yol, "w", encoding="utf-8") as f:
            f.write("[1, 2")
        self.assertIsNone(m.rekor_yukle(self.yol))
        with open(self.yol, "w", encoding="utf-8") as f:
            f.write('["liste"]')
        self.assertIsNone(m.rekor_yukle(self.yol))


class SahteMedya:
    def __init__(self):
        self.oynayan = []

    def oynayanlar(self):
        return list(self.oynayan)


class IzlemeSayaciTesti(unittest.TestCase):
    """Saniyeler dakikaların yerine: aralık 0,4 sn, ara 0,25 sn."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QCoreApplication
        cls.uygulama = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.medya = SahteMedya()
        self.sayac = m.IzlemeSayaci(self.medya, 0.4, 0.25)
        self.vakitler = []
        self.sayac.vakit.connect(lambda: self.vakitler.append(time.monotonic()))

    def bekle(self, sn):
        son = time.monotonic() + sn
        while time.monotonic() < son:
            self.uygulama.processEvents()
            time.sleep(0.005)

    def durum(self, oynuyor):
        self.medya.oynayan = ["org.mpris.MediaPlayer2.x"] if oynuyor else []
        self.sayac.degerlendir()

    def test_kesintisiz_izlemede_aralik_dolunca_cikar(self):
        basla = time.monotonic()
        self.durum(True)
        self.bekle(0.3)
        self.assertEqual(self.vakitler, [])
        self.bekle(0.2)
        self.assertEqual(len(self.vakitler), 1)
        self.assertAlmostEqual(self.vakitler[0] - basla, 0.4, delta=0.05)

    def test_kisa_duraklama_birikeni_silmez(self):
        self.durum(True)
        self.bekle(0.25)
        self.durum(False)           # 0,1 sn duraklat (ara 0,25'ten kısa)
        self.bekle(0.1)
        basla = time.monotonic()
        self.durum(True)
        self.bekle(0.3)
        self.assertEqual(len(self.vakitler), 1)
        self.assertAlmostEqual(self.vakitler[0] - basla, 0.15, delta=0.05)

    def test_sarma_titresimi_sayaci_bozmaz(self):
        basla = time.monotonic()
        self.durum(True)
        for _ in range(5):           # sararken oynatıcı Paused/Playing arasında gidip gelir
            self.bekle(0.05)
            self.durum(False)
            self.durum(True)
        self.bekle(0.3)
        self.assertEqual(len(self.vakitler), 1)
        self.assertAlmostEqual(self.vakitler[0] - basla, 0.4, delta=0.05)

    def test_uzun_ara_sayaci_sifirlar(self):
        self.durum(True)
        self.bekle(0.3)
        self.durum(False)
        self.bekle(0.3)             # ara 0,25'ten uzun
        basla = time.monotonic()
        self.durum(True)
        self.bekle(0.5)
        self.assertEqual(len(self.vakitler), 1)
        self.assertAlmostEqual(self.vakitler[0] - basla, 0.4, delta=0.05)

    def test_oynamazken_hic_cikmaz_ve_sonra_yeniden_sayar(self):
        self.bekle(0.5)
        self.assertEqual(self.vakitler, [])
        self.durum(True)
        self.bekle(0.9)
        self.assertEqual(len(self.vakitler), 2)     # her 0,4 sn'de bir
        self.sayac.sifirla()
        self.assertLess(self.sayac.gecen(), 0.01)


if __name__ == "__main__":
    unittest.main()
