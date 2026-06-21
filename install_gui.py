#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import ctypes

class PancoX11Installer:
    def __init__(self):
        try:
            self.x11 = ctypes.CDLL("libX11.so.6")
        except Exception:
            try:
                self.x11 = ctypes.CDLL("libX11.so")
            except Exception:
                print("Error: Could not load libX11.so. X11 environment is required for graphical setup.", file=sys.stderr)
                sys.exit(1)

        self.x11.XOpenDisplay.restype = ctypes.c_void_p
        self.x11.XDefaultRootWindow.restype = ctypes.c_ulong
        self.x11.XCreateSimpleWindow.restype = ctypes.c_ulong

        self.display = self.x11.XOpenDisplay(None)
        if not self.display:
            print("Error: Could not open X11 display. Ensure DISPLAY environment variable is configured.", file=sys.stderr)
            sys.exit(1)

        self.root = self.x11.XDefaultRootWindow(self.display)
        # Create a simple window (450x300, white background 0xFFFFFF)
        self.window = self.x11.XCreateSimpleWindow(self.display, self.root, 100, 100, 450, 300, 1, 0, 0xFFFFFF)
        
        self.x11.XStoreName(self.display, self.window, b"Panco Interpreter Installer")
        
        # Select ExposureMask (1<<15), ButtonPressMask (1<<2)
        self.x11.XSelectInput(self.display, self.window, (1<<15) | (1<<2))
        self.x11.XMapWindow(self.display, self.window)
        
        self.gc = self.x11.XCreateGC(self.display, self.window, 0, None)
        self.status = "Ready to install."

        # Setup buttons
        self.btn_local = {"text": "Install User-Local (~/.pco)", "x": 80, "y": 100, "w": 290, "h": 40}
        self.btn_global = {"text": "Install System-Wide (/opt/panco)", "x": 80, "y": 160, "w": 290, "h": 40}

    def draw(self):
        # Clear background (white rectangle)
        self.x11.XSetForeground(self.display, self.gc, 0xFFFFFF)
        self.x11.XFillRectangle(self.display, self.window, self.gc, 0, 0, 450, 300)
        
        # Set drawing color to black
        self.x11.XSetForeground(self.display, self.gc, 0x000000)
        
        # Draw Title
        title = b"Panco Interpreter Graphical Setup"
        self.x11.XDrawString(self.display, self.window, self.gc, 80, 50, title, len(title))
        
        # Draw Buttons
        for btn in (self.btn_local, self.btn_global):
            self.x11.XDrawRectangle(self.display, self.window, self.gc, btn["x"], btn["y"], btn["w"], btn["h"])
            txt = btn["text"].encode("utf-8")
            self.x11.XDrawString(self.display, self.window, self.gc, btn["x"] + 20, btn["y"] + 25, txt, len(txt))
            
        # Draw Status
        status_bytes = self.status.encode("utf-8")
        self.x11.XDrawString(self.display, self.window, self.gc, 80, 240, status_bytes, len(status_bytes))
        self.x11.XFlush(self.display)

    def run(self):
        class XEvent(ctypes.Structure):
            _fields_ = [("type", ctypes.c_int), ("pad", ctypes.c_byte * 188)]

        class XButtonEvent(ctypes.Structure):
            _fields_ = [
                ("type", ctypes.c_int),
                ("serial", ctypes.c_ulong),
                ("send_event", ctypes.c_int),
                ("display", ctypes.c_void_p),
                ("window", ctypes.c_ulong),
                ("root", ctypes.c_ulong),
                ("subwindow", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("x", ctypes.c_int),
                ("y", ctypes.c_int),
            ]

        event = XEvent()
        self.x11.XFlush(self.display)

        while True:
            self.x11.XNextEvent(self.display, ctypes.byref(event))
            
            if event.type == 12: # Expose
                self.draw()
            elif event.type == 4: # ButtonPress
                click = ctypes.cast(ctypes.byref(event), ctypes.POINTER(XButtonEvent)).contents
                
                # Check Local Button
                if (self.btn_local["x"] <= click.x <= self.btn_local["x"] + self.btn_local["w"] and 
                    self.btn_local["y"] <= click.y <= self.btn_local["y"] + self.btn_local["h"]):
                    self.install_local()
                    self.draw()
                    
                # Check Global Button
                elif (self.btn_global["x"] <= click.x <= self.btn_global["x"] + self.btn_global["w"] and 
                      self.btn_global["y"] <= click.y <= self.btn_global["y"] + self.btn_global["h"]):
                    self.install_global()
                    self.draw()

    def install_local(self):
        self.status = "Installing user-local..."
        self.draw()
        
        panco_dir = os.path.expanduser("~/.pco")
        bin_dir = os.path.expanduser("~/.local/bin")
        
        try:
            self.copy_files(panco_dir, bin_dir)
            self.status = "User-Local install successful!"
        except Exception as e:
            self.status = f"Install failed: {str(e)[:30]}"
            
    def install_global(self):
        # Global install requires root privileges
        if os.geteuid() != 0:
            self.status = "Acquiring root privileges..."
            self.draw()
            try:
                subprocess.run(["sudo", sys.executable] + sys.argv, check=True)
                sys.exit(0)
            except Exception as e:
                self.status = f"Root privilege acquisition failed: {str(e)[:30]}"
                return

        panco_dir = "/opt/panco"
        bin_dir = "/usr/local/bin"
        
        try:
            self.copy_files(panco_dir, bin_dir)
            self.status = "Global install successful!"
        except Exception as e:
            self.status = f"Global install failed: {str(e)[:30]}"

    def copy_files(self, panco_dir, bin_dir):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Create directories
        os.makedirs(panco_dir, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)
        
        # Copy files
        src_panco = os.path.join(script_dir, "panco.py")
        src_interpreter = os.path.join(script_dir, "interpreter")
        src_install_gui = os.path.join(script_dir, "install_gui.py")
        
        dest_panco = os.path.join(panco_dir, "panco.py")
        dest_interpreter = os.path.join(panco_dir, "interpreter")
        dest_install_gui = os.path.join(panco_dir, "install_gui.py")
        
        shutil.copy2(src_panco, dest_panco)
        shutil.copy2(src_install_gui, dest_install_gui)
        os.chmod(dest_panco, 0o755)
        
        if os.path.exists(dest_interpreter):
            shutil.rmtree(dest_interpreter)
        shutil.copytree(src_interpreter, dest_interpreter)
        
        # Create Symlink
        symlink_path = os.path.join(bin_dir, "delta")
        if os.path.lexists(symlink_path):
            os.remove(symlink_path)
        os.symlink(dest_panco, symlink_path)

if __name__ == "__main__":
    app = PancoX11Installer()
    app.run()
