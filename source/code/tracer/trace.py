import pathlib
import tempfile
import AppKit
import drawBot as bot

def traceGlyphImage(
        glyphWithImage,
        destinationGlyph=None,
        threshold=0,
        blur=0,
        invert=False,
        turdSize=0,
        tolerance=0
    ):
    if destinationGlyph is None:
        destinationGlyph = glyphWithImage
    imageData = glyphWithImage.image.data
    if not imageData:
        return
    data = AppKit.NSData.dataWithBytes_length_(imageData, len(imageData))
    image = AppKit.NSImage.alloc().initWithData_(data)
    image = bot.ImageObject(image)
    tracer = bot.BezierPath()
    tracer.traceImage(
        image,
        threshold=threshold,
        blur=blur,
        invert=invert,
        turd=turdSize,
        tolerance=tolerance
    )
    pointPen = destinationGlyph.getPointPen()
    tracer.drawToPointPen(pointPen)