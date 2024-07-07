import win32print


# printer = win32print.EnumPrinters(2, None, 5)


# device_caps = win32print.GetDeviceCaps(printer_handle, win32print.PRINTER_ENUM_LOCAL)

# for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL):
#     print(p[2])

printer_name = win32print.GetDefaultPrinter()

printer_handle = win32print.OpenPrinter(printer_name)
# print(printer_handle)
printer_info = win32print.GetPrinter(printer_handle, 2)
devmode = printer_info["pDevMode"]

print(devmode.DefaultSource)
print(devmode.Color)
print(devmode.PrintQuality)
print(devmode.Duplex)

# print(printer_info["pDevMode"].PrintQuality)

# for i in printer_info:
#     print(i)

# https://timgolden.me.uk/pywin32-docs/win32print.html