import os
import sys
import glob
import json
import requests
import exifread
from os.path import isfile, join
from os import listdir, path, remove
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps


PICTURE_FOLDER  = ""
PREPROCESS_FLAG = "_2000."
MY_SPECIAL_TAG  = "_lcy"
SUMMARY_FILE_NAME = "mobile.jpg"
OPT_MAX_ROW_IN_SUMMRARY     = 1



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
        if ext in filter and "mobile" not in filename:
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
    -w                  thumbnail width
    --height            thumbnail height
    -h, --help			show this help message and exit
    -v, --version		show version information and exit
""")

def query_addr(exif):
    if "GPS GPSLongitudeRef" not in exif.keys():
        return ""
    # 经度
    lon_ref = exif["GPS GPSLongitudeRef"].printable
    lon = exif["GPS GPSLongitude"].printable[1:-1].replace(" ", "").replace("/", ",").split(",")
    if len(lon) < 4:
        return ""
    lon = float(lon[0]) + float(lon[1]) / 60 + float(lon[2]) / float(lon[3]) / 3600
    if lon_ref != "E":
        lon = lon * (-1)
    # 纬度
    lat_ref = exif["GPS GPSLatitudeRef"].printable
    lat = exif["GPS GPSLatitude"].printable[1:-1].replace(" ", "").replace("/", ",").split(",")
    if len(lat) < 4:
        return ""
    lat = float(lat[0]) + float(lat[1]) / 60 + float(lat[2]) / float(lat[3]) / 3600
    if lat_ref != "N":
        lat = lat * (-1)
    #print('照片的经纬度：', (lat, lon))
    # 调用百度地图api转换经纬度为详细地址
    secret_key = '1flkRi6QA71FrifGk4yFEB6jGtWOpFxC' # 百度地图api 填入你自己的key
    baidu_map_api = 'http://api.map.baidu.com/reverse_geocoding/v3/?ak={}&output=json&coordtype=wgs84ll&location={},{}'.format(secret_key, lat, lon)
    content = requests.get(baidu_map_api).text
    gps_address = json.loads(content)
    # 结构化的地址
    formatted_address = gps_address["result"]["formatted_address"]
    # 国家（若需访问境外POI，需申请逆地理编码境外POI服务权限）
    country = gps_address["result"]["addressComponent"]["country"]
    # 省
    province = gps_address["result"]["addressComponent"]["province"]
    # 市
    city = gps_address["result"]["addressComponent"]["city"]
    # 区
    district = gps_address["result"]["addressComponent"]["district"]
    # 街
    street = gps_address["result"]["addressComponent"]["street"]
    # 语义化地址描述
    sematic_description = gps_address["result"]["sematic_description"]
    #print(formatted_address)
    #print(city)
    #print(street)
    #print(gps_address["result"]["business"])
    idx = street.find("路")
    if idx != -1:
        street = street[0:idx+1]
    return street + " " + city.replace("市", "")

def get_basic_info(exif):
    # shot time
    shot_time = "unkown shot time"
    date_time = ""
    if "EXIF DateTimeOriginal" in exif.keys():
        shot_time = exif["EXIF DateTimeOriginal"].printable
        date_time = shot_time.split(" ", 1)[0]
        date_time = date_time.split(":")
        date_time = ("%s-%d-%d" % (date_time[0][0:4], int(date_time[1]), int(date_time[2])))
    desc = query_addr(exif)
    return (date_time, shot_time, desc)

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
    #draw_frame(ctx, rect_left, rect_top, width, height, "black", 3)
    date_time, shot_time, desc = get_basic_info(exif)
    ctx.text((left, top + resize_height + 4), date_time + " " + desc, font=ImageFont.truetype("FZWBJW.TTF", 22), fill=(60, 60, 60))

def write_summary_file(bg_img, summary_file_count):
    if bg_img == None:
        return
    bg_img = bg_img.rotate(270.0, resample=Image.NEAREST, expand=1)
    bg_img = bg_img.convert("RGB")
    output_full_path = ("%s/__%d_%s" % (PICTURE_FOLDER, summary_file_count, SUMMARY_FILE_NAME))
    bg_img.save(output_full_path, quality=100)
    print(output_full_path)


def process():
    # search 
    files = search_files(PICTURE_FOLDER)
    total_file_count = len(files)
    if total_file_count == 0:
        print("no file found. %s" % PICTURE_FOLDER)
        sys.exit()
    
    thumbnail_width         = 560 * 2
    thumbnail_height        = 420 * 2
    photo_count_each_row    = total_file_count
    gap_x                   = 20 * 3
    gap_y                   = 20
    margin_x                = 20
    margin_y                = 20
    row_count               = 1

    bg_width    = thumbnail_width * photo_count_each_row + gap_x * (photo_count_each_row-1) + margin_x * 2
    bg_height   = thumbnail_height * row_count + gap_y * (row_count-1) + margin_y * 2 + 20
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
        print("\nNo.%04d: left %04d, row %d,  %s" % (idx, total_file_count-idx, row, each_picture))
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
    if bg_img != None:
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

    PICTURE_FOLDER = sys.argv[1]
    process()



