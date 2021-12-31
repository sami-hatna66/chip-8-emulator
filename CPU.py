import Screen
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, QUrl, Qt
from PyQt5.QtMultimedia import QSoundEffect
import sys
import random
import time

class CPU:
    def __init__(self, screen):
        self.screen = screen
        self.screen.passCPU(cpu=self)

        # 4096 spaces
        self.memory = bytearray(4096)
        # First 512 slots in memory used for system
        self.memoryOffset = 512

        # 16 registers named V0 - VE
        self.registers = [0] * 16

        # Address register
        self.I = 0
        # Program counter
        self.PC = 512

        # Hex value of current key
        self.pressedKey = None

        # Current instruction
        self.instruction = None

        # Map of screen pixels
        self.screenMap = [[0 for x in range (0,32)] for y in range (0,64)]

        # Stack with 64 levels - for remembering previous state when making jumps
        self.stack = [None] * 16
        self.stackpointer = 0

        # For storing keypad state
        self.key = [None] * 16

        # Timers
        self.delayTimer = 0
        self.soundTimer = 0

        # Load font
        for x in range(0, len(fontSet)):
            self.memory[x] = fontSet[x]

        self.drawFlag = False

        self.instructionDict = {
            0x0: self.evaluateZero,
            0x1: self.jumpToAddress,
            0x2: self.callSubroutine,
            0x3: self.skipNextIfCondition,
            0x4: self.skipNextIfNotCondition,
            0x5: self.skipNextIfVariableSame,
            0x6: self.setVariable,
            0x7: self.addValToVar,
            0x8: self.evaluateEight,
            0x9: self.skipNextIfVariableNotSame,
            0xA: self.setIToAddress,
            0xB: self.jumpToAddressPlusV0,
            0xC: self.bitwiseAnd,
            0xD: self.drawSprite,
            0xE: self.evaluateE,
            0xF: self.evaluateF
        }

        self.beep = QSoundEffect()
        self.beep.setSource(QUrl.fromLocalFile("media/beep.wav"))
        self.beep.setVolume(0.1)

    def initialize(self):
        self.memory = bytearray(4096)
        self.memoryOffset = 512
        self.registers = [0] * 16
        self.I = 0
        self.PC = 512
        self.pressedKey = None
        self.instruction = None
        self.screenMap = [[0 for x in range(0, 32)] for y in range(0, 64)]
        self.stack = [None] * 16
        self.stackpointer = 0
        self.key = [None] * 16
        self.delayTimer = 0
        self.soundTimer = 0
        for x in range(0, len(fontSet)):
            self.memory[x] = fontSet[x]
        self.drawFlag = False

    def keyPressAction(self, key):
        mapKey = {
            Qt.Key_1: 0x1,
            Qt.Key_2: 0x2,
            Qt.Key_3: 0x3,
            Qt.Key_4: 0xC,
            Qt.Key_Q: 0x4,
            Qt.Key_W: 0x5,
            Qt.Key_E: 0x6,
            Qt.Key_R: 0xD,
            Qt.Key_A: 0x7,
            Qt.Key_S: 0x8,
            Qt.Key_D: 0x9,
            Qt.Key_F: 0xE,
            Qt.Key_Z: 0xA,
            Qt.Key_X: 0x0,
            Qt.Key_C: 0xB,
            Qt.Key_V: 0xF
        }
        self.pressedKey = mapKey[key]

    def keyReleaseAction(self):
        self.pressedKey = None

    def loadRom(self, romPath):
        binary = open(romPath, 'rb').read()
        for index, value in enumerate(binary):
            self.memory[self.memoryOffset + index] = value

    def run(self):
        self.thread = emuThread(screen=self.screen, cpu=self)
        self.thread.start()

    def playPauseSlot(self):
        if self.thread.isRunning():
            self.thread.running = False
            return True
        else:
            self.thread.running = True
            self.thread.start()
            return False

    def menuSlot(self):
        if self.thread.isRunning():
            self.thread.running = False

    def fdeCycle(self):
        # Perform left shift on opcode then combine with operand using bitwise OR
        self.instruction = (self.memory[self.PC] << 8) | self.memory[self.PC + 1]

        # N
        # self.instruction & 0xFFF >> 8
        # NN
        # self.instruction & 0xFFF >> 4
        # NNN
        # self.instruction & 0xFFF
        # X
        # (self.instruction & 0xFFF) >> 8
        # Y
        # (self.instruction & 0xFF) >> 4

        self.PC += 2

        # Right shift by twelve to get first three hex digits
        self.instructionDict[self.instruction >> 12]()

        if self.delayTimer > 0:
            self.delayTimer -= 1
        if self.soundTimer > 0:
            if self.soundTimer == 1:
                self.beep.stop()
                self.beep.play()
            self.soundTimer -= 1

    def evaluateZero(self):
        if self.instruction == 0x00E0:
            self.screenMap = [[0 for x in range (0,32)] for y in range (0,64)]
            self.drawFlag = True
        elif self.instruction == 0x00EE:
            self.stackpointer -= 1
            self.PC = self.stack[self.stackpointer]
            self.stack[self.stackpointer] = None

    def jumpToAddress(self):
        self.PC = self.instruction & 0xFFF

    def callSubroutine(self):
        self.stack[self.stackpointer] = self.PC
        self.stackpointer += 1
        self.PC = self.instruction & 0xFFF

    def skipNextIfCondition(self):
        if self.registers[(self.instruction & 0xFFF) >> 8] == self.instruction & 0xFFF >> 4:
            self.PC += 2

    def skipNextIfNotCondition(self):
        if self.registers[(self.instruction & 0xFFF) >> 8] != self.instruction & 0xFFF >> 4:
            self.PC += 2

    def skipNextIfVariableSame(self):
        if self.registers[(self.instruction & 0xFFF) >> 8] == self.registers[(self.instruction & 0xFF) >> 4]:
            self.PC += 2

    def setVariable(self):
        self.registers[(self.instruction & 0xFFF) >> 8] = self.instruction & 0xFFF >> 4

    def addValToVar(self):
        result = self.registers[(self.instruction & 0xFFF) >> 8] + self.instruction & 0xFFF >> 4
        if result > 255:
            self.registers[(self.instruction & 0xFFF) >> 8] = result - 256
        else:
            self.registers[(self.instruction & 0xFFF) >> 8] = result

    def evaluateEight(self):
        N = self.instruction & 0xFFF >> 8
        if N == 0x0:
            self.registers[(self.instruction & 0xFFF) >> 8] = self.registers[(self.instruction & 0xFF) >> 4]
        elif N == 0x1:
            self.registers[(self.instruction & 0xFFF) >> 8] = self.registers[(self.instruction & 0xFFF) >> 8] | \
                                                              self.registers[(self.instruction & 0xFF) >> 4]
        elif N == 0x2:
            self.registers[(self.instruction & 0xFFF) >> 8] = self.registers[(self.instruction & 0xFFF) >> 8] & \
                                                              self.registers[(self.instruction & 0xFF) >> 4]
        elif N == 0x3:
            self.registers[(self.instruction & 0xFFF) >> 8] = self.registers[(self.instruction & 0xFFF) >> 8] ^ \
                                                              self.registers[(self.instruction & 0xFF) >> 4]
        elif N == 0x4:
            result = self.registers[(self.instruction & 0xFFF) >> 8] + self.registers[(self.instruction & 0xFF) >> 4]
            if result > 255:
                self.registers[(self.instruction & 0xFFF) >> 8] = result - 256
                self.registers[15] = 1
            else:
                self.registers[(self.instruction & 0xFFF) >> 8] = result
                self.registers[15] = 0
        elif N == 0x5:
            if self.registers[(self.instruction & 0xFFF) >> 8] >= self.registers[(self.instruction & 0xFF) >> 4]:
                self.registers[15] = 1
                self.registers[(self.instruction & 0xFFF) >> 8] -= self.registers[(self.instruction & 0xFF) >> 4]
            else:
                self.registers[15] = 0
                self.registers[(self.instruction & 0xFFF) >> 8] = 256 + self.registers[(self.instruction & 0xFFF) >> 8] \
                                                                  - self.registers[(self.instruction & 0xFF) >> 4]
        elif N == 0x6:
            X = (self.instruction & 0xFFF) >> 8
            self.registers[15] = not not self.registers[X] & 0x1
            self.registers[X] >>= 1
        elif N == 0x7:
            if self.registers[(self.instruction & 0xFF) >> 4] >= self.registers[(self.instruction & 0xFFF) >> 8]:
                self.registers[15] = 1
                self.registers[(self.instruction & 0xFF) >> 4] -= self.registers[(self.instruction & 0xFFF) >> 8]
            else:
                self.registers[15] = 0
                self.registers[(self.instruction & 0xFF) >> 4] = 256 + self.registers[(self.instruction & 0xFF) >> 4] - \
                                                                 self.registers[(self.instruction & 0xFFF) >> 8]
        elif N == 0xe:
            X = (self.instruction & 0x0F00) >> 8
            self.registers[15] = not not self.registers[X] & (1<<7)
            self.registers[X] <<= 1

    def skipNextIfVariableNotSame(self):
        if self.registers[(self.instruction & 0xFFF) >> 8] != self.registers[(self.instruction & 0xFF) >> 4]:
            self.PC += 2

    def setIToAddress(self):
        self.I = self.instruction & 0xFFF

    def jumpToAddressPlusV0(self):
        self.PC = self.registers[0] + (self.instruction & 0xFFF)

    def bitwiseAnd(self):
        self.registers[(self.instruction & 0xFFF) >> 8] = random.randint(0, 255) & (self.instruction & 0xFFF >> 4)

    def drawSprite(self):
        X = (self.instruction & 0xFFF) >> 8
        Y = (self.instruction & 0xFF) >> 4
        VY = self.registers[Y]
        height = self.instruction & 0xFFF >> 8

        self.registers[15] = 0
        for y in range(0, height):
            if VY > 31:
                break
            VX = self.registers[X]
            nthByte = bin(self.memory[self.I + y])
            nthByte = nthByte[2:].zfill(8)
            for x in range(0, 8):
                currentBit = int(nthByte[x])
                if VX > 63:
                    break
                if currentBit and self.screenMap[VX][VY]:
                    self.screenMap[VX][VY] = 0
                    self.registers[15] = 1
                elif currentBit and not self.screenMap[VX][VY]:
                    self.screenMap[VX][VY] = 1
                VX += 1

            VY += 1

        self.drawFlag = True

    def evaluateE(self):
        NN = self.instruction & 0xFFF >> 4
        if NN == 0x9E:
            if self.registers[(self.instruction & 0xFFF) >> 8] == self.pressedKey:
                self.PC += 2
        if NN == 0xA1:
            if self.registers[(self.instruction & 0xFFF) >> 8] != self.pressedKey:
                self.PC += 2

    def evaluateF(self):
        NN = self.instruction & 0xFFF >> 4
        if NN == 0x07:
            self.registers[(self.instruction & 0xFFF) >> 8] = self.delayTimer
        elif NN == 0x0A:
            if self.pressedKey is not None:
                self.registers[(self.instruction & 0xFFF) >> 8] = self.pressedKey
            else:
                self.PC -= 2
        elif NN == 0x15:
            self.delayTimer = self.registers[(self.instruction & 0xFFF) >> 8]
        elif NN == 0x18:
            self.soundTimer = self.registers[(self.instruction & 0xFFF) >> 8]
        elif NN == 0x1E:
            self.I += self.registers[(self.instruction & 0xFFF) >> 8]
        elif NN == 0x29:
            self.I = self.registers[(self.instruction & 0xFFF) >> 8] * 5
        elif NN == 0x33:
            numVX = self.registers[(self.instruction & 0xFFF) >> 8]
            for x in range(0,3):
                self.memory[self.I + x] = int(str(numVX).zfill(3)[x])
        elif NN == 0x55:
            X = (self.instruction & 0xFFF) >> 8
            for x in range(0, X+1):
                self.memory[self.I + x] = self.registers[x]
        elif NN == 0x65:
            X = (self.instruction & 0xFFF) >> 8
            for x in range(0, X+1):
                self.registers[x] = self.memory[self.I + x]

class emuThread(QThread):
    def __init__(self, screen, cpu):
        super(emuThread, self).__init__()
        self.screen = screen
        self.cpu = cpu
        self.running = True

    def run(self):
        while self.cpu.PC < 4096 and self.running:
            self.cpu.fdeCycle()

            if self.cpu.drawFlag:
                self.screen.screenMap = self.cpu.screenMap
                self.screen.update()
                self.cpu.drawFlag = False

            time.sleep(0.0001)

fontSet = [
    0xF0, 0x90, 0x90, 0x90, 0xF0,
    0x20, 0x60, 0x20, 0x20, 0x70,
    0xF0, 0x10, 0xF0, 0x80, 0xF0,
    0xF0, 0x10, 0xF0, 0x10, 0xF0,
    0x90, 0x90, 0xF0, 0x10, 0x10,
    0xF0, 0x80, 0xF0, 0x10, 0xF0,
    0xF0, 0x80, 0xF0, 0x90, 0xF0,
    0xF0, 0x10, 0x20, 0x40, 0x40,
    0xF0, 0x90, 0xF0, 0x90, 0xF0,
    0xF0, 0x90, 0xF0, 0x10, 0xF0,
    0xF0, 0x90, 0xF0, 0x90, 0x90,
    0xE0, 0x90, 0xE0, 0x90, 0xE0,
    0xF0, 0x80, 0x80, 0x80, 0xF0,
    0xE0, 0x90, 0x90, 0x90, 0xE0,
    0xF0, 0x80, 0xF0, 0x80, 0xF0,
    0xF0, 0x80, 0xF0, 0x80, 0x80
]

if __name__ == "__main__":
    App = QApplication(sys.argv)
    Screen = Screen.Screen()
    CPU = CPU(screen=Screen)
    sys.exit(App.exec())
