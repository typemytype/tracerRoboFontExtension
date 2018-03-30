from AppKit import *
import tempfile
import os

from xml.dom import minidom
from fontTools.misc.transform import Transform

from vanilla import *
from defconAppKit.windows.baseWindow import BaseWindowController

try:
    from mojo.canvas import CanvasGroup
except:
    from mojo.canvas import Canvas

    class CanvasGroup(Canvas):

        def width(self):
            return self.getNSView().frame().size.width

        def height(self):
            return self.getNSView().frame().size.height

from mojo.drawingTools import *

from mojo.roboFont import OpenWindow, CurrentGlyph
from mojo.compile import executeCommand

potrace = os.path.join(os.path.dirname(__file__), "potrace")
mkbitmap = os.path.join(os.path.dirname(__file__), "mkbitmap")

os.chmod(potrace, 0o0755)
os.chmod(mkbitmap, 0o0755)


def _getPath(element, path=None, pathItems=None):
    if pathItems is None:
        pathItems = list()

    children = [child for child in element.childNodes if child.nodeType == 1]
    for child in children:
        if child.tagName == "g":
            # group
            path = dict(coordinates=[])
            pathItems.append(path)
            for name, value in child.attributes.items():
                if name == "transform":
                    t = Transform()
                    for trans in value.split(" "):
                        key, v = trans.split("(")
                        if key.lower() != "scale":
                            continue
                        if ")" in v:
                            v = v.replace(")", "")
                        x, y = v.split(",")
                        x = float(x)
                        y = float(y)
                        y = x
                        t = getattr(t, key)(x, y)
                    path["transform"] = t
            _getPath(child, path, pathItems)
        elif child.tagName == "path":
            # path
            if path is None:
                path = dict(coordinates=[])
                pathItems.append(path)
            for name, value in child.attributes.items():
                path["coordinates"].append(value.split(" "))
        else:
            continue
    return pathItems


class BaseSegment(object):

    def __init__(self):
        self._points = []

    def addPoint(self, p):
        self._points.append(p)

    def bezier(self, pen):
        pass


class AbsMoveTo(BaseSegment):

    def bezier(self, pen):
        for p in self._points:
            pen._moveTo(p)


class RelMoveTo(BaseSegment):

    def bezier(self, pen):
        for p in self._points:
            pen._relMoveTo(p)


class AbsLineTo(BaseSegment):

    def bezier(self, pen):
        for p in self._points:
            pen._lineTo(p)


class RelLineTo(BaseSegment):

    def bezier(self, pen):
        for p in self._points:
            pen._relLineTo(p)


class AbsCurveTo(BaseSegment):

    def bezier(self, pen):
        for i in range(2, len(self._points), 3):
            h1 = self._points[i - 2]
            h2 = self._points[i - 1]
            p = self._points[i]
            pen._curveTo(h1, h2, p)


class RelCurveTo(BaseSegment):

    def bezier(self, pen):
        for i in range(2, len(self._points), 3):
            h1 = self._points[i - 2]
            h2 = self._points[i - 1]
            p = self._points[i]
            pen._relCurveTo(h1, h2, p)


class RelClosePath(BaseSegment):

    def bezier(self, pen):
        pen._closePath()


class AbsClosePath(BaseSegment):

    def bezier(self, pen):
        pen._closePath()


class RelativePen:

    def __init__(self, outPen, transform):
        self.outPen = outPen
        self.transform = transform
        self.currentPoint = (0, 0)

    def _moveTo(self, p):
        self.currentPoint = p
        if self.transform:
            p = self.transform.transformPoint(p)
        self.outPen.moveTo(p)

    def _relMoveTo(self, p):
        x, y = p
        cx, cy = self.currentPoint
        self._moveTo((cx + x, cy + y))

    def _lineTo(self, p):
        self.currentPoint = p
        if self.transform:
            p = self.transform.transformPoint(p)
        self.outPen.lineTo(p)

    def _relLineTo(self, p):
        x, y = p
        cx, cy = self.currentPoint
        self._lineTo((cx + x, cy + y))

    def _curveTo(self, h1, h2, p):
        self.currentPoint = p
        if self.transform:
            h1 = self.transform.transformPoint(h1)
            h2 = self.transform.transformPoint(h2)
            p = self.transform.transformPoint(p)
        self.outPen.curveTo(h1, h2, p)

    def _relCurveTo(self, h1, h2, p):
        x1, y1 = h1
        x2, y2 = h2
        x, y = p
        cx, cy = self.currentPoint
        self._curveTo((cx + x1, cy + y1), (cx + x2, cy + y2), (cx + x, cy + y))

    def _closePath(self):
        self.outPen.closePath()


instructions = dict(
    m=RelMoveTo,
    M=AbsMoveTo,
    l=RelLineTo,
    L=AbsLineTo,
    c=RelCurveTo,
    C=AbsCurveTo,
    z=RelClosePath,
    Z=AbsClosePath
)


class Paths:

    def __init__(self):
        self._currentInstruction = None
        self._segments = list()

    def setInstruction(self, instruction):
        if instruction is None:
            return
        instruction = instructions[instruction]

        self._currentInstruction = instruction()
        self._segments.append(self._currentInstruction)

    def addPoint(self, x, y):
        self._currentInstruction.addPoint((x, y))

    def beziers(self, outPen, transfrom=None):
        pen = RelativePen(outPen, transfrom)
        for seg in self._segments:
            seg.bezier(pen)


def importSVGWithPen(svgPath, outPen, box=None):
    svgDoc = minidom.parse(svgPath)
    svgParent = svgDoc.documentElement

    translate = (0, 0)
    scaleX = scaleY = 1
    if box is not None:
        (x, y, w, h) = box
        translate = (x, y)

        docWidth = float(svgParent.attributes["width"].value[:-2])
        docHeight = float(svgParent.attributes["height"].value[:-2])

        scaleX = w / docWidth
        scaleY = h / docHeight

    svgPaths = _getPath(svgParent)
    for path in svgPaths:
        paths = Paths()
        transform = path.get("transform").reverseTransform(Transform().translate(*translate).scale(scaleX, scaleY))

        allCoordinates = path.get("coordinates")
        for coordinates in allCoordinates:
            for i in range(1, len(coordinates), 2):
                x = coordinates[i - 1]
                y = coordinates[i]

                instruction = None
                closePath = False
                if x[0] in instructions:
                    instruction = x[0]
                    x = x[1:]
                if y[-1] in instructions:
                    closePath = True
                    y = y[:-1]
                x = float(x)
                y = float(y)

                paths.setInstruction(instruction)
                paths.addPoint(x, y)

                if closePath:
                    closePath = False
                    paths.setInstruction("z")

        paths.beziers(outPen, transform)


def saveImageAsBitmap(image, bitmapPath):
    # http://stackoverflow.com/questions/23258596/how-to-save-png-file-from-nsimage-retina-issues-the-right-way
    x, y, maxx, maxy = image.bounds
    width = maxx - x
    height = maxy - y

    bitmap = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bitmapFormat_bytesPerRow_bitsPerPixel_(
        None,  # data planes
        int(width),  # pixels wide
        int(height),  # pixels high
        8,  # bits per sample
        4,  # samples per pixel
        True,  # has alpha
        False,  # is planar
        NSDeviceRGBColorSpace,  # color space
        0,  # bitmap format
        0,  # bytes per row
        0   # bits per pixel
    )

    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(NSGraphicsContext.graphicsContextWithBitmapImageRep_(bitmap))
    NSGraphicsContext.currentContext().setShouldAntialias_(True)

    NSColor.whiteColor().set()
    NSRectFill(((0, 0), (width, height)))

    imageData = image.naked().getRepresentation("doodle.CIImageFiltered")
    if imageData:
        ciImage, imageRect = imageData
        ciImage.drawAtPoint_fromRect_operation_fraction_((0, 0), imageRect, NSCompositeSourceOver, 1)
        
    NSGraphicsContext.restoreGraphicsState()

    data = bitmap.representationUsingType_properties_(NSBMPFileType, {NSImageCompressionFactor: 1})
    data.writeToFile_atomically_(bitmapPath, True)


def traceImage(glyph, destGlyph=None, threshold=.2, blur=None, invert=False, turdsize=2, opttolerance=0.2, neededForPreview=False):
    if destGlyph is None:
        destGlyph = glyph
    if glyph is None:
        return
    image = glyph.image
    if image is None:
        return
    x, y, maxx, maxy = image.bounds
    w = maxx - x
    h = maxy - y

    imagePath = tempfile.mktemp(".bmp")
    bitmapPath = tempfile.mktemp(".pgm")
    svgPath = tempfile.mktemp(".svg")

    saveImageAsBitmap(image, imagePath)

    cmds = [mkbitmap, "-x", "-t", str(threshold)]
    if blur:
        cmds.extend(["-b", str(blur)])
    if invert:
        cmds.extend(["-i"])
    cmds.extend([
        # "-g",
        # "-1",
        "-o",
        bitmapPath,
        imagePath
    ])
    log = executeCommand(cmds, shell=True)
    if log != ('', ''):
        print(log)

    cmds = [potrace, "-s"]
    cmds.extend(["-t", str(turdsize)])
    cmds.extend(["-O", str(opttolerance)])
    cmds.extend(["-o", svgPath, bitmapPath])

    log = executeCommand(cmds, shell=False)
    if log != ('', ''):
        print(log)

    glyph.prepareUndo("Tracing")
    importSVGWithPen(svgPath, destGlyph.getPen(), (x, y, w, h))
    glyph.performUndo()

    os.remove(imagePath)
    os.remove(svgPath)

    if not neededForPreview:
        os.remove(bitmapPath)
    else:
        return bitmapPath


class TraceWindow(BaseWindowController):

    def __init__(self):
        self.w = FloatingWindow((400, 450), "Tracer", minSize=(400, 400))

        middle = 130
        gap = 15
        y = 10
        self.w.thresholdText = TextBox((10, y + 1, middle, 22), "Threshold:", alignment="right")
        self.w.threshold = Slider((middle + gap, y, -10, 22), minValue=0, maxValue=1, value=.2, continuous=False, callback=self.makePreview)

        y += 30
        self.w.blurText = TextBox((10, y + 1, middle, 22), "Blur:", alignment="right")
        self.w.blur = Slider((middle + gap, y, -10, 22), minValue=0, maxValue=30, value=0, continuous=False, callback=self.makePreview)
        y += 30
        self.w.invert = CheckBox((middle + gap, y + 2, -10, 22), "Invert", callback=self.makePreview)
        y += 30
        self.w.turdsizeText = TextBox((10, y + 1, middle, 22), "Suppress Speckles:", alignment="right")
        self.w.turdsize = Slider((middle + gap, y, -10, 22), minValue=0, maxValue=30, value=2, continuous=False, callback=self.makePreview)
        y += 30
        self.w.opttoleranceText = TextBox((10, y + 1, middle, 22), "Tolerance:", alignment="right")
        self.w.opttolerance = Slider((middle + gap, y, -10, 22), minValue=0, maxValue=2, value=0.2, continuous=False, callback=self.makePreview)

        y += 25
        _y = -40
        self.w.preview = CanvasGroup((0, y, -0, _y), delegate=self)
        self._previewImage = None
        self._previewGlyph = None

        _y = -30
        self.w.trace = Button((-100, _y, -10, 22), "Trace", callback=self.trace)
        self.w.traceFont = Button((-210, _y, -110, 22), "Trace Font", callback=self.traceFont)
        self.w.update = Button((-300, _y, -220, 22), "Update", callback=self.makePreview)
        self.w.showPreview = CheckBox((10, _y, 100, 22), "Preview", value=True, callback=self.makePreview)

        self.w.setDefaultButton(self.w.trace)
        self.makePreview()
        self.w.open()

    def makePreview(self, sender=None):
        if not self.w.showPreview.get():
            self._previewImage = None
            self._previewGlyph = None
        else:
            glyph = CurrentGlyph()
            dest = RGlyph()
            bitmapPath = traceImage(
                glyph,
                dest,
                threshold=self.w.threshold.get(),
                blur=self.w.blur.get(),
                invert=self.w.invert.get(),
                turdsize=self.w.turdsize.get(),
                opttolerance=self.w.opttolerance.get(),
                neededForPreview=True
            )
            if bitmapPath:
                im = NSImage.alloc().initWithContentsOfFile_(bitmapPath)
                x, y, maxx, maxy = glyph.image.bounds
                dest.move((-x, -y))
                self._previewImage = im
                self._previewGlyph = dest
        self.w.preview.update()

    def draw(self):
        b = 10
        translate(b * .5, b * .5)
        w = self.w.preview.width() - b
        h = self.w.preview.height() - b

        if self._previewImage and self._previewGlyph:
            iw, ih = self._previewImage.size()

            ws = w / iw
            hs = h / ih

            s = ws
            if ws > hs:
                s = hs

            scale(s)
            shiftX = (w / s - iw) * .5
            shiftY = (h / s - ih) * .5
            translate(shiftX, shiftY)

            fill(1, 0, 0, .3)
            stroke(1, 0, 0)
            strokeWidth(1 / s)
            drawGlyph(self._previewGlyph)

            path = NSBezierPath.bezierPath()
            dotSize = 3 / s
            fill(1, 0, 0)
            stroke(None)
            for contour in self._previewGlyph:
                for point in contour.points:
                    if point.type != "offCurve":
                        path.appendBezierPathWithOvalInRect_(NSMakeRect(point.x - dotSize, point.y - dotSize, dotSize * 2, dotSize * 2))
            drawPath(path)

    def _trace(self, glyph):
        traceImage(glyph,
                   threshold=self.w.threshold.get(),
                   blur=self.w.blur.get(),
                   invert=self.w.invert.get(),
                   turdsize=self.w.turdsize.get(),
                   opttolerance=self.w.opttolerance.get()
                   )

    def trace(self, sender):
        self._trace(CurrentGlyph())

    def traceFont(self, sender):
        font = CurrentFont()
        progress = self.startProgress("Tracing...", tickCount=len(font))
        for glyph in CurrentFont():
            progress.update()
            self._trace(glyph)
        progress.close()


OpenWindow(TraceWindow)
