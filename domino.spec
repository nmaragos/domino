# Build: uv run pyinstaller domino.spec --noconfirm
a = Analysis(
    ["src/receipt.py"],
    pathex=["src"],
    datas=[
        ("src/receipt.ui", "."),
        ("src/calculator.ui", "."),
        ("src/resource", "resource"),
        ("templates", "templates"),
    ],
    hiddenimports=["win32com.client", "win32timezone"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DominoReceipt",
    console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="DominoReceipt")
