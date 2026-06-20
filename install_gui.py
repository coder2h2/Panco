#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import tkinter as tk
from tkinter import messagebox

class PancoInstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Panco Interpreter Installer")
        self.root.geometry("450x300")
        self.root.resizable(False, False)
        
        # Color Scheme (Premium clean aesthetic)
        self.bg_color = "#1e1e2e"
        self.fg_color = "#cdd6f4"
        self.accent_color = "#89b4fa"
        self.btn_bg = "#313244"
        
        self.root.configure(bg=self.bg_color)
        
        # Header Label
        self.title_label = tk.Label(
            self.root, 
            text="Panco Interpreter", 
            font=("Helvetica", 18, "bold"), 
            bg=self.bg_color, 
            fg=self.accent_color
        )
        self.title_label.pack(pady=(20, 5))
        
        self.subtitle_label = tk.Label(
            self.root, 
            text="Graphical Setup Installer", 
            font=("Helvetica", 10, "italic"), 
            bg=self.bg_color, 
            fg=self.fg_color
        )
        self.subtitle_label.pack(pady=(0, 20))
        
        # Action Buttons
        self.btn_local = tk.Button(
            self.root, 
            text="Install User-Local (~/.panco)", 
            command=self.install_local,
            font=("Helvetica", 11),
            bg=self.btn_bg,
            fg=self.fg_color,
            activebackground=self.accent_color,
            activeforeground=self.bg_color,
            relief="flat",
            width=30,
            height=2
        )
        self.btn_local.pack(pady=10)
        
        self.btn_global = tk.Button(
            self.root, 
            text="Install System-Wide (/opt/panco)", 
            command=self.install_global,
            font=("Helvetica", 11),
            bg=self.btn_bg,
            fg=self.fg_color,
            activebackground=self.accent_color,
            activeforeground=self.bg_color,
            relief="flat",
            width=30,
            height=2
        )
        self.btn_global.pack(pady=10)
        
        # Status footer
        self.status_label = tk.Label(
            self.root, 
            text="Ready to install.", 
            font=("Helvetica", 9), 
            bg=self.bg_color, 
            fg="#a6adc8"
        )
        self.status_label.pack(side="bottom", pady=15)

    def install_local(self):
        self.status_label.config(text="Installing user-local...")
        self.root.update()
        
        panco_dir = os.path.expanduser("~/.panco")
        bin_dir = os.path.expanduser("~/.local/bin")
        
        try:
            self.copy_files(panco_dir, bin_dir)
            messagebox.showinfo(
                "Success", 
                f"Panco successfully installed to:\n{panco_dir}\n\nExecutable symlink created at:\n{bin_dir}/delta\n\nEnsure {bin_dir} is in your PATH."
            )
            self.status_label.config(text="Installation completed successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to install: {str(e)}")
            self.status_label.config(text="Installation failed.")
            
    def install_global(self):
        # Global install requires root privileges
        if os.geteuid() != 0:
            # Rerun installer with sudo
            self.status_label.config(text="Requesting root privileges...")
            self.root.update()
            try:
                subprocess.run(["sudo", sys.executable] + sys.argv, check=True)
                sys.exit(0)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to acquire root privileges: {str(e)}")
                self.status_label.config(text="Acquisition of root privileges failed.")
                return

        panco_dir = "/opt/panco"
        bin_dir = "/usr/local/bin"
        
        try:
            self.copy_files(panco_dir, bin_dir)
            messagebox.showinfo(
                "Success", 
                f"Panco successfully installed system-wide to:\n{panco_dir}\n\nExecutable symlink created at:\n{bin_dir}/delta"
            )
            self.status_label.config(text="Global installation completed successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to install globally: {str(e)}")
            self.status_label.config(text="Global installation failed.")

    def copy_files(self, panco_dir, bin_dir):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Create directories
        os.makedirs(panco_dir, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)
        
        # Copy files
        src_panco = os.path.join(script_dir, "panco.py")
        src_interpreter = os.path.join(script_dir, "interpreter")
        
        dest_panco = os.path.join(panco_dir, "panco.py")
        dest_interpreter = os.path.join(panco_dir, "interpreter")
        
        shutil.copy2(src_panco, dest_panco)
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
    # Standard Tkinter application setup
    root = tk.Tk()
    app = PancoInstallerApp(root)
    root.mainloop()
