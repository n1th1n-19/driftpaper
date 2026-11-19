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
        // PauseAllScreens: a maximized window on any monitor pauses every monitor
        filterByScreen: !root.configuration.PauseAllScreens
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
    // Screen.virtualX/Y don't notify, so a binding on them goes stale and the second monitor ends up
    // watching the first monitor's windows. Look this screen up by name and set the rect explicitly.
    // Screen.name is only right at load time (it later reports the primary screen), so remember it once.
    property string myScreen: ""
    function updateGeometry() {
        if (!myScreen) myScreen = Screen.name;
        for (const s of Qt.application.screens) {
            if (s.name === myScreen) {
                tasks.screenGeometry = Qt.rect(s.virtualX, s.virtualY, s.width, s.height);
                break;
            }
        }
        recount();
    }
    Connections { target: Qt.application; function onScreensChanged() { root.updateGeometry() } }
    Component.onCompleted: { updateGeometry(); if (video && !shouldPause) player.play() }
}
