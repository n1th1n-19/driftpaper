import QtQuick
import QtQuick.Window
import QtMultimedia
import org.kde.plasma.plasmoid
import org.kde.plasma.plasma5support as P5Support
import org.kde.taskmanager as TaskManager

WallpaperItem {
    id: root
    readonly property string video: root.configuration.Video
    readonly property bool onBattery: pm.data["AC Adapter"] ? !pm.data["AC Adapter"]["Plugged in"] : false
    property bool covered: false
    readonly property bool shouldPause:
        (root.configuration.PauseMaximized && covered)
        || (root.configuration.PauseOnBattery && onBattery)

    P5Support.DataSource {
        id: pm
        engine: "powermanagement"
        connectedSources: ["AC Adapter"]
    }

    // maximized/fullscreen, non-minimized window on this screen
    TaskManager.TasksModel {
        id: tasks
        filterByScreen: true
        screenGeometry: Qt.rect(Screen.virtualX, Screen.virtualY, Screen.width, Screen.height)
        filterMinimized: true
        groupMode: TaskManager.TasksModel.GroupDisabled
        onDataChanged: root.recount()
        onCountChanged: root.recount()
    }
    function recount() {
        for (let i = 0; i < tasks.count; ++i) {
            const ix = tasks.index(i, 0);
            if (tasks.data(ix, TaskManager.AbstractTasksModel.IsMaximized) || tasks.data(ix, TaskManager.AbstractTasksModel.IsFullScreen)) {
                covered = true; return;
            }
        }
        covered = false;
    }

    Rectangle { anchors.fill: parent; color: "black" }

    MediaPlayer {
        id: player
        source: root.video
        loops: MediaPlayer.Infinite
        videoOutput: out
        onSourceChanged: if (!root.shouldPause) play()
    }
    VideoOutput {
        id: out
        anchors.fill: parent
        fillMode: VideoOutput.PreserveAspectCrop
    }
    onShouldPauseChanged: shouldPause ? player.pause() : player.play()
    Component.onCompleted: { recount(); if (video && !shouldPause) player.play() }
}
