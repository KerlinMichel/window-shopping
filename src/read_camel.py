import sys
import datetime
import cv2
import numpy as np
#import heapq
import os
import math
from PIL import Image #, ImageEnhance, ImageFilter
import pytesseract
import csv
import re

def detect_month(ocrMonth):
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    if months.count(ocrMonth):
        return ocrMonth

    minDiff = math.inf
    for month in months:
        diff = 0
        for i in range(0, 3):
            diff += 0 if month[i] == ocrMonth[i] else 1
        if diff < minDiff:
            minDiff = diff
            ret = month

    return ret

def ocr(pic, rotation = 0, firstThreshold = 40, secondThreshold = 80, enhancement = 1.3, ratio = 4):
    if len(pic.shape) > 2:
        raise AttributeError('Grayscale picture only.')

    pic = cv2.resize(pic, (0, 0), fx = ratio, fy = ratio)
    # cv2.imshow('resize1', pic)
    pic = cv2.medianBlur(pic, 3)
    # cv2.imshow('blur1', pic)
    pic = cv2.threshold(pic, firstThreshold, 255, cv2.THRESH_TOZERO)[1]
    # cv2.imshow('threshold1', pic)
    pic = cv2.resize(pic, (0, 0), fx = ratio, fy = ratio)
    # cv2.imshow('resize2', pic)
    pic = cv2.medianBlur(pic, 3)
    # cv2.imshow('blur2', pic)
    pic = cv2.threshold(pic, secondThreshold, 255, cv2.THRESH_TOZERO)[1]
    # cv2.imshow('threshold2', gray)

    rows, cols = pic.shape
    # gray = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)[1]
    blank = np.zeros((rows, cols), np.uint8)
    blank[:] = int(255 / pic.max() * enhancement)
    pic = cv2.multiply(pic, blank)
    pic = cv2.medianBlur(pic, 3)
    # cv2.imshow('enhance', pic)

    if rotation != 0:
        rotate = cv2.getRotationMatrix2D((cols / 2, rows / 2), rotation, 1)
        pic = cv2.warpAffine(pic, rotate, (int(cols * (2 ** (1 / 2))), rows))
        # gray = cv2.warpAffine(startDate,gray,(int(cols * (2**(1/2))), int(rows * (2**(1/2)))), None, cv2.INTER_LINEAR, cv2.BORDER_CONSTANT, (255, 255, 255))
        # cv2.imshow('gray9', rotatedGray)
        # cv2.waitKey()

    ocrFile = 'ocr.jpg'
    cv2.imwrite(ocrFile, pic, [cv2.IMWRITE_JPEG_QUALITY, 100])
    text = pytesseract.image_to_string(Image.open(ocrFile)).upper()

    return text, pic

def ocrMonthDay(ocrText):
    ocrMonth = ''
    ocrDay = ''

    if len(ocrText) > 3:
        ocrMonth = ocrText[0:3]
        ocrDay = ocrText[3:len(ocrText)]
        ocrDay = ocrDay.strip("‘' ")

    return ocrMonth, ocrDay


#pytesseract.pytesseract.tesseract_cmd = 'C:/Program Files (x86)/Tesseract-OCR/tesseract'
pytesseract.pytesseract.tesseract_cmd = 'tesseract'
fileName = 'chart.png'
errorNum = 0

# print usage
print('Usage: python read_camel.py fileName *startDate_as_MM/DD/YYYY *lowestPrice *highestPrice')
print('!Stared Arguments can be parsed from graph.')
print('!!pytesseract path must be set before running.')
print('!!!parsed results saved as csv in same directory.')

# parse inputs
if len(sys.argv) > 1:
    fileName = sys.argv[1]
    if len(sys.argv) > 2:
        startDate = datetime.datetime.strptime(sys.argv[2], '%m/%d/%Y')
        if len(sys.argv) > 3:
            lowerPrice = float(sys.argv[3])
            if len(sys.argv) > 4:
                highestPrice = float(sys.argv[4])


src = cv2.imread(fileName)
cv2.imshow('src', src)

# ----- extract bgr and black layers -----
# split into bgr channels
b = src[:,:,0]
g = src[:,:,1]
r = src[:,:,2]

# detect bgr dominated parts
blueLayer = cv2.multiply(cv2.subtract(b, g), cv2.subtract(b, r))#, None, 255)
#cv2.imshow('blue', blueLayer)
greenLayer = cv2.multiply(cv2.subtract(g, b), cv2.subtract(g, r))#, None, 255)
#cv2.imshow('green', greenLayer)
redLayer = cv2.multiply(cv2.subtract(r, b), cv2.subtract(r, g))#, None, 255)
#cv2.imshow('red', redLayer)

bgrLayer = cv2.add(blueLayer, greenLayer)
bgrLayer = cv2.add(bgrLayer, redLayer)
#cv2.imshow('bgr', bgrLayer)
cv2.imwrite('bgr.png', bgrLayer)

blackLayer = cv2.add(cv2.absdiff(b,g), cv2.absdiff(b,r))
#blackLayer = cv2.add(blackLayer, cv2.absdiff(g,r))
blackLayer = cv2.threshold(blackLayer, 0, 255, cv2.THRESH_BINARY_INV)[1]
#cv2.imshow('black', blackLayer)
cv2.imwrite('black.png',blackLayer)

# detect line segments
linesP = cv2.HoughLinesP(blackLayer, 3, np.pi / 180, 50, None, 50, 10)
cdstP  = cv2.cvtColor(blackLayer, cv2.COLOR_GRAY2BGR)

# ----- detect left and right boundaries -----
hLines = []
left = math.inf
if linesP is not None:
    for i in range(0, len(linesP)):
        l = linesP[i][0]
        cv2.line(cdstP, (l[0], l[1]), (l[2], l[3]), (0, 0, 255), 1, cv2.LINE_AA)
        if l[0] == l[2]:
            if hLines.count(l[0]) == 0:
                hLines.append(l[0])
            if l[0] < left:
                left = l[0]
                leftLine = l


if leftLine[1] > leftLine[3]:
    swap = leftLine[1]
    leftLine[1] = leftLine[3]
    leftLine[3] = swap

bottom = 0
if linesP is not None:
    for i in range(0, len(linesP)):
        l = linesP[i][0]
        #cv2.line(cdstP, (l[0], l[1]), (l[2], l[3]), (0, 0, 255), 1, cv2.LINE_AA)
        if l[1] == l[3] and l[1] >= leftLine[1] and l[1] <= leftLine[3]:
            if l[1] > bottom:
                bottom = l[1]
                bottomLine = l

top = leftLine[1]
right = bottomLine[2] if bottomLine[2] >= bottomLine[0] else bottomLine[0]
hLines.append(right)

#cv2.imshow('detected black', cdstP)
#l = leftLine
#cv2.line(cdstP, (l[0], l[1]), (l[2], l[3]), (0, 0, 255), 1, cv2.LINE_AA)
#l = bottomLine
#cv2.line(cdstP, (l[0], l[1]), (l[2], l[3]), (0, 0, 255), 1, cv2.LINE_AA)
cv2.imshow('detect black', cdstP)
#cv2.waitKey()

# ----- parse amazon id -----
idPic = src[16 : 32, 378 : 673]
idPic = cv2.cvtColor(idPic, cv2.COLOR_BGR2GRAY)
cv2.imshow('idPic', idPic)
rows, cols = idPic.shape
blank = np.zeros((rows, cols), np.uint8)
blank[ : ] = 255
datePic = blank - idPic
#cv2.imshow('idPic2', idPic)
blank[ : ] = int(255 / idPic.max())
datePic = cv2.multiply(idPic, blank)
#cv2.imshow('gray3', datePic)
ocrText, ocrPic = ocr(idPic)
idText = ocrText.replace(' ', '').split('/')[-1]
print(idText)

# ----- parse dates on x-axis -----
hLines.sort()
hLines.reverse()
hDates = []
removeLines = []
for i in range(len(hLines)):
    if i == 0:
        currentDate = datetime.datetime.fromtimestamp(os.stat(fileName).st_ctime)
        currentYear = currentDate.year
    else:
        x = hLines[i]
        datePic = src[bottom + 6 : bottom + 38, x - 30 : x + 5]
        datePic = cv2.cvtColor(datePic, cv2.COLOR_BGR2GRAY)
        #cv2.imshow('gray1', datePic)
        rows, cols = datePic.shape
        blank = np.zeros((rows, cols), np.uint8)
        blank[ : ] = 255
        datePic = blank - datePic
        #cv2.imshow('gray2', datePic)
        blank[ : ] = int(255 / datePic.max())
        datePic = cv2.multiply(datePic, blank)
        #cv2.imshow('gray3', datePic)

        ocrText, ocrPic = ocr(datePic, -45)
        ocrMonth, ocrDay = ocrMonthDay(ocrText)
        if ocrMonth == '' or ocrDay == '':
            errorNum += 1
            cv2.imwrite('error' + str(errorNum) + '.jpg', ocrPic)
            ocrText, ocrPic = ocr(datePic, -45, 45, 85)
            ocrMonth, ocrDay = ocrMonthDay(ocrText)
            if ocrMonth == '' or ocrDay == '':
                errorNum += 1
                cv2.imwrite('error' + str(errorNum) + '.jpg', ocrPic)
                ocrText, ocrPic = ocr(datePic, -45, 40, 80, 1.5, 2)
                ocrMonth, ocrDay = ocrMonthDay(ocrText)
                if ocrMonth == '' or ocrDay == '':
                    errorNum += 1
                    cv2.imwrite('error' + str(errorNum) + '.jpg', ocrPic)
                    print('ocr error: error' + str(errorNum) + '.jpg: ')
                    removeLines.append(x)
                    continue

        # analyze month and day
        ocrMonth = ocrMonth.replace('€', 'E')
        ocrMonth = ocrMonth.replace('5', 'S')
        ocrMonth = ocrMonth.replace('$', 'S')
        ocrMonth = ocrMonth.replace('|', 'L')
        ocrMonth = ocrMonth.replace('0', 'O')
        ocrMonth = detect_month(ocrMonth)
        #print(ocrMonth)

        ocrDay = ocrDay.replace('?', '7')
        ocrDay = ocrDay.replace('N', '11')
        ocrDay = ocrDay.replace('Z', '2')
        ocrDay = ocrDay.replace('S', '5')
        ocrDay = ocrDay.replace('I', '1')
        ocrDay = ocrDay.replace('T', '7')
        #print(str(currentYear) + ' ' + ocrMonth + ' ' + ocrDay)
        print(str(currentYear) + ' ' + ocrMonth + ' ' + ocrDay)
        currentDate = datetime.datetime.strptime(str(currentYear) + ' ' + ocrMonth + ' ' + ocrDay, '%Y %b %d')
        if currentDate > previousDate:
            currentYear = currentYear - 1
            currentDate = datetime.datetime.strptime(str(currentYear) + ' ' + ocrMonth + ' ' + ocrDay, '%Y %b %d')
        print(currentDate.date())

    hDates.append(currentDate)
    previousDate = currentDate

for line in removeLines:
    hLines.remove(line)

# ----- parse prices -----
pricePic = bgrLayer[0 : bgrLayer.shape[0], right + 1 : bgrLayer.shape[1]]
ocrText, ocrPic = ocr(pricePic)
prices = ocrText.replace(' ', '').split()
upperPrice = prices[0][1 : len(prices[0]) - 1]
lowerPrice = prices[-1][1 : len(prices[-1]) - 1]
upperPrice = re.findall("([0-9.]*[0-9]+)", upperPrice)[0]
lowerPrice = re.findall("([0-9.]*[0-9]+)", lowerPrice)[0]
upperPrice = float(upperPrice)
lowerPrice = float(lowerPrice)
#upperPrice = float(prices[0].strip('$'))
#lowerPrice = float(prices[-1].strip('$'))
print(prices[0] + ', ' + prices[-1])

# ----- parse price line -----
cdstP  = cv2.cvtColor(bgrLayer, cv2.COLOR_GRAY2BGR)
linesP = cv2.HoughLinesP(bgrLayer, 1, np.pi / 180, 50, None, 250, 5)
upper = math.inf
lower = 0
if linesP is not None:
    for i in range(0, len(linesP)):
        l = linesP[i][0]
        #cv2.line(cdstP, (l[0], l[1]), (l[2], l[3]), (0, 0, 255), 1, cv2.LINE_AA)
        if l[1] == l[3]:
            if l[1] < upper:
                upper = l[1]
                upperLine = l
            if l[1] > lower:
                lower = l[1]
                lowerLine = l

l = upperLine
cv2.line(cdstP, (l[0], l[1]), (l[2], l[3]), (0, 0, 255), 1, cv2.LINE_AA)
l = lowerLine
cv2.line(cdstP, (l[0], l[1]), (l[2], l[3]), (0, 0, 255), 1, cv2.LINE_AA)
#cv2.imshow('detected Bgr', cdstP)
#cv2.waitKey()

datePrices = []
hLines.reverse()
hDates.reverse()
assert(len(hDates) == len(hLines))
previousY = lower
l2hFlag = False
for i in range(len(hLines) - 1):
    previousDate = hDates[i]
    nextDate = hDates[i+1]
    step = (hLines[i+1] - hLines[i]) / (nextDate - previousDate).days

    days = (nextDate - previousDate).days
    if i == len(hLines) - 1:
        days += 1
    for x in range(0, days):
        y = lower - 1
        #print(x)
        while y > upper:
            #print(y)
            pixel = bgrLayer[y][int(hLines[i] + x * step)]
            if l2hFlag == False and pixel >= 1:
                if previousY < y:
                    break
                elif previousY >= y:
                    l2hFlag = True
            elif l2hFlag == True and pixel < 1:
                y = y - 1
                break
            y -= 1

        if l2hFlag == False and y <= upper:
            y = previousY
        cv2.circle(cdstP, (int(hLines[i] + x * step), y), 1, (0, 255, 0))
        thisDate = previousDate + datetime.timedelta(days = x)
        thisPrice = lowerPrice + (lower - y - 1) * (upperPrice - lowerPrice) / (lower - 1 - upper)
        #print(str(x) + ', ' + str(y) + ', ' + str(previousY) + ', ' + str(thisDate) + ', $' + str(thisPrice))
        datePrices.append([thisDate, thisPrice])

        previousY = y
        l2hFlag = False

myFile = open(fileName[0:fileName.rfind('.')] + '.csv', 'w')
with myFile:
   writer = csv.writer(myFile, lineterminator='\n')
   writer.writerows(datePrices)
cv2.imshow('detected bgr', cdstP)
cv2.imwrite('detected bgr.jpg', cdstP)
#cv2.waitKey()
