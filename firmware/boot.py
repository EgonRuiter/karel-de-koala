"""
Karel de Koala - CircuitPython USB Descriptor & Boot Configuration
Study Association Sticky (Information Science, Utrecht University)

Place this file in the root of the CircuitPython drive as /boot.py.
Changes to boot.py take effect after a hard reset (unplug and replug USB).
"""

import time
import board
import digitalio
import storage
import usb_cdc
import usb_hid

try:
    import microcontroller
except ImportError:
    microcontroller = None

# Default to board.NEOPIXEL -> GP16 (RP2350 SuperMini standard); set GP23/GP22 in code.py if batch differs.
NEOPIXEL_PIN = getattr(board, "NEOPIXEL", None) or getattr(board, "GP16", None) or getattr(board, "GP23", None)


def _is_pin_held_low(pin_name):
    """Check whether a GPIO pin is pulled LOW (button pressed during plug-in)."""
    pin = getattr(board, pin_name, None)
    if pin is None and microcontroller is not None:
        gpio_name = "GPIO" + pin_name[2:]
        pin = getattr(microcontroller.pin, gpio_name, None)
    if pin is None:
        return False

    dio = None
    try:
        dio = digitalio.DigitalInOut(pin)
        dio.direction = digitalio.Direction.INPUT
        dio.pull = digitalio.Pull.UP
        time.sleep(0.01)
        return not dio.value
    except Exception:
        return False
    finally:
        if dio is not None:
            try:
                dio.deinit()
            except Exception:
                pass


def _flash_boot_cyan():
    """Briefly signal Dev/Safe Mode on the NeoPixel before code.py takes over."""
    if NEOPIXEL_PIN is None:
        return
    try:
        import neopixel
    except ImportError:
        return

    px = None
    try:
        px = neopixel.NeoPixel(NEOPIXEL_PIN, 1, brightness=0.35, auto_write=True)
        px[0] = (0, 255, 255)
        time.sleep(0.15)
    except Exception:
        pass
    finally:
        if px is not None:
            try:
                px.deinit()
            except Exception:
                pass


# 1. Detect Dev/Safe Mode if GP0 (outer header pin) or GP24 is held to GND at plug-in.
dev_mode = _is_pin_held_low("GP0") or _is_pin_held_low("GP24")

if microcontroller is not None:
    try:
        flag = 1 if dev_mode else 0
        if microcontroller.nvm[0] != flag:
            microcontroller.nvm[0] = flag
    except Exception:
        pass

if dev_mode:
    _flash_boot_cyan()
else:
    # Host writes save.json / updates directly onto KAREL USB: prevent endless auto-reload loops.
    try:
        import supervisor
        supervisor.runtime.autoreload = False
    except Exception:
        pass

# 2. Enable USB CDC Console (REPL) and Data Serial, and explicitly DISABLE USB HID.
#    No simulated keyboard / Win+R injection: the stick is strictly USB storage + LED serial.
usb_cdc.enable(console=True, data=True)
usb_hid.disable()

# 3. Label USB Mass Storage volume as KAREL and keep CircuitPython read-only
#    so the host PC has full read/write access to save.json without corruption.
try:
    mount = storage.getmount("/")
    if mount.label != "KAREL":
        storage.remount("/", readonly=False)
        mount.label = "KAREL"
except Exception:
    pass
finally:
    try:
        storage.remount("/", readonly=True)
    except Exception:
        pass
