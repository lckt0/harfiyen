import QtQuick

// Sağdan açılan harf güveni paneli: harf başına güven çubuğu, son turların hızı.
Rectangle {
    id: kok
    readonly property var r: ana.renk
    readonly property var m: ana.metinler

    color: r.yuzey
    Rectangle {
        anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
        width: 1
        color: r.cizgi
    }

    function guvenRengi(v) {
        if (v.usta) return r.dogru
        if (v.guven < 0.4) return r.hata
        if (v.guven < 0.75) return r.uyari
        return r.dogru
    }

    Item {
        id: baslik
        anchors { top: parent.top; left: parent.left; right: parent.right }
        height: 52
        Text {
            anchors { left: parent.left; leftMargin: 24; verticalCenter: parent.verticalCenter }
            text: m.panel.toLocaleUpperCase(Qt.locale("tr_TR"))
            color: r.baslik
            font { family: pencere.yaziTipi; pixelSize: 13; weight: Font.DemiBold; letterSpacing: 2 }
        }
        TusIpucu {
            anchors { right: parent.right; rightMargin: 20; verticalCenter: parent.verticalCenter }
            tus: "F4"; etiket: ""
            onTiklandi: ana.panelDegistir()
        }
        Rectangle {
            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
            height: 1
            color: r.cizgi
        }
    }

    Flickable {
        anchors { top: baslik.bottom; bottom: grafik.top; left: parent.left; right: parent.right }
        contentHeight: liste.height + 32
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: liste
            x: 24
            y: 16
            width: parent.width - 48
            spacing: 2

            Text {
                text: ana.harfOzeti
                color: r.soluk
                font { family: pencere.yaziTipi; pixelSize: 12 }
                bottomPadding: 10
            }

            Repeater {
                model: ana.harfler
                delegate: Item {
                    required property var modelData
                    readonly property var v: modelData
                    width: liste.width
                    height: 22
                    Text {
                        id: harf
                        anchors.verticalCenter: parent.verticalCenter
                        width: 22
                        text: v.h
                        color: v.guncel ? r.vurgu : v.acik ? r.baslik : r.cizgi
                        font { family: pencere.yaziTipi; pixelSize: 15; weight: v.acik ? Font.DemiBold : Font.Normal }
                    }
                    Rectangle {
                        id: cubuk
                        anchors { left: harf.right; leftMargin: 6; right: yuzde.left; rightMargin: 12; verticalCenter: parent.verticalCenter }
                        height: 2
                        color: v.acik ? r.cizgi : "transparent"
                        Rectangle {
                            height: 2
                            width: parent.width * (v.usta ? 1 : v.guven)
                            color: kok.guvenRengi(v)
                            Behavior on width { NumberAnimation { duration: 300 } }
                        }
                        // kapalı harfler: noktalı çizgi
                        Row {
                            visible: !v.acik
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 6
                            Repeater {
                                model: Math.floor(cubuk.width / 8)
                                Rectangle { width: 2; height: 2; color: r.cizgi }
                            }
                        }
                    }
                    Text {
                        id: yuzde
                        anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                        width: 44
                        horizontalAlignment: Text.AlignRight
                        text: !v.acik ? "" : v.usta ? "✓" : v.veri ? "%" + Math.round(v.guven * 100) : "—"
                        color: v.usta ? r.dogru : r.soluk
                        font { family: pencere.yaziTipi; pixelSize: 12 }
                    }
                }
            }
        }
    }

    // Son turların hızı (çubuk boyu DBK, rengi doğruluk)
    Item {
        id: grafik
        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
        height: 132
        Rectangle {
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: 1
            color: r.cizgi
        }
        Text {
            x: 24; y: 16
            text: m.son_turlar.replace("{n}", ana.sonTurlar.length)
            color: r.soluk
            font { family: pencere.yaziTipi; pixelSize: 12 }
        }
        Row {
            id: cubuklar
            readonly property real enCok: Math.max(10, ...ana.sonTurlar.map(t => t.dbk))
            anchors { left: parent.left; leftMargin: 24; bottom: parent.bottom; bottomMargin: 22 }
            height: 70
            spacing: 2
            Repeater {
                model: ana.sonTurlar
                delegate: Rectangle {
                    required property var modelData
                    anchors.bottom: parent.bottom
                    width: Math.max(3, (grafik.width - 48) / 30 - 2)
                    height: Math.max(2, 70 * modelData.dbk / cubuklar.enCok)
                    color: modelData.dogruluk >= 97 ? r.dogru : modelData.dogruluk >= 90 ? r.uyari : r.hata
                    opacity: 0.85
                }
            }
        }
    }
}
