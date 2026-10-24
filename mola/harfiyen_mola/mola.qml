import QtQuick
import QtQuick.Window
import org.kde.layershell 1.0 as LayerShell

// Tüm ekranı kaplayan, üst katmanda (tam ekran videonun da üstünde) duran pencere.
Window {
    id: pencere

    readonly property var r: mola.renk
    readonly property string yaziTipi: "JetBrains Mono"

    visible: mola.gorunur
    color: "transparent"
    title: "Harfiyen Mola"

    LayerShell.Window.scope: "harfiyen-mola"
    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorBottom
                               | LayerShell.Window.AnchorLeft | LayerShell.Window.AnchorRight
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.keyboardInteractivity: klavyeAl
                                             ? LayerShell.Window.KeyboardInteractivityExclusive
                                             : LayerShell.Window.KeyboardInteractivityNone
    LayerShell.Window.wantsToBeOnActiveScreen: true

    onVisibleChanged: if (visible) { girdi.forceActiveFocus(); perde.opacity = 0; perdeAc.restart() }

    // Arkadaki videoyu karartan perde; tıklamaları da yutar.
    Rectangle {
        id: perde
        anchors.fill: parent
        color: "#000000"
        opacity: 0
        NumberAnimation on opacity { id: perdeAc; to: 0.82; duration: 180; running: false }
        MouseArea { anchors.fill: parent; onPressed: girdi.forceActiveFocus() }
    }

    Item {
        id: girdi
        anchors.fill: parent
        focus: true
        Keys.onPressed: (olay) => {
            olay.accepted = true
            if (olay.key === Qt.Key_Escape) {
                mola.atla()
            } else if (olay.text.length === 1 && olay.text >= " ") {
                mola.tus(olay.text)
            }
        }
    }

    Rectangle {
        id: kart
        anchors.centerIn: parent
        width: Math.min(pencere.width - 64, Math.max(720, satirOlcu.width + 120))
        height: govde.implicitHeight
        color: r.zemin
        border.color: r.cizgi
        border.width: 1
        opacity: perde.opacity / 0.82
        scale: 0.97 + 0.03 * opacity

        Column {
            id: govde
            width: parent.width

            // -- başlık ---------------------------------------------------------
            Item {
                width: parent.width
                height: 46
                Text {
                    anchors { left: parent.left; leftMargin: 22; verticalCenter: parent.verticalCenter }
                    text: "HARFİYEN  ·  MOLA"
                    font { family: yaziTipi; pixelSize: 14; weight: Font.DemiBold; letterSpacing: 2 }
                    color: r.baslik
                }
                Text {
                    anchors { right: parent.right; rightMargin: 22; verticalCenter: parent.verticalCenter }
                    text: mola.medyaBilgisi ? "⏸ " + mola.medyaBilgisi : ""
                    font { family: yaziTipi; pixelSize: 13 }
                    color: r.soluk
                    elide: Text.ElideLeft
                    width: Math.min(implicitWidth, parent.width / 2)
                    horizontalAlignment: Text.AlignRight
                }
            }
            Rectangle { width: parent.width; height: 1; color: r.cizgi }

            // -- yazı -------------------------------------------------------------
            Item {
                width: parent.width
                height: Math.max(150, yaziBlogu.height + 64)

                Column {
                    id: yaziBlogu
                    anchors.centerIn: parent
                    spacing: 16
                    visible: mola.asama === "yaziyor"

                    Column {
                        id: satirOlcu
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: 6
                        Repeater {
                            model: mola.satirlar
                            delegate: Row {
                                required property var modelData
                                anchors.horizontalCenter: parent.horizontalCenter
                                Repeater {
                                    model: modelData
                                    delegate: Rectangle {
                                        required property var modelData
                                        readonly property bool simdi: modelData.durum === "simdi"
                                        width: harf.implicitWidth
                                        height: harf.implicitHeight + 8
                                        color: simdi ? (flas.running ? r.hata : r.vurgu) : "transparent"
                                        Text {
                                            id: harf
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            y: 4
                                            text: modelData.c
                                            font { family: yaziTipi; pixelSize: 34 }
                                            color: parent.simdi ? r.vurgu_yazi
                                                 : modelData.durum === "dogru" ? r.soluk
                                                 : modelData.durum === "hatali" ? r.hata
                                                 : r.yazi
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // Ayarla açılır: mola.json → "parmak_goster": true
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        visible: mola.parmakGoster
                        text: mola.parmakTarifi
                        font { family: yaziTipi; pixelSize: 15 }
                        color: mola.parmakRengi
                    }
                }

                Column {
                    anchors.centerIn: parent
                    spacing: 12
                    visible: mola.asama === "bitti"
                    // Yeni rekor rozeti: vurgu zeminli şerit, belirirken hafifçe büyüyüp oturur.
                    Rectangle {
                        id: rozet
                        anchors.horizontalCenter: parent.horizontalCenter
                        visible: mola.rekor
                        width: rozetYazi.implicitWidth + 28
                        height: rozetYazi.implicitHeight + 10
                        color: r.vurgu
                        Text {
                            id: rozetYazi
                            anchors.centerIn: parent
                            text: "★  YENİ REKOR"
                            font { family: yaziTipi; pixelSize: 15; weight: Font.Bold; letterSpacing: 2 }
                            color: r.vurgu_yazi
                        }
                        onVisibleChanged: if (visible) rozetBelir.restart()
                        SequentialAnimation {
                            id: rozetBelir
                            NumberAnimation { target: rozet; property: "scale"; from: 0.6; to: 1.12; duration: 160; easing.type: Easing.OutCubic }
                            NumberAnimation { target: rozet; property: "scale"; to: 1.0; duration: 120; easing.type: Easing.InOutQuad }
                        }
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: mola.sonuc
                        font { family: yaziTipi; pixelSize: 30 }
                        color: mola.rekor ? r.vurgu : r.dogru
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        visible: text !== ""
                        text: mola.rekorBilgisi
                        font { family: yaziTipi; pixelSize: 14 }
                        color: r.soluk
                    }
                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: mola.medyaBilgisi ? "▶ devam ediliyor" : "kapanıyor"
                        font { family: yaziTipi; pixelSize: 14 }
                        color: r.soluk
                    }
                }
            }

            // -- ilerleme çubuğu ------------------------------------------------
            Rectangle {
                width: parent.width
                height: 1
                color: r.cizgi
                Rectangle {
                    width: parent.width * mola.oran
                    height: 2
                    y: -1
                    color: r.vurgu
                    Behavior on width { NumberAnimation { duration: 90 } }
                }
            }

            // -- alt bilgi --------------------------------------------------------
            Item {
                width: parent.width
                height: 40
                Text {
                    anchors { left: parent.left; leftMargin: 22; verticalCenter: parent.verticalCenter }
                    text: mola.sayac + "    hata " + mola.hataSayisi
                    font { family: yaziTipi; pixelSize: 13 }
                    color: r.soluk
                }
                // Parmak göstergeleri: sol serçe → sol işaret | sağ işaret → sağ serçe.
                // Sıradaki karakterin parmağı yukarı kalkar ve renklenir; boşlukta hiçbiri.
                Row {
                    anchors { horizontalCenter: parent.horizontalCenter; verticalCenter: parent.verticalCenter }
                    spacing: 32
                    visible: mola.asama === "yaziyor"
                    Repeater {
                        model: 2
                        delegate: Row {
                            id: elSirasi
                            required property int index
                            readonly property int el: index
                            spacing: 8
                            Repeater {
                                model: 4
                                delegate: Item {
                                    required property int index
                                    readonly property bool basilacak: mola.parmakSirasi === elSirasi.el * 4 + index
                                    width: 24
                                    height: 12
                                    Rectangle {
                                        width: parent.width
                                        height: 3
                                        radius: 1.5
                                        y: basilacak ? 2 : 7
                                        color: basilacak ? r.vurgu : r.cizgi
                                        Behavior on y { NumberAnimation { duration: 90; easing.type: Easing.OutCubic } }
                                        Behavior on color { ColorAnimation { duration: 90 } }
                                    }
                                }
                            }
                        }
                    }
                }
                Text {
                    anchors { right: parent.right; rightMargin: 22; verticalCenter: parent.verticalCenter }
                    text: "Esc  atla"
                    font { family: yaziTipi; pixelSize: 13 }
                    color: r.soluk
                }
            }
        }
    }

    Timer { id: flas; interval: 350 }
    Connections {
        target: mola
        function onYanlis() { flas.restart() }
    }
}
