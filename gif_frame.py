#!/usr/bin/env python3
import os
import time
import glob
from random import randrange

import RPi.GPIO as GPIO
import ST7789
import textwrap

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("""This script requires PIL/Pillow, try:
sudo apt install python3-pil
""")

print("""
gif_frame.py - Display a image files on the LCD.
""")

images = []

realpath = os.path.dirname(os.path.realpath(__file__))
print(realpath)

images_stills = []
extensions = ('*.png', '*.jpg')  # extensions to load
for extension in extensions:
    images_stills.extend(glob.glob("%s/stills/**/%s" % (realpath, extension), recursive=True))
print(images_stills)

images_gifs = []
for file in glob.glob("%s/gifs/**/*.gif" % realpath, recursive=True):
    images_gifs.append(file)

print(images_gifs)

# Buttons
BUTTON_A = 5
BUTTON_B = 6
BUTTON_X = 16
BUTTON_Y = 24

# Onboard RGB LED
LED_R = 17
LED_G = 27
LED_B = 22

# General
SPI_PORT = 0
SPI_CS = 1
SPI_DC = 9
BACKLIGHT = 13

# Screen dimensions
WIDTH = 320
HEIGHT = 240

disp = ST7789.ST7789(
    width=WIDTH,
    height=HEIGHT,
    rotation=180,
    port=SPI_PORT,
    cs=SPI_CS,
    dc=SPI_DC,
    backlight=BACKLIGHT,
    spi_speed_hz=60 * 1000 * 1000,
    offset_left=0,
    offset_top=0
)

# Initialize display.
disp.begin()

DISPLAY_WIDTH = disp.width
DISPLAY_HEIGHT = disp.height

print('Drawing images, press Ctrl+C to exit!')

frame = 0

# Setup user buttons
GPIO.setup(BUTTON_A, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_X, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_Y, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def switch_file_list():
    global current_image_list, image_file, images, images_stills, images_gifs
    if current_image_list != "stills":
        images = images_stills
        current_image_list = "stills"
    else:
        images = images_gifs
        current_image_list = "gifs"

    if len(images) == 0:
        error_message = "Error: folder \"%s\" contains no images" % current_image_list
        print(error_message)

        error_image = render_error_message(error_message)
        disp.display(error_image)
        exit(1)

    image_file = images[0]


def display_next_image():
    global image_file, images
    print("display_next_sprite")
    next_sprite = current_image_index + 1

    if next_sprite >= len(images):
        next_sprite = 0

    display_image_by_index(next_sprite)


def display_previous_image():
    print("display_previous_sprite")
    global current_image_index, image_file, images
    next_image_index = current_image_index - 1

    if next_image_index < 0:
        next_image_index = len(images) - 1

    display_image_by_index(next_image_index)


def draw_multiple_line_text(image, text, font, text_color, text_start_height):
    """
    From ubuntu on [python PIL draw multiline text on image](https://stackoverflow.com/a/7698300/395857)
    """
    draw = ImageDraw.Draw(image)
    image_width, image_height = image.size
    y_text = text_start_height
    lines = textwrap.wrap(text, width=40)
    for line in lines:
        line_width, line_height = font.getsize(line)
        draw.text(((image_width - line_width) / 2, y_text),
                  line, font=font, fill=text_color)
        y_text += line_height


def render_error_message(error_text, text_color=(0, 0, 0), text_start_height=0):
    global DISPLAY_WIDTH, DISPLAY_HEIGHT
    image_message = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(200, 0, 0))
    font = ImageFont.load_default()
    draw_multiple_line_text(image_message, error_text, font, text_color, text_start_height)
    return image_message


def display_image_by_index(number):
    global current_image_index, image_file, image_file_extension, image, images, disp
    print("display_sprite_by_number: %s" % number)
    current_image_index = number
    image_file = images[number]

    print('Loading image: {}...'.format(image_file))
    try:
        image = Image.open(image_file)

        # Resize the image
        image_file_extension = image_file.lower().split(".")[-1]
        if image_file_extension != "gif":
            image = image.resize((WIDTH, HEIGHT))

    except BaseException as err:
        error_text = f"Unexpected {err=}, {type(err)=}"
        print(error_text)
        image = render_error_message(error_text)

    print('Draw image')
    disp.display(image)


def display_random_image():
    """
    random choose one of two lists and choose show one random image
    :return:
    """
    global images, current_image_list, image_file
    print("display_random_image")
    # choose between two lists
    image_list_index = randrange(2)

    if image_list_index == 0:
        images = images_stills
        current_image_list = "stills"
    else:
        images = images_gifs
        current_image_list = "gifs"

    image_index_to_show = randrange(len(images))
    display_image_by_index(image_index_to_show)


image = None
image_file = None
current_image_list = None
image_file_extension = None
current_image_index = 0

switch_file_list()
display_image_by_index(0)

while True:
    try:
        last_button = None

        if not GPIO.input(BUTTON_A):
            print("BUTTON_A")
            last_button = "A"
            display_random_image()
        elif not GPIO.input(BUTTON_B):
            print("BUTTON_B")
            last_button = "B"
            display_next_image()
        elif not GPIO.input(BUTTON_X):
            print("BUTTON_X")
            last_button = "X"
            switch_file_list()
            display_image_by_index(0)
        elif not GPIO.input(BUTTON_Y):
            print("BUTTON_Y")
            last_button = "Y"
            display_previous_image()

        if image_file_extension == "gif":
            image.seek(frame)
            disp.display(image.resize((DISPLAY_WIDTH, DISPLAY_HEIGHT)))
            frame += 1
            time.sleep(0.05)

    except EOFError:
        frame = 0
