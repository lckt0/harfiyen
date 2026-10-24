import QtQuick

// 4+4 ayrık sekiz kısa çizgi (sol serçe → sol işaret | sağ işaret → sağ serçe).
// Sıradaki karakterin parmağı yukarı kalkar ve vurgu rengine döner; boşlukta hiçbiri.
Row {
    id: kok
    property int sira: -1
    readonly property var r: ana.renk
    spacing: 32

    Repeater {
        model: 2
        delegate: Row {
            id: el
            required property int index
            spacing: 8
            Repeater {
                model: 4
                delegate: Item {
                    required property int index
                    readonly property bool basilacak: kok.sira === el.index * 4 + index
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
