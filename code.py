import random
import time
import board
import displayio
import adafruit_imageload
import busio
import adafruit_lis3dh
from analogio import AnalogIn
from adafruit_matrixportal.matrix import Matrix
from sprites.data import SPRITES_DATA

# UTILITY FUNCTIONS AND CLASSES --------------------------------------------

class Sprite(displayio.TileGrid):
    def __init__(self, filename, transparent=None):
        bitmap, palette = adafruit_imageload.load(
            filename, bitmap=displayio.Bitmap, palette=displayio.Palette)
        if isinstance(transparent, (tuple, list)):
            closest_distance = 0x1000000
            for color_index, color in enumerate(palette):
                delta = (transparent[0] - ((color >> 16) & 0xFF),
                         transparent[1] - ((color >> 8) & 0xFF),
                         transparent[2] - (color & 0xFF))
                rgb_distance = (delta[0] * delta[0] +
                                delta[1] * delta[1] +
                                delta[2] * delta[2])
                if rgb_distance < closest_distance:
                    closest_distance = rgb_distance
                    closest_index = color_index
            palette.make_transparent(closest_index)
        elif isinstance(transparent, int):
            palette.make_transparent(transparent)
        super(Sprite, self).__init__(bitmap, pixel_shader=palette)

# SET UP
MATRIX = Matrix(bit_depth=6)
DISPLAY = MATRIX.display

# Order in which sprites are added determines the layer order
SPRITES = displayio.Group()
SPRITES.append(Sprite(SPRITES_DATA['base_image'])) #Keep opaque
SPRITES.append(Sprite(SPRITES_DATA['pupil_image'], SPRITES_DATA['transparent']))
SPRITES.append(Sprite(SPRITES_DATA['eyes_image'], SPRITES_DATA['transparent']))
SPRITES.append(Sprite(SPRITES_DATA['mouth_image'], SPRITES_DATA['transparent']))
SPRITES.append(Sprite(SPRITES_DATA['exp_image'])) #Keep opaque

DISPLAY.show(SPRITES)

MOVE_STATE = False                                     # Initially stationary
MOVE_EVENT_DURATION = random.uniform(0.1, 3)           # Time to first move
BLINK_STATE = 2                                        # Start eyes closed
BLINK_EVENT_DURATION = random.uniform(0.25, 0.5)       # Time for eyes to open
EXP_EVENT_DURATION = 1                                 # Time for expression to last
TIME_OF_LAST_TAP_EVENT = TIME_OF_LAST_EXP_EVENT = TIME_OF_LAST_BLINK_EVENT = TIME_OF_LAST_EYEMOVEMENT_EVENT = time.monotonic()

EXP_STATE = 0                                          # Expression neutral
EXP_TYPE = 0                                           # Expression type

EYEMOVEMENT_EVENT_DURATION = random.uniform(1, 10)
PUPIL_STATE = 0
PUPIL_SET_X = 0
PUPIL_SET_Y = 0


MOUTH_TYPE = 0

WIDTH = 64
HEIGHT = 32

# Audio set up
sampleWindow = 0.028  # Sample window width (0.033 sec = 33 mS = ~30 Hz)
dc_offset = 0  # DC offset in mic signal - if unusure, leave 0
noise = 800  # Noise/hum/interference in mic signal
mic_pin = board.A1
mic = AnalogIn(mic_pin)  # Getting the audio value

# PyGamer OR MatrixPortal I2C Setup:
i2c = busio.I2C(board.SCL, board.SDA)
lis3dh = adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x19)

# Set range of accelerometer (can be RANGE_2_G, RANGE_4_G, RANGE_8_G or RANGE_16_G).
lis3dh.range = adafruit_lis3dh.RANGE_2_G

# MAIN LOOP ----------------------------------------------------------------

while True:
    NOW = time.monotonic()

    # Audio mouth syncing -------------------------------------------------------------

    # Listen to mic for short interval, recording min & max signal
    signalMin = 65535
    signalMax = 0
    while (time.monotonic() - NOW) < sampleWindow:
        signal = mic.value
        if signal < signalMin:
            signalMin = signal
        if signal > signalMax:
            signalMax = signal

    peakToPeak = signalMax - signalMin  # Audio amplitude
    MOUTH_TYPE = int(((peakToPeak - 250) * 2) / 40383)  # Remove low-level noise, boost
    if MOUTH_TYPE > 3:
        MOUTH_TYPE = 3

    # Blinking -------------------------------------------------------------

    if NOW - TIME_OF_LAST_BLINK_EVENT > BLINK_EVENT_DURATION:
        TIME_OF_LAST_BLINK_EVENT = NOW  # Start change in blink
        BLINK_STATE += 1                # Cycle paused/closing/opening
        if BLINK_STATE == 1:            # Starting a new blink (closing)
            BLINK_EVENT_DURATION = random.uniform(0.03, 0.07)
        elif BLINK_STATE == 2:          # Starting de-blink (opening)
            BLINK_EVENT_DURATION *= 2
        else:                           # Blink ended,
            BLINK_STATE = 0             # paused
            BLINK_EVENT_DURATION = random.uniform(BLINK_EVENT_DURATION * 3, 5)

    if BLINK_STATE:  # Currently in a blink?
        # Fraction of closing or opening elapsed (0.0 to 1.0)
        FRAME = 0  # Open eyes frame
        if BLINK_STATE == 1:
            FRAME = 3  # Closed eyes frame
        elif BLINK_STATE == 2:     # Opening
            FRAME = FRAME - 1
            if FRAME == -1:
                FRAME += 2

    else:           # Not blinking
        FRAME = 0



    # Eye movement ---------------------------------------------------------------------
    #max 2 in the y 4 in the x negative and positive
    if NOW - TIME_OF_LAST_EYEMOVEMENT_EVENT > EYEMOVEMENT_EVENT_DURATION:
        TIME_OF_LAST_EYEMOVEMENT_EVENT = NOW
        PUPIL_STATE += 1
        if PUPIL_STATE == 1:
            PUPIL_SET_X = random.uniform(-5.5,5.6)
            PUPIL_SET_Y = random.uniform(-0.5,5.6)
            EYEMOVEMENT_EVENT_DURATION = random.uniform(0.01,3.6) #Move pupil back
        else:
            PUPIL_SET_X = 0
            PUPIL_SET_Y = 0
            PUPIL_STATE = 0
            EYEMOVEMENT_EVENT_DURATION = random.uniform(0.5,8.5)

    # Expression Changing -------------------------------------------------------------

    # Read accelerometer values (in m / s ^ 2).  Returns a 3-tuple of x, y,
    # z axis values.  Divide them by 9.806 to convert to Gs.
    x, y, z = [
        value / adafruit_lis3dh.STANDARD_GRAVITY for value in lis3dh.acceleration
    ]

    # Expression change according to accelerometer values
    if x:
        NUDGE = 0
        if x > 0.4:
            TIME_OF_LAST_EXP_EVENT = NOW
            EXP_SWITCH = 1
            NUDGE = 1
            EXP_STATE = 0
            EXP_TYPE += 1
            if EXP_TYPE == 4:
                EXP_TYPE = 3
        elif x < -0.4:
            TIME_OF_LAST_EXP_EVENT = NOW
            EXP_SWITCH = 1
            NUDGE = 1
            EXP_STATE = 1
            EXP_TYPE += 1
            if EXP_TYPE == 4:
                EXP_TYPE = 3
        else:
            NUDGE = NUDGE - 1
            if NUDGE == -1:
               NUDGE = 0
            if NOW - TIME_OF_LAST_EXP_EVENT > EXP_EVENT_DURATION:
                EXP_TYPE = EXP_TYPE - 1
                if EXP_TYPE == -1:
                    EXP_TYPE = 0
                    EXP_SWITCH = 0

    if z:
        if z > 0.4:
            TIME_OF_LAST_EXP_EVENT = NOW
            EXP_SWITCH = 1
            NUDGE = 1
            EXP_STATE = 3
            EXP_TYPE += 1
            if EXP_TYPE == 4:
                EXP_TYPE = 3
        elif z < -0.4:
            TIME_OF_LAST_EXP_EVENT = NOW
            EXP_SWITCH = 1
            NUDGE = 1
            EXP_STATE = 2
            EXP_TYPE += 1
            if EXP_TYPE == 4:
                EXP_TYPE = 3
        else:
            NUDGE = NUDGE - 1
            if NUDGE == -1:
               NUDGE = 0
            if NOW - TIME_OF_LAST_EXP_EVENT > EXP_EVENT_DURATION:
                EXP_TYPE = EXP_TYPE - 1
                if EXP_TYPE == -1:
                    EXP_TYPE = 0
                    EXP_SWITCH = 0

    # Then interpolate between closed position and open position

    PUPIL_POS = (PUPIL_SET_X,
                 PUPIL_SET_Y)
    
    EYES_POS = (SPRITES_DATA['eyes'][0],
                SPRITES_DATA['eyes'][1] - FRAME * HEIGHT)

    MOUTH_POS = (SPRITES_DATA['mouth'][0],
                 SPRITES_DATA['mouth'][1] - MOUTH_TYPE * HEIGHT)

    EXP_POS = (SPRITES_DATA['exp'][0] - EXP_STATE * WIDTH,
               SPRITES_DATA['exp'][1] - EXP_TYPE * HEIGHT)


    # Move sprites -----------------------------------------------------
    SPRITES[1].x, SPRITES[1].y = (int(PUPIL_POS[0]),
                                  int(PUPIL_POS[1]))
    SPRITES[2].x, SPRITES[2].y = (int(EYES_POS[0]),
                                  int(EYES_POS[1]))
    SPRITES[3].x, SPRITES[3].y = (int(MOUTH_POS[0]),
                                  int(MOUTH_POS[1]))
    SPRITES[4].x, SPRITES[4].y = (int(EXP_POS[0]),
                                  int(EXP_POS[1]))


