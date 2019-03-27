#!/usr/bin/python3

import argparse
import io
import math
from PyPDF2 import PdfFileWriter, PdfFileReader, pdf
from reportlab.pdfgen import canvas
import sys

formats = {
        "Letter":(612,792),
        "LetterSmall":(612,792),
        "Tabloid":(792,1224),
        "Ledger":(1224,792),
        "Legal":(612,1008),
        "Executive":(540,720),
        "A0":(2384,3371),
        "A1":(1685,2384),
        "A2":(1190,1684),
        "A3":(842,1190),
        "A4":(595,842),
        "A4Small":(595,842),
        "A5":(420,595),
        "B4":(729,1032),
        "B5":(516,729),
        "Folio":(612,936),
        "Quarto":(610,780),
        "10x14":(720,1008),
        }
min_border = 25

def create_parsers():
    p = argparse.ArgumentParser(
        prog='pdftile',
        description='Generate a grid of pages to print a given pdf',
    )

    p.add_argument(
        '-i', '--input',
        type=str,
        required=True,
        help='Input pdf',
    )

    p.add_argument(
        '-o', '--output',
        type=str,
        required=True,
        help='Output pdf',
    )

    p.add_argument(
        '-f', '--format',
        choices=sorted(formats.keys()),
        type=str,
        required=True,
        help='Output format',
    )

    p.add_argument(
        '-b', '--border',
        type=int,
        default=min_border,
        help='Border (in points) >= ' + str(min_border),
    )

    return p

if __name__ == '__main__':

    p = create_parsers()
    args = p.parse_args()

    input_filename = args.input
    output_filename = args.output
    border = args.border
    if args.border < min_border:
        print("minimum border is " + str(min_border))
        sys.exit(1)

    (formatX, formatY) = formats[args.format]

    input1 = PdfFileReader(input_filename)
    output = PdfFileWriter()

    numPages = input1.getNumPages()
    print("document has", numPages, "page(s)")
    print("generating", args.format,
          "(" + str(formatX) + "x" + str(formatY) + ")",
          "with borders of", border, "points")

    # iterate on all pages
    for pageNum in range(numPages):
        page = input1.getPage(pageNum)
        sizeX = page.mediaBox.getWidth()
        sizeY = page.mediaBox.getHeight()

        print("-----------------------------")
        print("page " + str(pageNum) + ":", str(sizeX) + "x" + str(sizeY))

        # check if landscape is more optimized
        numPagesXlandscape = math.ceil((sizeX + 2*border)/ formatY)
        numPagesYlandscape = math.ceil((sizeY + 2*border)/ formatX)
        total_landscape = numPagesXlandscape * numPagesYlandscape

        # don't forget border size
        numPagesX = math.ceil((sizeX + 2*border)/ formatX)
        numPagesY = math.ceil((sizeY + 2*border)/ formatY)
        total = numPagesX * numPagesY

        if total > total_landscape:
            print("Generating landscape tiles")
            numPagesX = numPagesXlandscape
            numPagesY = numPagesYlandscape
            total = total_landscape
            formatX, formatY = formatY, formatX

        print("X:", numPagesX, "pages")
        print("Y:", numPagesY, "pages")
        print("Total:", numPagesX * numPagesY, "pages")

        baseX = 0;
        for x in range(numPagesX):
            baseX -= 2*border
            baseY = 0
            for y in range(numPagesY):
                baseY -= 2*border
                endX = baseX + formatX
                endY = baseY + formatY
                print("page " + str(x) + "x" + str(y),
                      "from (" + str(baseX) + "," + str(baseY) + ")",
                      "to (" + str(endX) + "," + str(endY) + ")")

                # we need to duplicate each page to crop differently
                tmp = pdf.PageObject.createBlankPage(None, sizeX, sizeY)
                tmp.mergePage(page)
                tmp.mediaBox.lowerLeft = (baseX, baseY)
                tmp.mediaBox.upperRight = (endX, endY)

                # create a new PDF with Reportlab
                packet = io.BytesIO()
                can = canvas.Canvas(packet)

                # draw page number + scale
                #238pt = 84mm
                page_str = "page " + str(pageNum) +\
                           "/column " + str(x) +\
                           "/line " + str(y) +\
                           "/scale 238pt = 84mm"
                page_mark_offset = min_border/2
                page_markX = baseX + border + page_mark_offset
                page_markY = baseY + border - page_mark_offset
                # page mark
                can.drawString(page_markX, page_markY, page_str)
                # scale line X
                can.line(page_markX,
                         page_markY - 3,
                         page_markX + 238,
                         page_markY - 3)
                # scale line Y
                can.line(endX - border + page_mark_offset,
                         endY - border - page_mark_offset - 238 ,
                         endX - border + page_mark_offset,
                         endY - border - page_mark_offset)

                # draw corners
                leftX = baseX + border
                rightX = endX - border
                downY = baseY + border
                upY = endY - border
                corners = [(leftX, downY), # bottom left
                           (rightX, downY), # bottom right
                           (leftX, upY), # top left
                           (rightX, upY), # top right
                           ]

                for c in corners:
                    (i, j) = c
                    can.line(i - min_border, j, i + min_border, j)
                    can.line(i, j - min_border, i, j + min_border)

                # move to the beginning of the StringIO buffer
                can.save()
                packet.seek(0)
                tmp.mergePage(PdfFileReader(packet).getPage(0))
                output.addPage(tmp)

                baseY += formatY
            baseX += formatX;

    print('writing to output file ' + output_filename)
    out = open(output_filename, "wb")
    output.write(out)
    out.close()
