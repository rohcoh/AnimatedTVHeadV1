""" Configuration data for sprites """
SPRITES_PATH = __file__[:__file__.rfind('/') + 1]
SPRITES_DATA = {
    'base_image'     : SPRITES_PATH + 'base.bmp',

    'pupil_image'   : SPRITES_PATH + 'pupil.bmp',

    'eyes_image'    : SPRITES_PATH + 'eyes.bmp',

    'mouth_image'    : SPRITES_PATH + 'mouth.bmp',

    'exp_image'     : SPRITES_PATH + 'exp.bmp',

    'transparent'    : (255, 0, 255), # Transparent color (decimal values) in above images

    'pupil'         : (0, 0),

    'eyes'          : (0, 0),

    'mouth'         : (0, 0),

    'exp'           : (0, 32)
}
