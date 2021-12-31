from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QBrush, QPen, QPolygon, QColor, QPixmap, QFont, QKeySequence
from PyQt5.QtWidgets import QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QShortcut
import sys

class Screen(QMainWindow):
    def __init__(self):
        super(Screen, self).__init__()

        # Chip 8 screen is 64x32
        # Scaled by 10
        self.setFixedSize(640, 360)

        self.setWindowTitle("Chip-8")

        self.screenMap = [[0 for x in range (0,32)] for y in range (0,64)]

        self.setStyleSheet("background-color: black")
        self.showingMenu = True
        self.initUI()

        self.drawPause = False
        self.isMuted = False

        self.show()

    def initUI(self):
        self.clearFocus()
        self.playPauseShortcut = QShortcut(QKeySequence("Shift+P"), self)
        self.playPauseShortcut.activated.connect(self.playPauseAction)
        self.menuShortcut = QShortcut(QKeySequence("Shift+M"), self)
        self.menuShortcut.activated.connect(self.menuAction)
        self.muteShortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        self.muteShortcut.activated.connect(self.muteAction)

        self.cw = QWidget()
        self.setCentralWidget(self.cw)

        VBL = QVBoxLayout()
        self.cw.setLayout(VBL)
        VBL.addStretch()

        titleLBL = QLabel()
        titleLBL.setPixmap(QPixmap("media/chip-8-symbol.png"))
        VBL.addWidget(titleLBL)

        HBL = QHBoxLayout()
        VBL.addLayout(HBL)
        HBL.addStretch()

        lbl = QLabel("ROM file path:")
        lbl.setStyleSheet("color: white")
        HBL.addWidget(lbl)

        self.textBox = QLineEdit()
        self.textBox.setStyleSheet("background-color: black; color: white; border: 1px solid white")
        self.textBox.setFixedWidth(200)
        self.textBox.setAttribute(Qt.WA_MacShowFocusRect, False)
        HBL.addWidget(self.textBox)

        launchBTN = QPushButton("Run")
        launchBTN.setStyleSheet("""QPushButton { background-color: rgb(50,50,50); color: white; border: 1px solid white; height: 18; width: 30 }
                                    QPushButton::hover { background-color: green }
                                    QPushButton::pressed { background-color: rgb(144,238,144) }""")
        launchBTN.clicked.connect(self.runPress)
        HBL.addWidget(launchBTN)

        self.warningLBL = QLabel("Directory not found")
        self.warningLBL.setAlignment(Qt.AlignCenter)
        self.warningLBL.setStyleSheet("color: red")
        self.warningLBL.hide()
        VBL.addWidget(self.warningLBL)

        HBL.addStretch()
        VBL.addStretch()

    def playPauseAction(self):
        if not self.showingMenu:
            pause = self.cpu.playPauseSlot()
            self.drawPause = pause
            self.update()

    def menuAction(self):
        if not self.showingMenu:
            self.cpu.menuSlot()
            self.showingMenu = True
            self.setCentralWidget(self.cw)
            self.update()

    def muteAction(self):
        if self.cpu.beep.volume() == 0.1:
            self.cpu.beep.setVolume(0)
            self.isMuted = True
            self.update()
        else:
            self.cpu.beep.setVolume(0.1)
            self.isMuted = False
            self.update()

    def runPress(self):
        self.cpu.initialize()
        try:
            self.cpu.loadRom(self.textBox.text())
            success = True
        except:
            self.warningLBL.show()
            success = False
        if success:
            self.textBox.clear()
            self.cpu.run()
            self.showingMenu = False
            self.cw.setParent(None)
            self.warningLBL.hide()

    def passCPU(self, cpu):
        self.cpu = cpu

    def keyPressEvent(self, event):
        keypadArray = [Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_Q, Qt.Key_W, Qt.Key_E, Qt.Key_R, Qt.Key_A,
                       Qt.Key_S, Qt.Key_D, Qt.Key_F, Qt.Key_Z, Qt.Key_X, Qt.Key_C, Qt.Key_V]
        pressed = event.key()
        if pressed in keypadArray:
            self.cpu.keyPressAction(pressed)

    def keyReleaseEvent(self, event):
        keypadArray = [Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4, Qt.Key_Q, Qt.Key_W, Qt.Key_E, Qt.Key_R, Qt.Key_A,
                       Qt.Key_S, Qt.Key_D, Qt.Key_F, Qt.Key_Z, Qt.Key_X, Qt.Key_C, Qt.Key_V]
        if event.key() in keypadArray:
            self.cpu.keyReleaseAction()

    def paintEvent(self, event):
        if not self.showingMenu:
            painter = QPainter(self)

            for x in range (0, len(self.screenMap)):
                for y in range (0, len(self.screenMap[x])):
                    if self.screenMap[x][y]:
                        painter.setBrush(QBrush(Qt.white))
                        painter.setPen(QPen(Qt.white))
                    else:
                        painter.setBrush(QBrush(Qt.black))
                        painter.setPen(QPen(Qt.black))
                    painter.drawRect(x * 10, y * 10, 10, 10)

            painter.setBrush(QBrush(QColor(50, 50, 50)))
            painter.setPen(QPen(QColor(50, 50, 50)))
            painter.drawRect(0, 320, 640, 40)

            painter.setPen(QPen(Qt.white))
            painter.setBrush(QBrush(Qt.white))
            painter.setFont(QFont("", 10))
            painter.drawText(10, 335, "[Shift + P] = Play/Pause")
            painter.drawText(10, 350, "[Shift + M] = Show Menu")
            painter.drawText(250, 335, "[Ctrl + M] = Mute")

            if self.isMuted:
                painter.drawPolygon(QPolygon([
                    QPoint(544, 337),
                    QPoint(544, 343),
                    QPoint(549, 343),
                    QPoint(557, 350),
                    QPoint(557, 330),
                    QPoint(549, 337)
                ]))
                painter.drawLine(562, 337, 570, 343)
                painter.drawLine(562, 343, 570, 337)

            if self.drawPause:
                painter.drawRect(590, 330, 5, 20)
                painter.drawRect(600, 330, 5, 20)

            painter.end()

    def closeEvent(self, event):
        try:
            self.cpu.thread.running = False
        except:
            pass
