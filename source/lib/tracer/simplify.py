import pprint
import math
from fontTools.misc.bezierTools import approximateCubicArcLength, calcCubicArcLength
from fontTools.pens.basePen import AbstractPen
from fontTools.pens.filterPen import ContourFilterPen
from fontTools.pens.recordingPen import RecordingPen, replayRecording
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.roundingPen import RoundingPen
from simplification.cutil import simplify_coords as applyDouglasPeucker
from simplification.cutil import simplify_coords_vw as applyVisvalingamWhyatt
from simplification.cutil import simplify_coords_vwp as applyVisvalingamWhyattPlus

defaultMinimumCurveLength = 20
defaultDouglasPeuckerTolerance = 1.0
defaultVisvalingamWhyattTolerance = 1.0
defaultShallowCurveTolerance = 0.2
defaultMinimumContourSegments = 4
defaultMinimumContourArea = 500
defaultSpikeTolerance = 10

# ------------------
# Public Convenience
# ------------------

def simplifyGlyphContours(
        glyph,
        destinationGlyph=None,
        removeOverlappingPoints=True,
        roundToIntegers=True,
        minimumContourSegments=defaultMinimumContourSegments,
        minimumContourArea=defaultMinimumContourArea,
        minimumCurveLength=defaultMinimumCurveLength,
        douglasPeuckerTolerance=defaultDouglasPeuckerTolerance,
        visvalingamWhyattTolerance=defaultVisvalingamWhyattTolerance,
        shallowCurveTolerance=defaultShallowCurveTolerance,
        spikeTolerance=defaultSpikeTolerance
    ):
    sourceGlyph = glyph
    if destinationGlyph is None:
        sourceGlyph = sourceGlyph.copy()
        destinationGlyph = glyph
        glyph.clearContours()
    simplifyPen = SimplifyContoursPen(
        destinationGlyph.getPen(),
        removeOverlappingPoints=removeOverlappingPoints,
        roundToIntegers=roundToIntegers,
        minimumContourSegments=minimumContourSegments,
        minimumContourArea=minimumContourArea,
        minimumCurveLength=minimumCurveLength,
        douglasPeuckerTolerance=douglasPeuckerTolerance,
        visvalingamWhyattTolerance=visvalingamWhyattTolerance,
        shallowCurveTolerance=shallowCurveTolerance,
        spikeTolerance=spikeTolerance
    )
    sourceGlyph.draw(simplifyPen)

def countGlyphPoints(glyph):
    pen = CountPen()
    glyph.draw(pen)
    return pen.pointCount

# --------
# Simplify
# --------

def noArgs(**kwargs):
    d = dict(
        minimumCurveLength=None,
        douglasPeuckerTolerance=None,
        visvalingamWhyattTolerance=None,
        shallowCurveTolerance=None,
        minimumContourSegments=None,
        removeOverlappingPoints=False,
        minimumContourArea=None,
        roundToIntegers=False,
        spikeTolerance=0
    )
    d.update(kwargs)
    return d


class SimplifyContoursPen(ContourFilterPen):

    """
    Options:

    - removeOverlappingPoints: bool
      Remove overlapping points in sequence.
    - roundToInteger: bool
      Round values to integers.
    - minimumContourSegments: value
      Remove contours with < N segments.
    - minimumContourArea: value
      Remove countours with an area below a minimum.
    - minimumCurveLength: value
      Convert small curves to lines
    - douglasPeuckerTolerance: value
      Use DP simplification on sequential line segments.
    - visvalingamWhyattTolerance: value
      Use VW simplification on sequential line segments.
    - shallowCurveTolerance: value
      Convert shallow curves to lines.
    - spikeTolerance: value
      Remove single point spikes.


    To Do:
    - filterSpikes test
    - convert curves with meaningless off curves to lines?
      (not sure if these are even happening)
    - algorithm to remove short line segments?
    - build SimplifyContoursDataPen to give the user
      some clues about where optimization can be
      most effective.
    - look into bezier merging
    """

    def __init__(self,
            outPen,
            removeOverlappingPoints=True,
            roundToIntegers=True,
            minimumContourSegments=defaultMinimumContourSegments,
            minimumContourArea=defaultMinimumContourArea,
            minimumCurveLength=defaultMinimumCurveLength,
            douglasPeuckerTolerance=defaultDouglasPeuckerTolerance,
            visvalingamWhyattTolerance=defaultVisvalingamWhyattTolerance,
            shallowCurveTolerance=defaultShallowCurveTolerance,
            spikeTolerance=defaultSpikeTolerance,
        ):
        super().__init__(outPen)
        self.minimumCurveLength = minimumCurveLength
        self.douglasPeuckerTolerance = douglasPeuckerTolerance
        self.visvalingamWhyattTolerance = visvalingamWhyattTolerance
        self.shallowCurveTolerance = shallowCurveTolerance
        self.minimumContourSegments = minimumContourSegments
        self.removeOverlappingPoints = removeOverlappingPoints
        self.minimumContourArea = minimumContourArea
        self.roundToIntegers = roundToIntegers
        self.spikeTolerance = spikeTolerance

    def filterContour(self, contour):
        filtered = list(contour)
        while filtered:
            # Note: some filters are applied more than once.
            # The first pass is done to simplify the data before
            # expensive processing to eliminate obvious data.
            # The second pass eliminates any of the conditions
            # created through other filtering.
            if self.removeOverlappingPoints:
                filtered = filterOverlappingPoints(filtered)
            if self.spikeTolerance:
                filtered = filterSpikes(filtered, self.spikeTolerance)
            if self.minimumContourSegments:
                filtered = filterContourSegmentCounts(filtered, self.minimumContourSegments)
            if self.minimumContourArea:
                filtered = filterContourAreas(filtered, self.minimumContourArea)

            if self.minimumCurveLength:
                filtered = filterCurveLengths(filtered, self.minimumCurveLength)
            if self.shallowCurveTolerance:
                filtered = filterShallowCurves(filtered, self.shallowCurveTolerance)
            if self.douglasPeuckerTolerance:
                filtered = filterDouglasPeucker(filtered, self.douglasPeuckerTolerance)
            if self.visvalingamWhyattTolerance:
                filtered = filterVisvalingamWhyatt(filtered, self.visvalingamWhyattTolerance)

            if self.roundToIntegers:
                filtered = filterRoundedPoints(filtered)
            if self.removeOverlappingPoints:
                filtered = filterOverlappingPoints(filtered)
            if self.spikeTolerance:
                filtered = filterSpikes(filtered, self.spikeTolerance)
            if self.minimumContourSegments:
                filtered = filterContourSegmentCounts(filtered, self.minimumContourSegments)
            if self.minimumContourArea:
                filtered = filterContourAreas(filtered, self.minimumContourArea)
            break
        return filtered

# -------
# Filters
# -------

def filterRoundedPoints(contour):
    """
    >>> input = [
    ...     ("moveTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((1.1, 1.1)) ),
    ...     ("endPath", pointsToOperands(()) )
    ... ]
    >>> expected = [
    ...     ("moveTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((1, 1)) ),
    ...     ("endPath", pointsToOperands(()) )
    ... ]
    >>> output = filterRoundedPoints(input)
    >>> output == expected
    True

    >>> recordingPen = RecordingPen()
    >>> simplifyPen = SimplifyContoursPen(
    ...     recordingPen,
    ...     **noArgs(roundToIntegers=True)
    ... )
    >>> replayRecording(input, simplifyPen)
    >>> recordingPen.value == expected
    True
    """
    recordingPen = RecordingPen()
    roundingPen = RoundingPen(recordingPen)
    replayRecording(contour, roundingPen)
    return recordingPen.value

def filterOverlappingPoints(contour):
    """
    >>> input = [
    ...     ("moveTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((1, 1)) ),
    ...     ("lineTo", pointsToOperands((1, 1)) ),
    ...     ("lineTo", pointsToOperands((0, 0)) ),
    ...     ("endPath", pointsToOperands(()) )
    ... ]
    >>> expected = [
    ...     ("moveTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((1, 1)) ),
    ...     ("lineTo", pointsToOperands((0, 0)) ),
    ...     ("endPath", pointsToOperands(()) )
    ... ]
    >>> output = filterOverlappingPoints(input)
    >>> output == expected
    True

    >>> recordingPen = RecordingPen()
    >>> simplifyPen = SimplifyContoursPen(
    ...     recordingPen,
    ...     **noArgs(removeOverlappingPoints=True)
    ... )
    >>> replayRecording(input, simplifyPen)
    >>> recordingPen.value == expected
    True
    """
    filtered = []
    prevPt = None
    for operator, operands in contour:
        if operator in ("endPath", "closePath"):
            pass
        else:
            point = operands[-1]
            if point == prevPt:
                continue
            else:
                prevPt = point
        filtered.append((operator, operands))
    return filtered

def filterContourSegmentCounts(contour, minimumContourSegments=defaultMinimumContourSegments):
    """
    >>> input = [
    ...     ("moveTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((0, 0)) ),
    ...     ("endPath", pointsToOperands(()) )
    ... ]
    >>> expected = []
    >>> output = filterContourSegmentCounts(input)
    >>> output == expected
    True

    >>> recordingPen = RecordingPen()
    >>> simplifyPen = SimplifyContoursPen(
    ...     recordingPen,
    ...     **noArgs(minimumContourSegments=defaultMinimumContourSegments)
    ... )
    >>> replayRecording(input, simplifyPen)
    >>> recordingPen.value == expected
    True

    >>> input = [
    ...     ("moveTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((0, 0)) ),
    ...     ("endPath", pointsToOperands(()) )
    ... ]
    >>> expected = [
    ...     ("moveTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((0, 0)) ),
    ...     ("endPath", pointsToOperands(()) )
    ... ]
    >>> output = filterContourSegmentCounts(input)
    >>> output == expected
    True

    >>> recordingPen = RecordingPen()
    >>> simplifyPen = SimplifyContoursPen(
    ...     recordingPen,
    ...     **noArgs(minimumContourSegments=defaultMinimumContourSegments)
    ... )
    >>> replayRecording(input, simplifyPen)
    >>> recordingPen.value == expected
    True
    """
    segments = [i for i in contour if i[0] not in ("endPath", "closePath")]
    if not segments:
        return []
    if len(segments) < minimumContourSegments:
        return []
    return contour

def filterContourAreas(contour, minArea=defaultMinimumContourArea):
    """
    >>> input = [
    ...     ("moveTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((0, 100)) ),
    ...     ("lineTo", pointsToOperands((100, 100)) ),
    ...     ("lineTo", pointsToOperands((100, 0)) ),
    ...     ("closePath", pointsToOperands(()) )
    ... ]
    >>> expected = input
    >>> output = filterContourAreas(input)
    >>> output == expected
    True

    >>> input = [
    ...     ("moveTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((0, 10)) ),
    ...     ("lineTo", pointsToOperands((10, 10)) ),
    ...     ("lineTo", pointsToOperands((10, 0)) ),
    ...     ("closePath", pointsToOperands(()) )
    ... ]
    >>> expected = []
    >>> output = filterContourAreas(input)
    >>> output == expected
    True

    >>> recordingPen = RecordingPen()
    >>> simplifyPen = SimplifyContoursPen(
    ...     recordingPen,
    ...     **noArgs(minimumContourArea=defaultMinimumContourArea)
    ... )
    >>> replayRecording(input, simplifyPen)
    >>> recordingPen.value == expected
    True
    """
    # first do a simple bounds calculation.
    # if the area is less than the minimum
    # the more complex aarea calculation
    # doesn't need to be done because
    # the result of that can't be larger
    # than the bounds area.
    boundsPen = BoundsPen(None)
    replayRecording(contour, boundsPen)
    if boundsPen.bounds is None:
        return []
    xMin, yMin, xMax, yMax = boundsPen.bounds
    boundsWidth = xMax - xMin
    boundsHeight = yMax - yMin
    boundsArea = boundsWidth * boundsHeight
    if boundsArea < minArea:
        return []
    # now do the more complex area calculation
    areaPen = AreaPen()
    replayRecording(contour, areaPen)
    if abs(areaPen.value) < minArea:
        return []
    return contour

def filterCurveLengths(contour, minimumCurveLength=defaultMinimumCurveLength):
    """
    >>> input = [
    ...     ("moveTo", pointsToOperands((0, 0)) ),
    ...     ("curveTo", pointsToOperands((0, 5), (5, 10), (10, 10)) ),
    ...     ("curveTo", pointsToOperands((10, 35), (35, 41), (41, 41)) ),
    ...     ("lineTo", pointsToOperands((50, 50)) ),
    ...     ("endPath", pointsToOperands(()) )
    ... ]
    >>> expected = [
    ...     ("moveTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((10, 10)) ),
    ...     ("curveTo", pointsToOperands((10, 35), (35, 41), (41, 41)) ),
    ...     ("lineTo", pointsToOperands((50, 50)) ),
    ...     ("endPath", pointsToOperands(()) )
    ... ]
    >>> output = filterCurveLengths(input)
    >>> output == expected
    True

    >>> recordingPen = RecordingPen()
    >>> simplifyPen = SimplifyContoursPen(
    ...     recordingPen,
    ...     **noArgs(minimumCurveLength=defaultMinimumCurveLength)
    ... )
    >>> replayRecording(input, simplifyPen)
    >>> recordingPen.value == expected
    True
    """
    filtered = []
    prevPt = None
    for operator, operands in contour:
        if operator == "moveTo":
            prevPt = operands[0]
            filtered.append((operator, operands))
        elif operator == "lineTo":
            prevPt = operands[0]
            filtered.append((operator, operands))
        elif operator == "curveTo":
            pt1 = operands[0]
            pt2 = operands[1]
            pt3 = operands[2]
            # if the length of prevPt - pt3
            # is greater than the minimum,
            # the curve length calculations
            # don't need to be done because
            # the curve can't be shorter than
            # the line length.
            lineLength = calcLineLength(prevPt, pt3)
            if lineLength > minimumCurveLength:
                filtered.append((operator, operands))
            else:
                # approximation is good enough here
                curveLength = approximateCubicArcLength(prevPt, pt1, pt2, pt3)
                if curveLength < minimumCurveLength:
                    filtered.append(("lineTo", (pt3,)))
                else:
                    filtered.append((operator, operands))
            prevPt = pt3
        else:
            filtered.append((operator, operands))
    return filtered

def _filterSequentialLines(contour, filter, *args):
    filtered = []
    lineSequence = []
    for operator, operands in contour:
        if operator == "moveTo":
            lineSequence.append((operator, operands))
        elif operator == "lineTo":
            lineSequence.append((operator, operands))
        else:
            if not lineSequence:
                pass
            elif len(lineSequence) == 1:
                filtered.append(lineSequence[0])
            elif len(lineSequence) == 2:
                filtered.append(lineSequence[0])
                filtered.append(lineSequence[1])
            else:
                firstOperator = lineSequence[0][0]
                points = [o[1][0] for o in lineSequence]
                points = filter(points, *args)
                filtered.append((firstOperator, (tuple(points.pop(0)),)))
                for point in points:
                    filtered.append(("lineTo", (tuple(point),)))
            filtered.append((operator, operands))
            lineSequence = []
    return filtered

def filterSpikes(contour, tolerance=defaultSpikeTolerance):
    return _filterSequentialLines(contour, removeSpikes, tolerance)

def filterDouglasPeucker(contour, tolerance=defaultDouglasPeuckerTolerance):
    """
    >>> input = [
    ...     ("moveTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((10, 1)) ),
    ...     ("lineTo", pointsToOperands((20, -1)) ),
    ...     ("lineTo", pointsToOperands((30, 0)) ),
    ...     ("lineTo", pointsToOperands((40, 20)) ),
    ...     ("lineTo", pointsToOperands((50, -20)) ),
    ...     ("endPath", ()),
    ... ]
    >>> expected = [
    ...     ("moveTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((30, 0)) ),
    ...     ("lineTo", pointsToOperands((40, 20)) ),
    ...     ("lineTo", pointsToOperands((50, -20)) ),
    ...     ("endPath", pointsToOperands(()) ),
    ... ]
    >>> output = filterDouglasPeucker(input)
    >>> output == expected
    True

    >>> recordingPen = RecordingPen()
    >>> simplifyPen = SimplifyContoursPen(
    ...     recordingPen,
    ...     **noArgs(douglasPeuckerTolerance=defaultDouglasPeuckerTolerance)
    ... )
    >>> replayRecording(input, simplifyPen)
    >>> recordingPen.value == expected
    True
    """
    return _filterSequentialLines(contour, applyDouglasPeucker, tolerance)

def filterVisvalingamWhyatt(contour, tolerance=defaultDouglasPeuckerTolerance):
    """
    >>> input = [
    ...     ("moveTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((10, 0)) ),
    ...     ("lineTo", pointsToOperands((20, 0)) ),
    ...     ("lineTo", pointsToOperands((30, 0)) ),
    ...     ("lineTo", pointsToOperands((40, 20)) ),
    ...     ("lineTo", pointsToOperands((50, -20)) ),
    ...     ("endPath", ()),
    ... ]
    >>> expected = [
    ...     ("moveTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((30, 0)) ),
    ...     ("lineTo", pointsToOperands((40, 20)) ),
    ...     ("lineTo", pointsToOperands((50, -20)) ),
    ...     ("endPath", pointsToOperands(()) ),
    ... ]
    >>> output = filterVisvalingamWhyatt(input)
    >>> output == expected
    True

    >>> recordingPen = RecordingPen()
    >>> simplifyPen = SimplifyContoursPen(
    ...     recordingPen,
    ...     **noArgs(visvalingamWhyattTolerance=defaultVisvalingamWhyattTolerance)
    ... )
    >>> replayRecording(input, simplifyPen)
    >>> recordingPen.value == expected
    True
    """
    return _filterSequentialLines(contour, applyVisvalingamWhyatt, tolerance)

def filterShallowCurves(contour, tolerance=defaultShallowCurveTolerance):
    """
    >>> input = [
    ...     ("moveTo", pointsToOperands((0, 0)) ),
    ...     ("curveTo", pointsToOperands((30, 3), (70, 3), (100, 0)) ),
    ...     ("curveTo", pointsToOperands((130, 5), (170, 5), (200, 0)) ),
    ...     ("endPath", pointsToOperands(()) )
    ... ]
    >>> expected = [
    ...     ("moveTo", pointsToOperands((0, 0)) ),
    ...     ("lineTo", pointsToOperands((100, 0)) ),
    ...     ("curveTo", pointsToOperands((130, 5), (170, 5), (200, 0)) ),
    ...     ("endPath", pointsToOperands(()))
    ... ]
    >>> output = filterShallowCurves(input)
    >>> output == expected
    True

    >>> recordingPen = RecordingPen()
    >>> simplifyPen = SimplifyContoursPen(
    ...     recordingPen,
    ...     **noArgs(shallowCurveTolerance=defaultShallowCurveTolerance)
    ... )
    >>> replayRecording(input, simplifyPen)
    >>> recordingPen.value == expected
    True
    """
    tolerance = tolerance / 100
    filtered = []
    prevPt = None
    for operator, operands in contour:
        if operator == "moveTo":
            prevPt = operands[0]
            filtered.append((operator, operands))
        elif operator == "lineTo":
            prevPt = operands[0]
            filtered.append((operator, operands))
        elif operator == "curveTo":
            pt1 = operands[0]
            pt2 = operands[1]
            pt3 = operands[2]
            curveLength = calcCubicArcLength(prevPt, pt1, pt2, pt3)
            lineLength = calcLineLength(prevPt, pt3)
            if 1.0 - lineLength / curveLength < tolerance:
                filtered.append(("lineTo", (pt3,)))
            else:
                filtered.append((operator, operands))
            prevPt = pt3
        else:
            filtered.append((operator, operands))
    return filtered

# ----------
# Algorithms
# ----------

def calcLineLength(pt1, pt2):
    pt1 = complex(*pt1)
    pt2 = complex(*pt2)
    return abs(pt1 - pt2)

def calculateAngle(pt1, pt2):
    x1, y1 = pt1
    x2, y2 = pt2
    xDiff = x2 - x1
    yDiff = y2 - y1
    angle = math.atan2(yDiff, xDiff)
    return math.degrees(angle)

def removeSpikes(points, tolerance=10):
    if len(points) <= 3:
        return points
    filtered = []
    p1 = points[-1]
    for i, p2 in enumerate(points):
        j = i + 1
        if j == len(points):
            filtered.append(p2)
            break
        p3 = points[j]
        a1 = calculateAngle(p1, p2)
        a2 = calculateAngle(p3, p2)
        if abs(a1 - a2) < tolerance:
            filtered.extend(points[i+1:])
            filtered = removeSpikes(filtered)
            break
        else:
            filtered.append(p2)
            p1 = p2
    return filtered

# ----
# Data
# ----

# class SimplifyContoursDataPen(ContourFilterPen):
#
#     def __init__(self):
#         self.curveSizes = {}
#         self.lineSequenceVariations = {}
#         self.contourSegments = {}
#         self.contourAreas = {}
#
#     def filterContour(self, contour):
#         pass

class CountPen(AbstractPen):

    pointCount = 0

    def moveTo(self, pt):
        self.pointCount += 1

    def lineTo(self, pt):
        self.pointCount += 1

    def curveTo(self, *points):
        self.pointCount += 3

    def closePath(self):
        pass

    def endPath(self):
        pass


# ------------
# Test Support
# ------------

def pointsToOperands(*points):
    """
    >>> pointsToOperands((1, 2))
    ((1, 2),)
    >>> pointsToOperands((1, 2), (3, 4), (5, 6))
    ((1, 2), (3, 4), (5, 6))
    >>> pointsToOperands(())
    ()
    """
    if not points[0]:
        return ()
    return points


if __name__ == "__main__":
    import doctest
    doctest.testmod()
