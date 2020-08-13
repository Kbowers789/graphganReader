import sys
import cv2
import imutils
import numpy as np

target_colors = {}
crop_coords = []
click_count = 0
all_cnts = []


def crop_click(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        crop_coords.append([y, x])


def color_click(event, x, y, flags, param):
    global click_count
    if event == cv2.EVENT_LBUTTONDOWN:
        click_count += 1
        # checking that we have not exceeded the specified number of colors
        if click_count <= len(target_colors):
            print("click count:", click_count)
            key = "color" + str(click_count)
            print("Color:", blurred[y, x])
            target_colors[key] = blurred[y, x]

def get_mask_contours(name, c, img):
    global all_cnts
    # creating bounds for masking based on selected color
    c_upper_bound = np.array([min(c[0]+8, 255), min(c[1]+8, 255), min(c[2]+8, 255)], np.uint8)
    c_lower_bound = np.array([max(c[0]-8, 0), max(c[1]-8, 0), max(c[2]-8, 0)], np.uint8)
    # creating mask
    m = cv2.inRange(img, c_lower_bound, c_upper_bound)
    # processing mask to isolate blocks more clearly
    thresh = cv2.threshold(m, 160, 255, cv2.THRESH_BINARY_INV)[1]
    # cv2.imshow(name, thresh)
    kernel = np.ones((3, 3), np.uint8)
    dilation = cv2.dilate(thresh, kernel, iterations=1)
    # cv2.imshow(name, dilation)
    # cv2.waitKey(0)
    # finding contours of blocks in the thresholded & dilated image
    cnts = cv2.findContours(dilation.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    curr_pts = []
    for c in cnts:
        # finding the center of the contour
        M = cv2.moments(c)
        if M["m10"] == 0 or M["m00"] == 0 or M["m01"] == 0:
            continue

        cX = int(M["m10"] / M["m00"])
        cY = int(M["m01"] / M["m00"])
        # storing center point and current color of each contour (aka block of chart)
        curr_pts.append({"Color": name, "Point": (cY, cX)})

        cv2.circle(img, (cX, cY), 1, (255, 0, 0), -1)
        cv2.imshow("Contours", img)
        cv2.waitKey(5)
    cv2.waitKey(0)
    all_cnts.extend(curr_pts[1::])
    print("all_cnts length =",len(all_cnts))

# stitchfiddle_image.png
# c2c_dog.jpg
# c2c_paw.jpg
# c2c_owl.jpg
# CoffeeGranny_Graph.jpg
src = "CoffeeGranny_Graph.jpg"
im = cv2.imread(src)
cv2.imshow("Image", im)

# Getting chart dimensions from user - to be used as final matrix size for parsing the instructions into rows
print("Enter chart height:")
chart_y = int(input())
print("Enter chart width:")
chart_x = int(input())
print("Chart is {} blocks tall and {} blocks wide.".format(chart_y, chart_x))

# Asking user to crop image to just the chart
# will help avoid unintended white or black pixels from background or text being in the contour mapping
print("Click on Upper-Left and Lower-Right Bounds of chart to crop image. Close image when complete")
cv2.setMouseCallback("Image", crop_click)
cv2.waitKey(0)
print(crop_coords)
cropped = im[crop_coords[0][0]:crop_coords[1][0], crop_coords[0][1]:crop_coords[1][1]].copy()

# smoothing image to increase more uniform coloring of blocks
blurred = cv2.bilateralFilter(cropped, 10, 50, 50)
cv2.imshow("Smoothed", blurred)

print("How many colors are in this chart?")
color_count = int(input())
for i in range(0,color_count):
    key_name = "color"+ str(i+1)
    target_colors[key_name] = []

# grabbing each color from the blurred image
print("Click on one block for each individual color. Close window when finished.")
cv2.setMouseCallback("Smoothed", color_click)
cv2.waitKey(0)
print(target_colors)

# creating a masked image for each color
for color in target_colors.keys():
    get_mask_contours(color, target_colors[color], blurred.copy())

# sorting the list of dictionaries (containing color name as key and contour center point as value)
# by the y-coord of the point, and then by the x-coord
all_cnts = sorted(all_cnts, key=lambda p: (p["Point"]))
color_chart = []

# displaying the center of each identified contour (aka block), and storing the respective color name
for item in all_cnts:
    color_chart.append(item["Color"])
    cv2.circle(blurred, (item["Point"][1], item["Point"][0]), 1, (255, 0, 0), -1)
    cv2.imshow("Final", blurred)
    cv2.waitKey(5)
cv2.waitKey(0)

color_chart = np.array(color_chart)
print("expected number of blocks:", chart_y*chart_x)
print("array shape:", color_chart.shape)
# checking that our block count is at least lower or equal to the expected number (based on dimensions given by user)
if color_chart.shape[0] < chart_y*chart_x:
    missing = chart_y*chart_x - color_chart.shape[0]
    for i in range(0, missing):
        color_chart = np.append(color_chart, "XXX")
if color_chart.shape[0] > chart_y*chart_x:
    print("error in image processing - too many blocks: program terminating")
    sys.exit()
print("image processed fully")
# reshaping np array to match dimensions of chart, in order to properly read diagonals
color_chart = np.reshape(color_chart, (chart_y, chart_x))
print("new array shape:", color_chart.shape)
color_chart = np.flipud(color_chart)
rows = dict()
y = chart_y - 1
x = 1
curr_row = 1
reading = True
side = "inc"

while reading:
    row_key = "Row " + str(curr_row)
    if x == chart_x:
        reading = False
        continue

    if y == 0:
        blocks = np.diag(color_chart)
        side = "dec"

    if side == "inc":
        blocks = np.diag(color_chart,k=-y)
        y -= 1

    if side == "dec":
        blocks = np.diag(color_chart, k=x)
        x += 1

    if (curr_row % 2) == 0:
        blocks = np.flip(blocks)

    print(row_key, blocks)
    rows[row_key] = blocks
    curr_row += 1

print("processing diagonal rows complete.")