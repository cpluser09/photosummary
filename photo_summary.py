import os
import sys
import glob
#import json
#import requests
import exifread
from os.path import isfile, join
from os import listdir, path, remove
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps


PICTURE_FOLDER  = ""
PREPROCESS_FLAG = "_2000."
MY_SPECIAL_TAG  = "_lcy"
SUMMARY_FILE_NAME = "summary.jpg"

OPT_PRINT_FILE_NAME         = 0
is_read_row                 = 0
OPT_MAX_ROW_IN_SUMMRARY     = 20
is_read_column              = 0
OPT_MAX_COLUMN_IN_SUMMRARY  = 5

ORIENT_ROTATES = {"Horizontal (normal)":1, "Mirrored horizontal":2, "Rotated 180":3, "Mirrored vertical":4,
                  "Mirrored horizontal then rotated 90 CCW":5, "Rotated 90 CW":6, "Mirrored horizontal then rotated 90 CW":7, "Rotated 90 CCW":8}

def check_orientation(image, exif):
    orientation = 1
    if "Image Orientation" in exif.keys():
        orientation = ORIENT_ROTATES[exif["Image Orientation"].printable]
    if orientation == 1:
        return image
    elif orientation == 2:
        # left-to-right mirror
        return ImageOps.mirror(image)
    elif orientation == 3:
        # rotate 180
        return image.transpose(Image.ROTATE_180)
    elif orientation == 4:
        # top-to-bottom mirror
        return ImageOps.flip(image)
    elif orientation == 5:
        # top-to-left mirror
        return ImageOps.mirror(image.transpose(Image.ROTATE_270))
    elif orientation == 6:
        # rotate 270
        return image.transpose(Image.ROTATE_270)
    elif orientation == 7:
        # top-to-right mirror
        return ImageOps.mirror(image.transpose(Image.ROTATE_90))
    elif orientation == 8:
        # rotate 90
        return image.transpose(Image.ROTATE_90)
    else:
        return image

def search_files(dirname):
    filter = [".jpg", ".JPG", ".jpeg", ".JPEG"]
    result = []

    for filename in os.listdir(dirname):
        apath = os.path.join(dirname, filename)
        ext = os.path.splitext(apath)[1]
        if ext in filter and SUMMARY_FILE_NAME not in filename:
            if -1 == apath.find(MY_SPECIAL_TAG):
                if PREPROCESS_FLAG == "" or -1 != apath.find(PREPROCESS_FLAG):
                    result.append(apath)
    result = sorted(result)
    return result

def usage():
	print ("""
usage: add_frame [path_of_picture][-h][-v]

arguments:
    path_of_picture	    path of JPG file
    -i                  ignore PREPROCESS_FLAG("_2000.") flag from source picture
    -c                  column count in summary file
    -r                  row count in summary file
    -h, --help			show this help message and exit
    -v, --version		show version information and exit
""")

def draw_frame(ctx, x, y, width, height, color, line_width):
    offset = 2
    ctx.line((x-offset, y, x+width+offset, y), color, line_width)
    ctx.line((x+width, y, x+width, y+height), color, line_width+1)
    ctx.line((x+width+offset, y+height, x-offset, y+height), color, line_width)
    ctx.line((x, y+height, x, y), color, line_width+1)

def draw_thumbnail(input_file, bg_img, left, top, width, height):
    rect_left, rect_top = left, top
    file_name = os.path.basename(input_file)
    imgexif = open(input_file, 'rb')
    exif = exifread.process_file(imgexif)
    
    # check landscape or portrait
    origin_file = Image.open(input_file).convert("RGBA")
    origin_file = check_orientation(origin_file, exif)
    origin_width, origin_height = origin_file.size
    is_landscape = (origin_width > origin_height)

    # calculate size using landscape by default
    resize_width    = width
    resize_height   = (int)(resize_width * origin_height / origin_width)

    if is_landscape == True:
        left = left
        top += (int)((height - resize_height) / 2)
    else:
        resize_height   = height
        resize_width    = (int)(resize_height * origin_width / origin_height)
        left += (int)((width - resize_width) / 2)
        top = top

    img_resize = origin_file.resize((resize_width, resize_height), Image.ANTIALIAS)
    bg_img.paste(img_resize, (left, top))

    ctx = ImageDraw.Draw(bg_img)
    draw_frame(ctx, rect_left, rect_top, width, height, "black", 3)
    if OPT_PRINT_FILE_NAME == 1:
        ctx.text((rect_left, rect_top - 12), file_name, font=ImageFont.truetype("FZWBJW.TTF", 10), fill=(0,0,0))

def write_summary_file(bg_img, summary_file_count):
    if bg_img == None:
        return
    bg_img = bg_img.convert("RGB")
    output_full_path = ("%s/__%d_%s" % (PICTURE_FOLDER, summary_file_count, SUMMARY_FILE_NAME))
    bg_img.save(output_full_path, quality=100)
    print(output_full_path)


def process():
    # search 
    files = search_files(PICTURE_FOLDER)
    if len(files) == 0:
        print("no file found. %s" % PICTURE_FOLDER)
        sys.exit()
    
    thumbnail_width         = 230
    thumbnail_height        = 230
    photo_count_each_row    = OPT_MAX_COLUMN_IN_SUMMRARY
    gap_x                   = 20
    gap_y                   = 20
    margin_x                = (int)(thumbnail_width / 2)
    margin_y                = (int)(thumbnail_height / 2)
    row_count               = (int)(len(files) / photo_count_each_row)
    if len(files) % photo_count_each_row > 0:
        row_count += 1
    if row_count > OPT_MAX_ROW_IN_SUMMRARY:
        row_count = OPT_MAX_ROW_IN_SUMMRARY
    if OPT_PRINT_FILE_NAME == 1:
        gap_y += 12

    bg_width    = thumbnail_width * photo_count_each_row + gap_x * (photo_count_each_row-1) + margin_x * 2
    bg_height   = thumbnail_height * row_count + gap_y * (row_count-1) + margin_y * 2
    #print("%d,%d   %d,%d" % (bg_width, bg_height, row_count, photo_count_each_row))

    idx     = 1
    left    = 0
    top     = 0
    row     = 0
    column  = 0
    bg_img  = None
    summary_file_count = 0
    for each_picture in files:
        if bg_img == None:
            bg_img = Image.new('RGBA', (bg_width, bg_height), (255, 255, 255))

        left    = margin_x + gap_x * column + thumbnail_width * column
        top     = margin_y + gap_y * row + thumbnail_height * row 
        print("\nNo.%04d: %d,%d" % (idx, left, top))
        draw_thumbnail(each_picture, bg_img, left, top, thumbnail_width, thumbnail_height)

        idx     += 1
        column  += 1
        if column % photo_count_each_row == 0:
            left    = 0
            column  = 0
            row     += 1
        if row >= OPT_MAX_ROW_IN_SUMMRARY:
            write_summary_file(bg_img, summary_file_count)
            # again
            row = 0
            bg_img = None
            summary_file_count += 1
   
    # write file
    write_summary_file(bg_img, summary_file_count)
    print ("\nDONE.")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("arguments error!\r\n-h shows usage.")
        # PICTURE_FOLDER = "/Users/junlin/test/gps"
        # process()
        sys.exit()
    for arg in sys.argv[1:]:
        if arg == '-v' or arg == "--version":
            print("1.0.0")
            sys.exit()
        elif arg == '-h' or arg == '--help':
            usage()
            sys.exit()
        elif arg == '-i' or arg == '--ignore':
            PREPROCESS_FLAG = ""
        elif arg == '-p' or arg == '--print':
            OPT_PRINT_FILE_NAME = 1
        elif arg == '-c' or arg == '--column':
            is_read_column = 1
        elif arg == '-r' or arg == '--row':
            is_read_row = 1
        elif is_read_column == 1:
            is_read_column = 0
            OPT_MAX_COLUMN_IN_SUMMRARY = int(arg)
        elif is_read_row == 1:
            is_read_row = 0
            OPT_MAX_ROW_IN_SUMMRARY = int(arg)

    PICTURE_FOLDER = sys.argv[1]
    process()



