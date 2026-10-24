# Değişiklik günlüğü

Bu dosyadaki biçim [Keep a Changelog](https://keepachangelog.com/tr-TR/1.1.0/) önerisini,
sürüm numaraları [Anlamsal Sürümleme](https://semver.org/lang/tr/) kurallarını izler.

## [Yayımlanmamış]

### Eklenenler

- Harfiyen Mola (`harfiyen-mola`, isteğe bağlı): medya oynarken belli aralıklarla oynayan
  medyayı duraklatıp ekranın üstüne kısa bir alıştırma çıkarır, bitince medyayı sürdürür.
  systemd kullanıcı servisi olarak çalışır; Arch'ta ayrı `harfiyen-mola` paketi.
- Masaüstü arayüzü (`harfiyen-masaustu`, Qt Quick / PySide6, isteğe bağlı): ortada odak
  kartı, üstte metrik ve harf çipi şeridi, altta parmak renkli klavye, sağda açılır harf
  güveni paneli (F4), zen modu (F9), mod/metin listeleri, hız testi sonucu ve yeni harf
  rozeti. Terminal arayüzüyle aynı ilerleme, ayar ve temaları kullanır.

- Tuş başına RGB aydınlatma (OpenRGB SDK sunucusu üzerinden): basılacak tuş klavyede yanar;
  Shift gerekiyorsa karşı eldeki Shift yarı parlaklıkta, yanlış basılan tuş kısa süre kırmızı.
  Diğer tuşlar sönük, soluk beyaz ya da açık harfler parmak renklerinde olabilir; çıkışta
  klavyenin önceki ışıkları ve efekti geri yüklenir.
- Tuşlar fiziksel konuma göre eşlenir (OpenRGB'nin ABD tuş adları; farklı sürücülerin
  eş anlamlı adları da tanınır).
- Yazının hemen altında, ekranın altındaki parmak göstergeleriyle aynı görünümde bir şerit:
  parmak adları klavyedeki gibi aralıklı dizilir, basılacak parmak vurgulanır ve üstünde
  yön oku ile harf görünür. Ayarlar → Görünüm → "Yazının altında parmaklar" (`yazi_parmak`)
  ile kapatılabilir. Kart dar ya da ekran kısaysa şerit düşer; klavye gizliyken yerine
  parmak çipleri yazının altında durur (önceden ipucu satırının altındaydı).
- Ayarlar → Veri → "İlerlemeyi sıfırla": onay penceresinde yalnızca etkin profil (dil +
  düzen) ya da tüm ilerleme (XP, seviye, rozetler, günlük seri dahil) sıfırlanır; önceki
  kayıt `progress.json.yedek` dosyasına yazılır. Kaydedilmemiş ayar değişiklikleri korunur.

### Değişenler

- Alıştırma mantığı (profil, satır üretimi, vuruşlar, modlar, XP ve rozetler) arayüzden
  bağımsız `Oturum` sınıfına ayrıldı; terminal arayüzü (`Uygulama`) bunun alt sınıfı.
- Arch paketi masaüstü kısayolunu da kurar; terminal kısayolunun adı "Harfiyen (terminal)".

## [0.1.0] - 2026-09-30

İlk sürüm.

### Eklenenler

- Kademeli ders: harfler ana sıradan başlayarak, açık harflerin hepsi ustalaşınca birer birer açılır.
- Klavye düzenleri: Türkçe Q, Türkçe F, İngilizce (ABD); fiziksel olarak ISO, ANSI ve 102 tuşlu ANSI; isteğe bağlı numpad.
- Alıştırma dili ve arayüz dili: Türkçe ya da İngilizce.
- Modlar: ders, zayıf noktalar (en çok zorlanılan harfler ve harf çiftleri), hız testi, serbest metin.
- Seçenekler: hıza dayalı ustalık ölçütü, büyük harfler, noktalama, rakamlar.
- keybr tarzı özet: metrikler ve değişimleri, harf çipleri, güncel harfin hızı ve öğrenme hızı, doğruluk serisi, günlük hedef.
- Günlük hedef, gün serisi, seviye/XP ve 19 rozet; son 14 gün, parmaklar, harfler ve testlerle istatistik ekranı.
- Tuş başlığı görünümünde klavye: parmak renkleri ya da hata ısı haritası; tuş stili (derinlik, düz, yüzen), alt kenar yüksekliği ve klavye boyutu ayarları.
- Yazı boyutu: küçük, normal, büyük ve dev (yerleşik piksel yazı tipiyle).
- JSON ile tanımlanan, miras alınabilen temalar; altı yerleşik tema.
- Ayarlar hem JSON dosyasından hem uygulama içinden düzenlenebilir; değişiklikler canlı önizlenir.
- Fare desteği: düğmeler, menüler, ayar okları, harf çipleri, tekerlek; her pencerede kapatma düğmesi.
- Esc ve Ctrl-C için çıkış onayı.
- Açılışta pencereyi büyütme ya da tam ekrana geçme (KDE'de KWin, diğerlerinde xterm kaçış kodları).
- Tam ekranda, parmakların fiziksel hizasında göstergeler; konum ince ayarı.
