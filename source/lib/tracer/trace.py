import pathlib
import tempfile
from fontTools.misc import transform
from fontTools.pens.transformPen import TransformPointPen
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
    rep = AppKit.NSBitmapImageRep.imageRepWithData_(data)
    pixelWidth = rep.pixelsWide()
    imageWidth, imageHeight = image.size()
    imageScale = pixelWidth / imageWidth
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
    imageTransform = transform.Scale(imageScale)
    outPointPen = destinationGlyph.getPointPen()
    transformPointPen = TransformPointPen(outPointPen, imageTransform)
    tracer.drawToPointPen(transformPointPen)