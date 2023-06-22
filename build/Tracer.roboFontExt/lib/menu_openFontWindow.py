from vanilla import dialogs
from tracer.window import TracerWindowController

if __name__ == "__main__":
    font = CurrentFont()
    if font is None:
        dialogs.message("A font must be open to run Tracer.")
    else:
        TracerWindowController(font=font)