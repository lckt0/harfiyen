import QtQuick

// Müfredattaki bir harf: kapalıysa sönük; açıksa altında güven çizgisi;
// güncel (öğrenilen) harf vurgu zeminli; ustalaşmış harf tam yeşil çizgili.
Item {
    id: kok
    property var veri
    readonly property var r: ana.renk

    width: 26
    height: 34

    function guvenRengi(g) {
        if (veri.usta) return r.dogru
        if (g < 0.4) return r.hata
        if (g < 0.75) return r.uyari
        return r.dogru
    }

    Rectangle {
        id: zemin
        anchors { fill: parent; bottomMargin: 6 }
        color: veri.guncel ? r.vurgu : "transparent"
        border.color: veri.acik && !veri.guncel ? r.cizgi : "transparent"
        border.width: 1
        Behavior on color { ColorAnimation { duration: 200 } }
        Text {
            anchors.centerIn: parent
            text: veri.etiket
            color: veri.guncel ? r.vurgu_yazi : veri.usta ? r.baslik : veri.acik ? r.yazi : r.cizgi
            font { family: pencere.yaziTipi; pixelSize: Math.min(14, kok.width * 0.55); weight: veri.acik ? Font.DemiBold : Font.Normal }
        }
    }
    // güven çizgisi
    Rectangle {
        anchors { bottom: parent.bottom; left: parent.left }
        visible: veri.acik
        height: 2
        width: parent.width
        color: r.cizgi
        Rectangle {
            height: 2
            width: parent.width * (veri.usta ? 1 : veri.guven)
            color: guvenRengi(veri.guven)
            Behavior on width { NumberAnimation { duration: 300 } }
        }
    }

}
