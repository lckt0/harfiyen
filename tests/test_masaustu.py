#!/usr/bin/env python3
"""Masaüstü arayüzünün denetleyicisi (QML'siz). PySide6 yoksa atlanır."""

import os
import random
import tempfile
import unittest
from unittest import mock

import harfiyen as op

try:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication
    import harfiyen_masaustu as hm
except ImportError:                                   # PySide6 isteğe bağlı
    hm = None


@unittest.skipIf(hm is None, "PySide6 kurulu değil")
class Denetleyici(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.uygulama = QGuiApplication.instance() or QGuiApplication([])

    def setUp(self):
        self.dizin = tempfile.TemporaryDirectory()
        self.addCleanup(self.dizin.cleanup)
        d = self.dizin.name
        self.depo = op.IlerlemeDeposu(os.path.join(d, "progress.json"))
        temalar, _ = op.temalari_yukle(os.path.join(d, "yok"))
        self.ayar_yolu = os.path.join(d, "masaustu.json")
        self.oturum = op.Oturum(dict(op.VARSAYILAN_AYARLAR), temalar, self.depo,
                                rng=random.Random(5))
        self.ana = hm.Masaustu(self.oturum, hm.ayarlari_yukle(self.ayar_yolu), self.ayar_yolu)
        self.addCleanup(self.ana.zamanlayici.stop)

    def test_satir_karakter_siniri(self):
        self.assertLessEqual(len(self.ana.satir), hm.VARSAYILAN["satir_karakter"])

    def test_tus_ve_hata_maskesi(self):
        hedef = self.ana.satir[0]
        yanlis = "q" if hedef != "q" else "w"
        sinyaller = []
        self.ana.yanlis.connect(lambda: sinyaller.append(1))
        self.ana.tus(yanlis)
        self.assertEqual(sinyaller, [1])
        self.assertEqual(self.ana.konum, 0)
        self.assertEqual(self.ana.flasTus, yanlis)
        self.ana.tus(hedef)
        self.assertEqual(self.ana.konum, 1)
        self.assertTrue(self.ana.hataMaskesi.startswith("1"))
        self.assertEqual(len(self.ana.hataMaskesi), len(self.ana.satir))

    def test_katman_acikken_tus_yok_sayilir_ve_sure_durur(self):
        self.ana.katmanAc("menu")
        self.assertIsNotNone(self.oturum.duraklama)
        self.ana.tus(self.ana.satir[0])
        self.assertEqual(self.ana.konum, 0)
        self.ana.katmanAc("")
        self.assertIsNone(self.oturum.duraklama)

    def test_satir_bitince_ozet_sinyali(self):
        sinyaller = []
        self.ana.ozetDegisti.connect(lambda: sinyaller.append(1))
        with mock.patch.object(op.time, "monotonic", side_effect=(1000 + i * 0.2 for i in range(10000))):
            self.ana.tus(self.ana.satir)
        self.assertTrue(sinyaller)
        self.assertEqual(len(self.oturum.ilerleme.turlar), 1)
        self.assertNotEqual(self.ana.metrikler[0]["deger"], self.oturum.m["yok"])

    def test_klavye_tuslari(self):
        tuslar = {t["ad"]: t for t in self.ana.tuslar}
        self.assertTrue(tuslar["f"]["acik"])
        self.assertTrue(tuslar["f"]["cikinti"])
        self.assertFalse(tuslar["x"]["acik"])            # Türkçe müfredatta yok
        self.assertTrue(tuslar["x"]["harf"])
        self.assertEqual(tuslar["f"]["parmak"], "isaret")
        self.assertEqual(tuslar[" "]["etiket"], "")

    def test_parmak_sirasi(self):
        self.assertEqual(hm.parmak_sirasi(("sol", "serce")), 0)
        self.assertEqual(hm.parmak_sirasi(("sol", "isaret")), 3)
        self.assertEqual(hm.parmak_sirasi(("sag", "isaret")), 4)
        self.assertEqual(hm.parmak_sirasi(("sag", "serce")), 7)
        self.assertEqual(hm.parmak_sirasi(("", "basparmak")), -1)

    def test_zen_ayari_kaydedilir(self):
        self.ana.zenDegistir()
        self.assertTrue(hm.ayarlari_yukle(self.ayar_yolu)["zen"])

    def test_test_bitince_sonuc_katmani(self):
        self.ana.modSec("test")
        self.oturum.test["bas"] = op.time.monotonic() - 100
        self.oturum.test["dogru"] = 200
        self.ana._tik()
        self.assertEqual(self.ana.katman, "sonuc")
        self.assertEqual(self.ana.sonuc["dbk"], "40.0")


class TemaRenkleri(unittest.TestCase):
    @unittest.skipIf(hm is None, "PySide6 kurulu değil")
    def test_tum_temalar_hex_verir(self):
        for kimlik, tema in op.temalari_yukle("/yok")[0].items():
            with self.subTest(tema=kimlik):
                r = hm.tema_renkleri(tema)
                for alan in ("zemin", "yuzey", "yazi", "soluk", "cizgi", "vurgu", "hata",
                             "p_serce", "p_isaret"):
                    self.assertRegex(r[alan], r"^#[0-9a-f]{6}$")


if __name__ == "__main__":
    unittest.main()
