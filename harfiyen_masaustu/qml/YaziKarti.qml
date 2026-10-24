import QtQuick

// Odak kartı (mola dili): yazılacak satır, sönük sonraki satır, ilerleme çizgisi ve
// alt bilgi şeridinde durum + parmak çizgileri. Zen modunda çerçeve ve zemin kaybolur.
Item {
    id: kok
    readonly property var r: ana.renk
    readonly property var m: ana.metinler
    readonly property bool zen: pencere.zen

    // Yazı boyu: satırın en uzun hâli kartın içine sığsın.
    readonly property int icGenislik: width - (zen ? 32 : 96)
    readonly property real boy: Math.max(20, Math.min(zen ? 46 : 38,
                                         icGenislik / (Math.max(ana.satir.length, 24) * 0.62)))
    readonly property string sonrakiMetin: ana.sonraki

    height: govde.implicitHeight

    function titre() { titreme.restart() }

    FontMetrics { id: olcu; font.family: pencere.yaziTipi; font.pixelSize: kok.boy }

    Rectangle {
        id: zemin
        anchors.fill: parent
        color: zen ? "transparent" : r.yuzey
        border.color: zen ? "transparent" : r.cizgi
        border.width: 1
        Behavior on color { ColorAnimation { duration: 220 } }
        Behavior on border.color { ColorAnimation { duration: 220 } }
    }

    Column {
        id: govde
        width: parent.width

        // -- yazı -----------------------------------------------------------------------
        Item {
            width: parent.width
            height: Math.max(zen ? 200 : 170, yazi.height + (zen ? 72 : 80))

            Column {
                id: yazi
                anchors.centerIn: parent
                spacing: Math.round(kok.boy * 0.55)

                Item {
                    id: satirKutusu
                    // advanceWidth bir yöntem; yazı boyu değişince yeniden hesaplansın diye boya da bakılır
                    readonly property real adim: olcu.font.pixelSize > 0 ? olcu.advanceWidth("m") : 0
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: ana.satir.length * adim
                    height: olcu.height + 12
                    transform: Translate { id: kayma }

                    // İmleç: harfin arkasında kayan blok
                    Rectangle {
                        id: imlec
                        x: ana.konum * satirKutusu.adim - 1
                        y: 0
                        width: satirKutusu.adim + 2
                        height: parent.height
                        visible: ana.konum < ana.satir.length
                        color: flas.running ? r.hata : r.vurgu
                        Behavior on x { NumberAnimation { duration: 70; easing.type: Easing.OutCubic } }
                    }

                    Repeater {
                        model: ana.satir.length
                        delegate: Item {
                            required property int index
                            readonly property string c: ana.satir.charAt(index)
                            readonly property bool yazildi: index < ana.konum
                            readonly property bool hatali: ana.hataMaskesi.charAt(index) === "1"
                            readonly property bool simdi: index === ana.konum
                            x: index * satirKutusu.adim
                            width: satirKutusu.adim
                            height: satirKutusu.height
                            Text {
                                anchors.centerIn: parent
                                text: parent.c
                                font { family: pencere.yaziTipi; pixelSize: kok.boy }
                                color: parent.simdi ? r.vurgu_yazi
                                     : !parent.yazildi ? r.yazi
                                     : parent.hatali ? r.hata : r.soluk
                            }
                            // yanlış basılan boşluk görünsün
                            Rectangle {
                                visible: parent.c === " " && parent.yazildi && parent.hatali
                                anchors { bottom: parent.bottom; horizontalCenter: parent.horizontalCenter }
                                anchors.bottomMargin: 4
                                width: parent.width * 0.6
                                height: 2
                                color: r.hata
                            }
                        }
                    }
                }

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: text !== ""
                    text: kok.sonrakiMetin
                    color: r.soluk
                    opacity: 0.75
                    font { family: pencere.yaziTipi; pixelSize: Math.round(kok.boy * 0.62) }
                }
            }
        }

        // -- ilerleme çizgisi --------------------------------------------------------------
        Rectangle {
            width: parent.width
            height: 1
            color: zen ? "transparent" : r.cizgi
            Rectangle {
                readonly property real oran: ana.testOrani >= 0 ? ana.testOrani
                                             : (ana.satir.length ? ana.konum / ana.satir.length : 0)
                width: parent.width * oran
                height: 2
                y: -1
                color: r.vurgu
                opacity: zen ? 0.5 : 1
                Behavior on width { NumberAnimation { duration: 90 } }
            }
        }

        // -- alt bilgi ------------------------------------------------------------------------
        Item {
            width: parent.width
            height: 44

            Text {
                anchors { left: parent.left; leftMargin: 22; verticalCenter: parent.verticalCenter }
                width: parent.width / 2 - 140
                elide: Text.ElideRight
                visible: !zen
                text: ana.durum
                color: ana.testOrani >= 0 ? r.vurgu : r.soluk
                font { family: pencere.yaziTipi; pixelSize: 13 }
            }

            ParmakCizgileri {
                anchors { horizontalCenter: parent.horizontalCenter; verticalCenter: parent.verticalCenter }
                sira: ana.parmakSirasi
            }

            TusIpucu {
                anchors { right: parent.right; rightMargin: 22; verticalCenter: parent.verticalCenter }
                visible: !zen
                tus: "Tab"
                etiket: m.atla
                onTiklandi: ana.satirAtla()
            }
        }
    }

    Timer { id: flas; interval: 350 }

    SequentialAnimation {
        id: titreme
        ScriptAction { script: flas.restart() }
        NumberAnimation { target: kayma; property: "x"; to: -4; duration: 40 }
        NumberAnimation { target: kayma; property: "x"; to: 4; duration: 60 }
        NumberAnimation { target: kayma; property: "x"; to: 0; duration: 50 }
    }
}
