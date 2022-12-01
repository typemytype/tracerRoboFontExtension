# Tracer

This tool lets you autotrace the images assigned to glyphs.
It applies several simplification algorithms to reduce the
complexity of the traced outlines.

## Trace

- Threshold: The value to be used when converting the image
  to a black and white bitmap.
- Tolerance: The tracing accuracy tolerance. A higher number
  will result in less accuracy.
- Turd Size: Suppress speckles (aka turds) below this size.
- Blur: The amount to blur the image before converting
  to a black and white bitmap.

Tracer uses the (autotracing implementation in DrawBot)
[https://www.drawbot.com/content/shapes/bezierPath.html#drawBot.context.baseContext.BezierPath.traceImage].
DrawBot uses (Potrace)[https://potrace.sourceforge.net].
So for complete documentation on trace settings, refer to
these links.

## Simplify

- Segment Count: Contours with fewer segments than this
  number will be discarded.
- Small Curves: Curves shorter than this number will be
  converted to lines.
- Small Contours: Contours with an area smaller than this
  number will be discarded.
- Douglas Peucker: Apply the (Ramer–Douglas–Peucker)[https://en.wikipedia.org/wiki/Ramer–Douglas–Peucker_algorithm]
  algorithm.
- Visvalingam Whyatt: Apply the (Visvalingam Whyatt)[https://en.wikipedia.org/wiki/Visvalingam–Whyatt_algorithm]
  algorithm.
- Shallow Curves: Convert curves with a curve length
  that is similar to a line from the same on curve
  points to a line.
- Spikes: Remove those spiky points that autotracing
  is notorious for producing. Well, try to remove
  them at least.
- Remove Overlapping Points: Remove overlapping points.

If you don't want any simplification, set all of the values
to zero.

## Destination

- Layer: The name of the layer the trace should be
  stored in. If the given name doesn't exist, a new
  layer will be created.
- Trace Selected Glyphs: Trace the glyphs selected
  in the list.
- Trace All Glyphs: Trace all of the glyphs in the list.

## Preview

This gives you a preview of tracing with the input settings.
The button below will let you customize what you are seeing.

## Scripting

The internals of this extension are accessible via Python.
You can get the documentation for the various functions
and classes by getting the docstrings from these.

```
import tracer

tracer.traceGlyphImage
tracer.simplifyGlyphContours
tracer.countGlyphPoints
tracer.SimplifyContoursPen
tracer.CountPen
```

You can also look at the source code.