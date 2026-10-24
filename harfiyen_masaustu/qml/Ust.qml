import QtQuick

// Üst şerit: ad, mod, metrikler, seviye, kısayollar; altında harf çipleri ve günlük hedef.
// Zen modunda yalnızca ince bir başlık kalır.
Item {
    id: kok
    readonly property var r: ana.renk
    readonly property var m: ana.metinler
    readonly property bool zen: pencere.zen

    height: baslik.height + (zen ? 0 : cipSeridi.height + 1)
    Behavior on height { NumberAnimation { duration: 220; easing.type: Easing.OutCubic } }
    clip: true

    // -- başlık satırı ---------------------------------------------------------------------
    Item {
        id: baslik
        anchors { top: parent.top; left: parent.left; right: parent.right }
        height: 52

        Row {
            id: sol
            anchors { left: parent.left; leftMargin: 28; verticalCenter: parent.verticalCenter }
            spacing: 14
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "HARFİYEN"
                color: zen ? r.soluk : r.baslik
                font { family: pencere.yaziTipi; pixelSize: 14; weight: Font.DemiBold; letterSpacing: 2 }
                Behavior on color { ColorAnimation { duration: 200 } }
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "·"
                color: r.soluk
                font { family: pencere.yaziTipi; pixelSize: 14 }
            }
            // Mod düğmesi
            Item {
                anchors.verticalCenter: parent.verticalCenter
                width: modYazi.implicitWidth
                height: 30
                Text {
                    id: modYazi
                    anchors.verticalCenter: parent.verticalCenter
                    text: ana.modAdi.toLocaleUpperCase(Qt.locale("tr_TR")) + "  ▾"
                    color: modFare.containsMouse ? r.vurgu : (zen ? r.soluk : r.baslik)
                    font { family: pencere.yaziTipi; pixelSize: 14; weight: Font.DemiBold; letterSpacing: 2 }
                }
                MouseArea {
                    id: modFare
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: pencere.modListesi()
                }
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                visible: !zen && kok.width >= 1200
                text: ana.profil
                color: r.soluk
                font { family: pencere.yaziTipi; pixelSize: 12 }
                leftPadding: 10
            }
        }

        // Zen: yalnızca son hız
        Text {
            anchors { right: parent.right; rightMargin: 28; verticalCenter: parent.verticalCenter }
            visible: zen
            text: ana.hizKisa
            color: r.soluk
            font { family: pencere.yaziTipi; pixelSize: 13 }
        }

        Row {
            id: sag
            anchors { right: parent.right; rightMargin: 28; verticalCenter: parent.verticalCenter }
            spacing: 26
            visible: !zen

            // Metrikler: HIZ 38.7 ↑4.3 (dar pencerede yalnızca hız)
            Repeater {
                model: kok.width >= 1080 ? ana.metrikler : ana.metrikler.slice(0, 1)
                delegate: Row {
                    required property var modelData
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 7
                    Text {
                        anchors.baseline: deger.baseline
                        text: modelData.etiket.toLocaleUpperCase(Qt.locale("tr_TR"))
                        color: r.soluk
                        font { family: pencere.yaziTipi; pixelSize: 11; letterSpacing: 1 }
                    }
                    Text {
                        id: deger
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.deger
                        color: r.baslik
                        font { family: pencere.yaziTipi; pixelSize: 16; weight: Font.DemiBold }
                    }
                    Text {
                        anchors.baseline: deger.baseline
                        visible: modelData.degisim !== ""
                        text: modelData.degisim
                        color: modelData.iyi ? r.dogru : r.hata
                        font { family: pencere.yaziTipi; pixelSize: 11 }
                    }
                }
            }

            // Seviye ve XP çubuğu
            Column {
                visible: kok.width >= 820
                anchors.verticalCenter: parent.verticalCenter
                spacing: 4
                Row {
                    spacing: 8
                    Text {
                        text: ana.seviyeMetin.toLocaleUpperCase(Qt.locale("tr_TR"))
                        color: r.baslik
                        font { family: pencere.yaziTipi; pixelSize: 11; weight: Font.DemiBold; letterSpacing: 1 }
                    }
                    Text {
                        text: ana.xpMetin
                        color: r.soluk
                        font { family: pencere.yaziTipi; pixelSize: 11 }
                    }
                }
                Rectangle {
                    width: 96; height: 2
                    color: r.cizgi
                    Rectangle {
                        width: parent.width * ana.xpOrani; height: 2
                        color: r.vurgu
                        Behavior on width { NumberAnimation { duration: 300 } }
                    }
                }
            }

            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 14
                TusIpucu { tus: "F4"; etiket: ""; etkin: ana.panel; onTiklandi: ana.panelDegistir() }
                TusIpucu { tus: "F9"; etiket: m.zen; onTiklandi: ana.zenDegistir() }
                TusIpucu { tus: "Esc"; etiket: ""; onTiklandi: pencere.menuAc() }
            }
        }

        Rectangle {
            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
            height: 1
            color: r.cizgi
            opacity: zen ? 0 : 1
            Behavior on opacity { NumberAnimation { duration: 200 } }
        }
    }

    // -- harf çipleri ve günlük hedef ------------------------------------------------------
    Item {
        id: cipSeridi
        anchors { top: baslik.bottom; left: parent.left; right: parent.right }
        height: 58
        opacity: zen ? 0 : 1
        Behavior on opacity { NumberAnimation { duration: 160 } }

        Row {
            id: cipler
            anchors { left: parent.left; leftMargin: 28; verticalCenter: parent.verticalCenter }
            readonly property real yer: kok.width - 56 - (gunluk.visible ? gunluk.width + 40 : 0)
            readonly property real cipGenislik: Math.max(14, Math.min(26, yer / Math.max(1, ana.harfler.length) - spacing))
            spacing: 4
            Repeater {
                model: ana.harfler
                delegate: HarfCipi { required property var modelData; veri: modelData; width: cipler.cipGenislik }
            }
        }

        Row {
            id: gunluk
            anchors { right: parent.right; rightMargin: 28; verticalCenter: parent.verticalCenter }
            spacing: 14
            visible: kok.width >= 1000
            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: ana.seriMetin
                visible: text !== ""
                color: r.uyari
                font { family: pencere.yaziTipi; pixelSize: 12; weight: Font.DemiBold }
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 5
                Text {
                    anchors.right: parent.right
                    text: ana.gunlukMetin
                    color: ana.gunlukOran >= 1 ? r.dogru : r.yazi
                    font { family: pencere.yaziTipi; pixelSize: 12 }
                }
                Rectangle {
                    width: 140; height: 2
                    color: r.cizgi
                    Rectangle {
                        width: parent.width * ana.gunlukOran; height: 2
                        color: ana.gunlukOran >= 1 ? r.dogru : r.vurgu
                        Behavior on width { NumberAnimation { duration: 300 } }
                    }
                }
            }
        }

        Rectangle {
            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
            height: 1
            color: r.cizgi
        }
    }
}
