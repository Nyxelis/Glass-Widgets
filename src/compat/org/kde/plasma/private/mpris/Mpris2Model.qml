import QtQuick
import org.kde.plasma.private.mpris as Mpris

QtObject {
    id: modelRoot

    readonly property var currentPlayer: Mpris.GlobalActivePlayer

    function rowCount() {
        return currentPlayer && (currentPlayer.track || currentPlayer.artist) ? 1 : 0;
    }

    function data(index, role) {
        return currentPlayer;
    }
}
