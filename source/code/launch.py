from mojo.pipTools import installNeededPackages

try:
    import tracer
except ModuleNotFoundError:
    installNeededPackages(
        "Tracer",
        [
            dict(
                packageName="simplification"
            ),
            dict(
                packageName="Pillow",
                importName="PIL"
            )
        ]
    )