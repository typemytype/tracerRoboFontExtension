import pathlib
import tempfile
from fontParts.world import RGlyph
import AppKit
from PIL import Image as PILImage
import ezui
from . import trace
from . import simplify

class TracerWindowController(ezui.WindowController):

    def build(self,
            font
        ):
        self.font = font
        content = """
        = HorizontalStack

        # --------
        # Settings
        # --------

        * TwoColumnForm @settingsForm

        > !§ Trace

        > : Threshold:
        > --X-- [__] @traceThreshold

        > : Tolerance:
        > --X-- [__] @traceTolerance

        > : Turd Size:
        > --X-- [__] @traceTurdSize

        > : Blur:
        > --X-- [__] @traceBlur

        > :
        > [ ] Invert @traceInvert

        > !§ Simplify

        > : Segment Count:
        > --X-- [__] @simplifyMinimumContourSegments

        > : Small Curves:
        > --X-- [__] @simplifyMinimumCurveLength

        > : Small Contours:
        > --X-- [__] @simplifyMinimumContourArea

        > : Douglas Peucker:
        > --X-- [__] @simplifyDouglasPeuckerTolerance

        > : Visvalingam Whyatt:
        > --X-- [__] @simplifyVisvalingamWhyattTolerance

        > : Shallow Curves:
        > --X-- [__] @simplifyShallowCurveTolerance

        > : Spikes:
        > --X-- [__] @simplifySpikeTolerance

        > :
        > [X] Round @simplifyRoundToIntegers

        > :
        > [X] Overlapping Points @simplifyRemoveOverlappingPoints

        > !§ Destination

        > : Layer:
        > [_ ...] @destinationLayer

        > :
        > (Trace Selected Glyphs) @destinationTraceSelectedGlyphs

        > :
        > (Trace All Glyphs) @destinationTraceAllGlyphs

        # ----------
        # Glyph List
        # ----------

        |----| @glyphsTable
        |----|

        # -------
        # Preview
        # -------

        * VerticalStack
          > * MerzView @preview
          > * HorizontalStack
            >> . @previewLabel
            >> (...) @previewOptions

        ==============================

        (...) @footerActionButton
        (Finished) @finishedButton
        """
        sliderWidth = 150

        layerNames = list(self.font.layerOrder)
        if "traced" in layerNames:
            layerNames.remove("traced")
        layerNames.append("traced")

        glyphNames = []
        for glyphName in self.font.glyphOrder:
            if glyphName not in font:
                continue
            glyph = font[glyphName]
            if glyph.image:
                glyphNames.append(glyphName)

        descriptionData = dict(
            settingsForm=dict(
                titleColumnWidth=130
            ),
            glyphsTable=dict(
                items=glyphNames,
                width=150
            ),

            # Footer

            footerActionButton=dict(
                itemDescriptions=[
                    dict(
                        identifier="printSettingsFooterItem",
                        text="Print Settings"
                    ),
                    dict(
                        identifier="importSettingsFooterItem",
                        text="Import Settings"
                    ),
                    dict(
                        identifier="exportSettingsFooterItem",
                        text="Export Settings"
                    )
                ],
                gravity="leading"
            ),

            finishedButton=dict(
                gravity="trailing"
            ),

            # Preview

            preview=dict(
                width=750,
                backgroundColor=(1, 1, 1, 1)
            ),

            previewLabel=dict(
                width="fill"
            ),

            previewOptions=dict(
                gravity="trailing",
                itemDescriptions=[
                    dict(
                        identifier="previewImageItem",
                        text="Image",
                        state=1
                    ),
                    "----",
                    dict(
                        identifier="previewTraceFillItem",
                        text="Trace Fill",
                        state=1
                    ),
                    dict(
                        identifier="previewTraceStrokeItem",
                        text="Trace Stroke",
                        state=1
                    ),
                    "----",
                    dict(
                        identifier="previewSimplifiedFillItem",
                        text="Simplified Fill",
                        state=1
                    ),
                    dict(
                        identifier="previewSimplifiedStrokeItem",
                        text="Simplified Stroke",
                        state=1
                    ),
                ]
            ),

            # Trace Controls

            traceThreshold=dict(
                valueType="float:2",
                sliderWidth=sliderWidth,
                minValue=0,
                maxValue=1,
                value=0.5,
                tickMarks=2,
                stopOnTickMarks=False,
                continuous=False
            ),

            traceTolerance=dict(
                valueType="float:2",
                sliderWidth=sliderWidth,
                minValue=0,
                maxValue=5,
                value=1,
                tickMarks=2,
                stopOnTickMarks=False,
                continuous=False
            ),

            traceTurdSize=dict(
                sliderWidth=sliderWidth,
                minValue=0,
                maxValue=200,
                value=10,
                valueType="integer",
                tickMarks=2,
                stopOnTickMarks=False,
                continuous=False
            ),

            traceBlur=dict(
                valueType="float:2",
                sliderWidth=sliderWidth,
                minValue=0,
                maxValue=5,
                value=1,
                tickMarks=2,
                stopOnTickMarks=False,
                continuous=False
            ),

            # Simplify Controls

            simplifyMinimumContourSegments=dict(
                valueType="integer",
                minValue=0,
                maxValue=10,
                value=4,
                tickMarks=11,
                stopOnTickMarks=True,
                sliderWidth=sliderWidth,
                continuous=False
            ),

            simplifyMinimumCurveLength=dict(
                valueType="float:2",
                minValue=0,
                maxValue=30,
                value=10,
                tickMarks=2,
                stopOnTickMarks=False,
                sliderWidth=sliderWidth,
                continuous=False
            ),

            simplifyMinimumContourArea=dict(
                valueType="integer",
                minValue=0,
                maxValue=1000,
                value=100,
                tickMarks=2,
                stopOnTickMarks=False,
                sliderWidth=sliderWidth,
                continuous=False
            ),

            simplifyDouglasPeuckerTolerance=dict(
                valueType="float:2",
                minValue=0,
                maxValue=2,
                value=1.0,
                tickMarks=2,
                stopOnTickMarks=False,
                sliderWidth=sliderWidth,
                continuous=False
            ),

            simplifyVisvalingamWhyattTolerance=dict(
                valueType="float:2",
                minValue=0,
                maxValue=2,
                value=1.0,
                tickMarks=2,
                stopOnTickMarks=False,
                sliderWidth=sliderWidth,
                continuous=False
            ),

            simplifyShallowCurveTolerance=dict(
                valueType="float:2",
                minValue=0,
                maxValue=1,
                value=0.2,
                tickMarks=2,
                stopOnTickMarks=False,
                sliderWidth=sliderWidth,
                continuous=False
            ),

            simplifySpikeTolerance=dict(
                valueType="float:2",
                minValue=0,
                maxValue=45,
                value=10,
                tickMarks=2,
                stopOnTickMarks=False,
                sliderWidth=sliderWidth,
                continuous=False
            ),

            # Destination Controls

            destinationLayer=dict(
                items=layerNames,
                value="traced"
            )

        )

        cls = ezui.EZWindow
        windowKwargs = dict(
            content=content,
            descriptionData=descriptionData,
            controller=self
        )
        fontWindow = self.font.fontWindow()
        if fontWindow:
            cls = ezui.EZSheet
            windowKwargs["parent"] = fontWindow.w
        else:
            windowKwargs["title"] = "Tracer"

        self.w = cls(**windowKwargs)

        self.previewSettings = dict(
            image=True,
            traceFill=True,
            traceStroke=True,
            simplifiedFill=True,
            simplifiedStroke=True
        )

        self.previewView = self.w.getItem("preview")
        self.previewContainer = self.previewView.getMerzContainer()
        self.previewCenterLayer = self.previewContainer.appendBaseSublayer(
            position=("center", "center")
        )
        self.previewImageLayer = self.previewCenterLayer.appendImageSublayer(
            opacity=0.25
        )
        self.previewTraceLayer = self.previewCenterLayer.appendPathSublayer(
            position=(0, -self.font.info.descender),
            strokeWidth=2
        )
        self.previewSimplifiedLayer = self.previewCenterLayer.appendPathSublayer(
            position=(0, -self.font.info.descender),
            strokeWidth=2
        )
        self.updatePreviewSettings()

    def started(self):
        self.settingsFormCallback(self.w.getItem("settingsForm"))
        glyphsTable = self.w.getItem("glyphsTable")
        self.w.open()

    # Footer

    def _settingsFromText(self, text):
        traceSettings = {}
        simplifySettings = {}
        destinationSettings = {}
        d = None
        inDestination = False
        for line in text.splitlines():
            if not line:
                continue
            if line.startswith("Trace:"):
                inDestination = False
                d = traceSettings
            elif line.startswith("Simplify:"):
                inDestination = False
                d = simplifySettings
            elif line.startswith("Destination:"):
                inDestination = True
                d = destinationSettings
            elif line.startswith("- "):
                line = line[2:].strip()
                key, value = line.split(": ", 1)
                if not inDestination:
                    value = float(value)
                d[key] = value
        groups = [
            (traceSettings, "trace"),
            (simplifySettings, "simplify")
        ]
        for settings, tag in groups:
            for key, value in settings.items():
                identifier = tag + key[0].upper() + key[1:]
                self.w.getItem(identifier).set(value)
        self.w.getItem("destinationLayer").set(destinationSettings["layer"])
        self.traceSettings.update(traceSettings)
        self.simplifySettings.update(simplifySettings)
        self.updateTracePreview()
        self.updateSimplifiedPreview()
        self.updatePreviewLabel()

    def _settingsToText(self):
        def dictToLines(d):
            l = []
            for key, value in sorted(d.items()):
                l.append(f"- {key}: {value}")
            return l

        destinationSettings = dict(
            layer=self.w.getItem("destinationLayer").get()
        )
        text = []
        text.append("Trace:")
        text += dictToLines(self.traceSettings)
        text.append("")
        text.append("Simplify:")
        text += dictToLines(self.simplifySettings)
        text.append("")
        text.append("Destination:")
        text += dictToLines(destinationSettings)
        return "\n".join(text)

    def printSettingsFooterItemCallback(self, sender):
        divider = "-" * 10
        text = []
        print(divider)
        print("")
        print(self._settingsToText())
        print("")
        print(divider)

    def importSettingsFooterItemCallback(self, sender):
        self.showGetFile(
            callback=self._importSettings,
            allowsMultipleSelection=False,
            fileTypes=["rftracer"]
        )

    def _importSettings(self, path):
        if not path:
            return
        path = path[0]
        with open(path, "r") as f:
            text = f.read()
        self._settingsFromText(text)

    def exportSettingsFooterItemCallback(self, sender):
        self.showPutFile(
            callback=self._exportSettings,
            fileName="Untitled.rftracer",
            fileTypes=["rftracer"]
        )

    def _exportSettings(self, path):
        if not path:
            return
        text = self._settingsToText()
        with open(path, "w") as f:
            f.write(text)

    def finishedButtonCallback(self, sender):
        self.w.close()

    # Glyphs Table

    selectedImageGlyph = None
    selectedTracedGlyph = None
    selectedSimplifiedGlyph = None

    def glyphsTableSelectionCallback(self, sender):
        selectedItems = sender.getSelectedItems()
        if len(selectedItems) != 1:
            self.selectedImageGlyph = None
            self.selectedTracedGlyph = None
            self.selectedSimplifiedGlyph = None
        else:
            glyphName = selectedItems[0]
            self.selectedImageGlyph = self.font[glyphName]
            self.selectedTracedGlyph = RGlyph()
            self.selectedTracedGlyph.width = self.selectedImageGlyph.width
            self.selectedSimplifiedGlyph = RGlyph()
            self.selectedSimplifiedGlyph.width = self.selectedImageGlyph.width
            self.updateTracePreview()
            self.updateSimplifiedPreview()
        self.updatePreview()

    # Preview

    def updatePreview(self):
        previewLabel = self.w.getItem("previewLabel")
        if self.selectedImageGlyph is None:
            previewLabel.set("")
            self.previewImageLayer.setImage(None)
            self.previewTraceLayer.setPath(None)
            self.previewSimplifiedLayer.setPath(None)
            return
        # center
        view = self.previewView
        viewWidth = view.width()
        viewHeight = view.height()
        glyph = self.selectedImageGlyph
        font = glyph.font
        verticalMetrics = [
            font.info.descender,
            font.info.xHeight,
            font.info.capHeight,
            font.info.ascender
        ]
        bottom = min(verticalMetrics)
        top = max(verticalMetrics)
        contentHeight = top - bottom
        contentWidth = glyph.width
        widthScale = viewWidth / contentWidth
        heightScale = viewHeight / contentHeight
        scale = min((widthScale, heightScale)) * 0.9
        self.previewCenterLayer.setSize((contentWidth, contentHeight))
        self.previewContainer.setContainerScale(scale)
        # image
        image = self.selectedImageGlyph.image
        imageXMin, imageYMin, imageXMax, imageYMax = image.bounds
        imageX = imageXMin
        imageY = imageYMin - font.info.descender
        imageW = imageXMax - imageXMin
        imageH = imageYMax - imageYMin
        imageData = image.data
        data = AppKit.NSData.dataWithBytes_length_(imageData, len(imageData))
        image = AppKit.NSImage.alloc().initWithData_(data)
        self.previewImageLayer.setImage(image)
        self.previewImageLayer.setPosition((imageX, imageY))
        self.previewImageLayer.setSize((imageW, imageH))
        self.updatePreviewLabel()

    def updatePreviewLabel(self, text=""):
        previewLabel = self.w.getItem("previewLabel")
        if self.selectedImageGlyph is None:
            previewLabel.set("")
            return
        if not text:
            tracePointCount = simplify.countGlyphPoints(self.selectedTracedGlyph)
            simplifiedPointCount = simplify.countGlyphPoints(self.selectedSimplifiedGlyph)
            text = f"Trace: {tracePointCount} points | Simplified: {simplifiedPointCount} points"
        previewLabel.set(text)
        previewLabel.getNSTextField().display()

    def updateTracePreview(self):
        if self.selectedImageGlyph is None:
            return
        self.updatePreviewLabel("Tracing...")
        self._traceGlyph(
            self.selectedImageGlyph,
            self.selectedTracedGlyph
        )
        path = self.selectedTracedGlyph.getRepresentation("merz.CGPath")
        self.previewTraceLayer.setPath(path)

    def updateSimplifiedPreview(self):
        if self.selectedImageGlyph is None:
            return
        self.updatePreviewLabel("Simplifying...")
        self._simplifyGlyph(
            self.selectedTracedGlyph,
            self.selectedSimplifiedGlyph
        )
        path = self.selectedSimplifiedGlyph.getRepresentation("merz.CGPath")
        self.previewSimplifiedLayer.setPath(path)

    def updatePreviewSettings(self):
        settings = self.previewSettings
        showImage = settings["image"]
        showTraceFill = settings["traceFill"]
        showTraceStroke = settings["traceStroke"]
        showTrace = showTraceFill or showTraceStroke
        showSimplifiedFill = settings["simplifiedFill"]
        showSimplifiedStroke = settings["simplifiedStroke"]
        showSimplified = showSimplifiedFill or showSimplifiedStroke

        traceFillColor = None
        traceStrokeColor = (1, 0, 0, 0.5)
        simplifiedFillColor = (0, 0, 1, 0.25)
        simplifiedStrokeColor = (0, 0, 1, 1)
        soloFillStrokeStrokeColor = (0, 0, 0, 1)
        soloFillStrokeFillColor = (0, 0, 0, 0.25)
        soloStrokeColor = (0, 0, 0, 1)
        soloFillColor = (0, 0, 0, 1)
        clear = (0, 0, 0, 0)

        if not showImage:
            if not showSimplified:
                traceFillColor = soloFillStrokeFillColor
                traceStrokeColor = soloFillStrokeStrokeColor
                if not showTraceStroke:
                    traceFillColor = soloFillColor
                if not showTraceFill:
                    traceStrokeColor = soloStrokeColor
            if not showTrace:
                simplifiedFillColor = soloFillStrokeFillColor
                simplifiedStrokeColor = soloFillStrokeStrokeColor
                if not showSimplifiedStroke:
                    simplifiedFillColor = soloFillColor
                if not showSimplifiedFill:
                    simplifiedStrokeColor = soloStrokeColor

        if not showTraceFill:
            traceFillColor = clear
        if not showTraceStroke:
            traceStrokeColor = clear
        if not showSimplifiedFill:
            simplifiedFillColor = clear
        if not showSimplifiedStroke:
            simplifiedStrokeColor = clear

        self.previewImageLayer.setVisible(showImage)
        with self.previewTraceLayer.propertyGroup():
            self.previewTraceLayer.setFillColor(traceFillColor)
            self.previewTraceLayer.setStrokeColor(traceStrokeColor)
            self.previewTraceLayer.setVisible(showTrace)
        with self.previewSimplifiedLayer.propertyGroup():
            self.previewSimplifiedLayer.setFillColor(simplifiedFillColor)
            self.previewSimplifiedLayer.setStrokeColor(simplifiedStrokeColor)
            self.previewSimplifiedLayer.setVisible(showSimplified)

    def previewImageItemCallback(self, sender):
        state = not sender.state()
        sender.setState_(state)
        self.previewSettings["image"] = state
        self.updatePreviewSettings()

    def previewTraceFillItemCallback(self, sender):
        state = not sender.state()
        sender.setState_(state)
        self.previewSettings["traceFill"] = state
        self.updatePreviewSettings()

    def previewTraceStrokeItemCallback(self, sender):
        state = not sender.state()
        sender.setState_(state)
        self.previewSettings["traceStroke"] = state
        self.updatePreviewSettings()

    def previewSimplifiedFillItemCallback(self, sender):
        state = not sender.state()
        sender.setState_(state)
        self.previewSettings["simplifiedFill"] = state
        self.updatePreviewSettings()

    def previewSimplifiedStrokeItemCallback(self, sender):
        state = not sender.state()
        sender.setState_(state)
        self.previewSettings["simplifiedStroke"] = state
        self.updatePreviewSettings()

    # Settings

    traceSettings = {}
    simplifySettings = {}

    def settingsFormCallback(self, sender):
        settings = sender.getItemValues()
        traceChange = False
        simplifyChange = False
        for key, value in sorted(settings.items()):
            isTrace = False
            isSimplify = False
            if key.startswith("trace"):
                isTrace = True
                key = key[len("trace"):]
                storage = self.traceSettings
            elif key.startswith("simplify"):
                isSimplify = True
                key = key[len("simplify"):]
                storage = self.simplifySettings
            if True not in (isTrace, isSimplify):
                continue
            key = key[0].lower() + key[1:]
            oldValue = storage.get(key, "undefined")
            if value != oldValue:
                if isTrace:
                    traceChange = True
                    simplifyChange = True
                elif isSimplify:
                    simplifyChange = True
            storage[key] = value
        if traceChange:
            self.updateTracePreview()
        if simplifyChange:
            self.updateSimplifiedPreview()
        self.updatePreviewLabel()

    # Processing

    def destinationTraceSelectedGlyphsCallback(self, sender):
        glyphNames = self.w.getItem("glyphsTable").getSelectedItems()
        if glyphNames:
            self._traceGlyphs(glyphNames)

    def destinationTraceAllGlyphsCallback(self, sender):
        glyphNames = self.w.getItem("glyphsTable").getItems()
        if glyphNames:
            self._traceGlyphs(glyphNames)

    def _traceGlyphs(self, glyphNames):
        imageLayer = self.font.defaultLayer
        destinationLayerName = self.w.getItem("destinationLayer").get()
        if destinationLayerName not in self.font.layerOrder:
            self.font.newLayer(destinationLayerName)
        destinationLayer = self.font.getLayer(destinationLayerName)
        progressBar = self.startProgress(
            text="Processing...",
            maxValue=len(glyphNames),
            parent=self.w
        )
        try:
            for glyphName in glyphNames:
                progressBar.setText(f"Processing {glyphName}...")
                imageGlyph = self.font[glyphName]
                if glyphName not in destinationLayer:
                    destinationLayer.newGlyph(glyphName)
                destinationGlyph = destinationLayer[glyphName]
                with destinationGlyph.holdChanges():
                    destinationGlyph.unicodes = imageGlyph.unicodes
                    self._traceGlyph(imageGlyph, destinationGlyph)
                    self._simplifyGlyph(imageGlyph, None)
                progressBar.increment()
        finally:
            progressBar.close()

    def _traceGlyph(self, imageGlyph, destinationGlyph):
        if destinationGlyph is not None:
            destinationGlyph.width = imageGlyph.width
            destinationGlyph.clearContours()
        trace.traceGlyphImage(
            glyphWithImage=imageGlyph,
            destinationGlyph=destinationGlyph,
            **self.traceSettings
        )
        destinationGlyph.scaleBy(imageGlyph.image.scale)
        destinationGlyph.moveBy(imageGlyph.image.transformation[-2:])

    def _simplifyGlyph(self, tracedGlyph, destinationGlyph):
        if destinationGlyph is not None:
            destinationGlyph.clearContours()
            destinationGlyph.width = tracedGlyph.width
        simplify.simplifyGlyphContours(
            glyph=tracedGlyph,
            destinationGlyph=destinationGlyph,
            **self.simplifySettings
        )

