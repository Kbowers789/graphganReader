import sys
import cv2
import imutils
import numpy as np

target_colors = {}
crop_coords = []
click_count = 0


def crop_click(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        crop_coords.append([y, x])


def find_color(roi):
    global click_count
    # checking that we have not exceeded the specified number of colors
    if click_count <= len(target_colors):
        print("click count:", click_count)
        key = "color" + str(click_count)
        block_mean = cv2.mean(roi)
        print("block_mean =", block_mean)
        mean_hue = round(block_mean[0])
        mean_sat = round(block_mean[1])
        mean_val = round(block_mean[2])
        print("Mean Values:" + str(mean_hue) + "," + str(mean_sat) + "," + str(mean_val))
        target_colors[key] = [mean_hue, mean_sat, mean_val]


# stitchfiddle_image.png
# c2c_dog.jpg
# c2c_paw.jpg
# c2c_owl.jpg
src = "c2c_dog.jpg"
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

# smoothing cropped image before asking for user input to capture all colors needed in chart
blurred = cv2.bilateralFilter(cropped, 10, 50, 50)

# creating a copy with hsv colors for masking purposes
hsv_copy = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

cv2.imshow("Blurred", blurred)

print("How many colors are in this chart?")
color_count = int(input())
for i in range(0,color_count):
    key_name = "color"+ str(i+1)
    target_colors[key_name] = []

# grabbing each color from the blurred image
print("Select on one block for each individual color. Hit Enter once a block is selected.")
while click_count < color_count:
    click_count += 1
    new_color = cv2.selectROI("Blurred", blurred, fromCenter=False,showCrosshair=False)
    color_crop = hsv_copy[int(new_color[1]):int(new_color[1] + new_color[3]),
                 int(new_color[0]):int(new_color[0] + new_color[2])]
    find_color(color_crop)

cv2.waitKey(0)
print(target_colors)

rows, columns, channels = blurred.shape
for color in target_colors:
    for i in range(0, rows):
        for j in range(0, columns):
            old_h = hsv_copy[i, j][0]
            old_s = hsv_copy[i, j][1]
            old_v = hsv_copy[i, j][2]

            if target_colors[color][0] - 5 <= old_h <= target_colors[color][0] + 5:
                new_h = 0
                new_s = 0
                new_v = 35
                blurred[i, j] = [new_h, new_s, new_v]

cv2.imshow("recolored", blurred)
cv2.waitKey(0)

# converting blurred & recolored image to grayscale, then performing a threshold in prep for finding contours
gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
thresh = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY_INV)[1]
cv2.imshow("thresh", thresh)
cv2.waitKey(0)

# finding contours in the threshold image
cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cnts = imutils.grab_contours(cnts)
color_list = []

# loop over the contours to find center pixel of each (presumed) block in grid
for c in cnts:
    # compute the center of the contour
    M = cv2.moments(c)
    if M["m10"] == 0 or M["m00"] == 0 or M["m01"] == 0:
        continue

    cX = int(M["m10"] / M["m00"]) + crop_coords[0][1]
    cY = int(M["m01"] / M["m00"]) + crop_coords[0][0]

    # determining which color the contour is based on the original image colors that were stored
    for color in target_colors:
        if target_colors[color][0]-5 <= im[cY, cX][2] <= target_colors[color][0]+5:
            color_list.append(color)
            print(cY, cX, im[cY, cX], color)
        else:
            print(im[cY, cX])

    # draw the center of the shape on the image
    cv2.circle(im, (cX, cY), 1, (0, 255, 0), -1)
    cv2.imshow("Final", im)
    cv2.waitKey(5)

# print(color_list)
color_chart = np.array(color_list)
print("expected number of blocks:", chart_y*chart_x)
print("array shape:", color_chart.shape)
if color_chart.shape[0] < chart_y*chart_x:
    missing = chart_y*chart_x - color_chart.shape[0]
    for i in range(0, missing):
        color_chart = np.append(color_chart, "XXX")
if color_chart.shape[0] > chart_y*chart_x:
    print("error in image processing - missing blocks: program terminating")
    sys.exit()
print("image processed fully")
color_chart = np.reshape(color_chart, (chart_y, chart_x))
print("new array shape:", color_chart.shape)
# row_count = chart_y + chart_x - math.gcd(chart_y, chart_x)
# print("Number of rows = ", row_count)
color_chart = np.flipud(color_chart)

rows = {}
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