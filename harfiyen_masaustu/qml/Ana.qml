import QtQuick
import QtQuick.Window

// Harfiyen masaüstü: ortada odak kartı, üstte özet şeridi, altta klavye,
// sağda açılır harf güveni paneli. Zen modunda yalnızca yazı ve parmak çizgileri kalır.
Window {
    id: pencere

    readonly property var r: ana.renk
    readonly property var m: ana.metinler
    readonly property string yaziTipi: yaziTipiVar ? "JetBrains Mono" : "monospace"
    readonly property bool zen: ana.zen
    readonly property int panelGenislik: 300
    readonly property bool panelAcik: ana.panel && !zen

    width: 1280
    height: 800
    minimumWidth: 760
    minimumHeight: 520
    visible: true
    color: r.zemin
    title: "Harfiyen"

    // Zemin ayrı bir öğe: pencere rengi grabToImage'a girmiyor, tema geçişi de yumuşak olsun
    Rectangle {
        anchors.fill: parent
        color: r.zemin
        Behavior on color { ColorAnimation { duration: 200 } }
    }

    // -- klavye girdisi ---------------------------------------------------------------
    Item {
        id: girdi
        anchors.fill: parent
        focus: true
        Keys.onPressed: (olay) => {
            olay.accepted = true
            const ctrl = olay.modifiers & Qt.ControlModifier
            if (ctrl && olay.key === Qt.Key_Q) { Qt.quit(); return }
            if (olay.key === Qt.Key_F11) { tamEkran(); return }
            if (ana.katman !== "") { katmanTusu(olay); return }
            switch (olay.key) {
            case Qt.Key_Escape: menuAc(); return
            case Qt.Key_Tab: ana.satirAtla(); return
            case Qt.Key_F4: ana.panelDegistir(); return
            case Qt.Key_F8: modListesi(); return
            case Qt.Key_F9: ana.zenDegistir(); return
            }
            if (olay.text.length > 0 && olay.text.charCodeAt(0) >= 32)
                ana.tus(olay.text)
        }
    }

    // --goruntu: pencereyi PNG'ye kaydedip çık (deneme ve belgeleme için)
    function goruntuKaydet(yol) {
        pencere.contentItem.grabToImage(sonuc => { sonuc.saveToFile(yol); Qt.quit() })
    }

    function tamEkran() {
        if (pencere.visibility === Window.FullScreen) pencere.showNormal()
        else pencere.showFullScreen()
    }

    function katmanTusu(olay) {
        if (ana.katman === "sonuc") {
            if (olay.key === Qt.Key_Return || olay.key === Qt.Key_Enter || olay.key === Qt.Key_Space)
                ana.modSec("test")
            else if (olay.key === Qt.Key_Escape)
                ana.modSec("ders")
            return
        }
        liste.tus(olay)
    }

    // -- liste katmanları (menü, mod, metin) --------------------------------------------
    function menuAc() {
        liste.ac(m.menu_baslik, [
            { etiket: m.menu_devam, ipucu: "Esc", eylem: "devam" },
            { etiket: m.menu_mod, ipucu: "F8", eylem: "mod" },
            { etiket: m.zen_ac, ipucu: "F9", eylem: "zen", isaret: zen },
            { etiket: m.panel, ipucu: "F4", eylem: "panel", isaret: ana.panel },
            { etiket: m.menu_tam, ipucu: "F11", eylem: "tam" },
            { etiket: m.menu_satir, ipucu: "Tab", eylem: "satir" },
            { etiket: m.cikis, ipucu: "Ctrl Q", eylem: "cik" },
        ], "menu")
    }

    function modListesi() {
        const ogeler = []
        for (const mod of ["ders", "zayif", "test", "metin"])
            ogeler.push({ etiket: m.modlar[mod], ipucu: m.mod_aciklama[mod],
                          eylem: "mod:" + mod, isaret: ana.alistirmaModu === mod })
        liste.ac(m.menu_mod, ogeler, "mod")
    }

    function metinListesi() {
        const ogeler = ana.metinListesi().map(t => ({
            etiket: t.ad, ipucu: t.ipucu, eylem: "metin:" + t.ad }))
        if (ogeler.length === 0) { liste.kapat(); return }
        liste.ac(m.metin_sec, ogeler, "metin")
    }

    function eylem(ad) {
        if (ad === "devam") liste.kapat()
        else if (ad === "mod") modListesi()
        else if (ad === "zen") { liste.kapat(); ana.zenDegistir() }
        else if (ad === "panel") { liste.kapat(); ana.panelDegistir() }
        else if (ad === "tam") { liste.kapat(); tamEkran() }
        else if (ad === "satir") { liste.kapat(); ana.satirAtla() }
        else if (ad === "cik") Qt.quit()
        else if (ad === "mod:metin") metinListesi()
        else if (ad.startsWith("mod:")) ana.modSec(ad.slice(4))
        else if (ad.startsWith("metin:")) ana.metinSec(ad.slice(6))
    }

    // -- sahne ------------------------------------------------------------------------------
    Item {
        id: sahne
        anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
        width: parent.width - (panelAcik ? panelGenislik : 0)
        Behavior on width { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }

        Ust {
            id: ust
            anchors { top: parent.top; left: parent.left; right: parent.right }
        }

        // Kart ile klavye arasındaki boşluk: kart kalan alanda ortalanır.
        Item {
            id: orta
            anchors {
                top: ust.bottom; left: parent.left; right: parent.right
                bottom: zen ? zenIpucu.top : (klavye.gizli ? parent.bottom : klavye.top)
                bottomMargin: zen ? 0 : 12
            }

            YaziKarti {
                id: kart
                anchors.centerIn: parent
                anchors.verticalCenterOffset: -mesajSatiri.height / 2
                width: Math.min(parent.width - (zen ? 64 : 96), zen ? 1280 : 1040)
            }

            // Bildirim ya da durum satırı (kartın hemen altında)
            Text {
                id: mesajSatiri
                anchors { top: kart.bottom; topMargin: 18; horizontalCenter: parent.horizontalCenter }
                width: kart.width
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                text: ana.mesaj !== "" ? ana.mesaj : (zen ? "" : ana.durumUzun)
                color: ana.mesaj !== "" ? (r[ana.mesajTuru] || r.yazi) : r.soluk
                font { family: yaziTipi; pixelSize: 14 }
                Behavior on color { ColorAnimation { duration: 120 } }
            }

            YeniHarf { id: yeniHarf; anchors.centerIn: kart; anchors.verticalCenterOffset: -kart.height / 2 - 34 }
        }

        Klavye {
            id: klavye
            // Genişlik pencereye, yükseklik kartın en az ihtiyacından artan alana göre;
            // çok basık pencerede klavye kendiliğinden gizlenir.
            readonly property real yerYuksekligi: sahne.height - ust.height - 320
            readonly property bool sigar: yerYuksekligi * 3 >= 520
            anchors { bottom: parent.bottom; bottomMargin: gizli ? -height : 28; horizontalCenter: parent.horizontalCenter }
            readonly property bool gizli: zen || !sigar
            width: Math.min(parent.width - 96, 1000, yerYuksekligi * 3)
            opacity: gizli ? 0 : 1
            visible: opacity > 0
            Behavior on opacity { NumberAnimation { duration: 200 } }
            Behavior on anchors.bottomMargin { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
        }

        // Zen modunda alttaki tek satırlık ipucu
        Row {
            id: zenIpucu
            anchors { bottom: parent.bottom; bottomMargin: 22; horizontalCenter: parent.horizontalCenter }
            spacing: 22
            opacity: zen ? 1 : 0
            height: 24
            Behavior on opacity { NumberAnimation { duration: 200 } }
            TusIpucu { tus: "F9"; etiket: m.tam_gorunum; onTiklandi: ana.zenDegistir() }
            TusIpucu { tus: "F8"; etiket: m.modlar[ana.alistirmaModu]; onTiklandi: modListesi() }
            TusIpucu { tus: "Esc"; etiket: m.menu; onTiklandi: menuAc() }
        }
    }

    Panel {
        id: panel
        anchors { top: parent.top; bottom: parent.bottom }
        width: panelGenislik
        x: pencere.width - (panelAcik ? width : 0)
        visible: x < pencere.width
        Behavior on x { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    }

    // -- katmanlar ------------------------------------------------------------------------
    Liste {
        id: liste
        anchors.fill: parent
        onSecildi: (ad) => eylem(ad)
    }

    Sonuc {
        anchors.fill: parent
        gorunur: ana.katman === "sonuc"
    }

    Connections {
        target: ana
        function onYanlis() { kart.titre() }
        function onYeniHarf(harf) { yeniHarf.goster(harf) }
    }
}
