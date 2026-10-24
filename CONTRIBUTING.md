# Katkı rehberi

Katkılarınız memnuniyetle karşılanır. Aşağıdaki birkaç ilke projenin sade kalmasını sağlar.

## İlkeler

- **Yalnızca standart kütüphane.** Harfiyen (`harfiyen.py`) harici bağımlılık kullanmaz; isteğe
  bağlı masaüstü arayüzü ve Harfiyen Mola PySide6 kullanır. Python 3.9 ve sonrası
  ile çalışmalıdır.
- **Tek dosya.** Uygulama `harfiyen.py` içindedir; bu sayede indirilip doğrudan çalıştırılabilir.
- **Terminalden bağımsızlık.** Terminale özgü bir yetenek kullanılıyorsa önce standart yol
  (xterm kaçış kodları) denenir, sonra masaüstüne özgü yedek, en son zarif bir düşüş.
- **Curses'tan bağımsız mantık.** Kelime üretimi, ustalık, yerleşim ve renk hesapları curses
  kullanmayan işlevlerdedir ve birim testleri vardır; yeni mantık da böyle yazılmalıdır.
- **Türkçe adlandırma.** Kod içindeki adlar ve yorumlar Türkçedir; mevcut üslubu izleyin.

## Geliştirme

```sh
git clone https://github.com/lckt0/harfiyen
cd harfiyen
python3 harfiyen.py                                # doğrudan çalıştırma
python3 -m unittest discover -s tests -t . -v      # testler
```

Görsel bir değişiklik yaptıysanız birkaç terminalde (ör. Konsole, GNOME Terminal, kitty,
xterm) ve hem 256 renk hem 8 renk ortamında deneyin; ekran görüntüsünü çekme isteğine ekleyin.
Deneme sırasında gerçek ayarlarınızın bozulmaması için ayrı dizinler kullanabilirsiniz:

```sh
XDG_CONFIG_HOME=/tmp/h/config XDG_DATA_HOME=/tmp/h/data python3 harfiyen.py
```

## Tuş aydınlatmasını donanım olmadan denemek

OpenRGB'nin deneme (debug) klavyesi tuş başına RGB'li bir klavyeyi taklit eder. Boş bir ayar
dizininde şu `OpenRGB.json` ile sunucuyu başlatın:

```json
{"DebugDevices": {"devices": [{"type": "keyboard", "keyboard": true, "single": false,
                               "linear": false, "layout": 2}]}}
```

```sh
openrgb --config /tmp/orgb --server --server-port 6799 --noautoconnect
```

Harfiyen'in ayarlarında `"rgb_isik": "openrgb"` ve `"rgb_adres": "127.0.0.1:6799"` yapın.
Protokolün birim testleri gerçek sunucu gerektirmez (`tests/` içindeki sahte sunucu).

## Yeni bir klavye düzeni eklemek

`DUZENLER` sözlüğüne sayı, üst, orta ve alt sıraları, ISO'ya özgü `ek1` ve `ek2` tuşlarını ve
Shift eşlemesini ekleyin. Parmak ataması konuma göre yapıldığı için ayrıca tanımlanması gerekmez.
Düzenin kendi dilinde bir harf açılma sırası yoksa, ana sıra ve harf sıklığından otomatik
üretilir (`mufredat`).

## Yeni bir dil eklemek

`DILLER` sözlüğüne harfleri, sesli harfleri, en az 300 yaygın kelimelik bir liste ve noktalama
işaretlerini ekleyin; arayüz çevirisi için `METINLER` altına yeni bir dil anahtarı açın
(`test_metin_anahtarlari_ayni` testi eksik anahtarları yakalar).
