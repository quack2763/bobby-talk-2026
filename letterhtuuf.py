from datetime import datetime
from socket import *
import threading
import base64
import io
import wave
import queue

from customtkinter import *
from PIL import Image

import sounddevice as sd
import numpy as np


class MainWindow(CTk):
    def __init__(self):
        super().__init__()

        self.title("Chat App")
        self.geometry("900x600")

        self.incoming = queue.Queue()
        self.username = "Me"

        self.recording = False
        self.audio_chunks = []
        self.stream = None
        self.sample_rate = 44100

        self.message_widgets = []

        self.themes = {
            "Dark": {"bg": "#0f0f10", "mine": "#2b5278", "other": "#1e1e1e", "text": "#ffffff"},
            "Light": {"bg": "#f5f5f5", "mine": "#3B8ED0", "other": "#e0e0e0", "text": "#000000"},
            "Green": {"bg": "#0e2b1a", "mine": "#2FA572", "other": "#204F3A", "text": "#ffffff"},
            "Purple": {"bg": "#1a0e2b", "mine": "#8A2BE2", "other": "#3a2050", "text": "#ffffff"}
        }

        self.set_theme("Dark")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = CTkFrame(self, width=200)
        self.sidebar.grid(row=0, column=0, sticky="ns")

        self.name_entry = CTkEntry(self.sidebar, placeholder_text="Your name")
        self.name_entry.pack(pady=20, padx=10)

        self.theme_menu = CTkOptionMenu(self.sidebar, values=list(self.themes.keys()), command=self.set_theme)
        self.theme_menu.pack(pady=10, padx=10)

        self.chat_frame = CTkScrollableFrame(self)
        self.chat_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.bottom = CTkFrame(self)
        self.bottom.grid(row=1, column=1, sticky="ew", padx=10, pady=10)
        self.bottom.grid_columnconfigure(0, weight=1)

        self.input = CTkEntry(self.bottom)
        self.input.grid(row=0, column=0, sticky="ew", padx=5)
        self.input.bind("<Return>", lambda e: self.send_text())

        self.voice_btn = CTkButton(self.bottom, text="🎙", width=40, command=self.toggle_voice)
        self.voice_btn.grid(row=0, column=1, padx=5)

        self.img_btn = CTkButton(self.bottom, text="🖼", width=40, command=self.send_image)
        self.img_btn.grid(row=0, column=2, padx=5)

        self.send_btn = CTkButton(self.bottom, text="▶", width=40, command=self.send_text)
        self.send_btn.grid(row=0, column=3, padx=5)

        try:
            self.sock = socket(AF_INET, SOCK_STREAM)
            self.sock.connect(("localhost", 8080))
            threading.Thread(target=self.recv_loop, daemon=True).start()
        except:
            self.add_message("System", "No connection", False)

        self.after(50, self.poll)

    def set_theme(self, theme):
        t = self.themes[theme]

        self.bg = t["bg"]
        self.mine = t["mine"]
        self.other = t["other"]
        self.text = t["text"]

        self.configure(fg_color=self.bg)

        if hasattr(self, "chat_frame"):
            self.chat_frame.configure(fg_color=self.bg)
            self.sidebar.configure(fg_color=self.bg)
            self.bottom.configure(fg_color=self.bg)

            self.input.configure(fg_color=self.other, text_color=self.text)
            self.name_entry.configure(fg_color=self.other, text_color=self.text)
            self.theme_menu.configure(fg_color=self.other)

            self.voice_btn.configure(fg_color=self.mine)
            self.img_btn.configure(fg_color=self.mine)
            self.send_btn.configure(fg_color=self.mine)

            for bubble, label, meta, is_me in self.message_widgets:
                bubble.configure(fg_color=self.mine if is_me else self.other)
                if label:
                    label.configure(text_color=self.text)
                meta.configure(text_color=self.text)

    def time(self):
        return datetime.now().strftime("%H:%M")

    def add_message(self, author, text, is_me=True):
        row = CTkFrame(self.chat_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)

        container = CTkFrame(row, fg_color="transparent")
        container.pack(anchor="e" if is_me else "w", padx=10)

        bubble = CTkFrame(container, fg_color=self.mine if is_me else self.other, corner_radius=15)
        bubble.pack()

        label = CTkLabel(bubble, text=text, text_color=self.text, wraplength=400)
        label.pack(padx=10, pady=5)

        meta = CTkLabel(container, text=f"{author} • {self.time()}", font=("Arial", 9), text_color=self.text)
        meta.pack(anchor="e")

        self.message_widgets.append((bubble, label, meta, is_me))
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    def add_image(self, data, is_me):
        img = Image.open(io.BytesIO(data))
        img.thumbnail((250, 250))

        row = CTkFrame(self.chat_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)

        container = CTkFrame(row, fg_color="transparent")
        container.pack(anchor="e" if is_me else "w", padx=10)

        bubble = CTkFrame(container, fg_color=self.mine if is_me else self.other, corner_radius=15)
        bubble.pack()

        ctk_img = CTkImage(light_image=img, size=img.size)
        lbl = CTkLabel(bubble, image=ctk_img, text="")
        lbl.image = ctk_img
        lbl.pack(padx=6, pady=6)

        meta = CTkLabel(container, text=self.time(), font=("Arial", 9), text_color=self.text)
        meta.pack(anchor="e" if is_me else "w", padx=5)

        self.message_widgets.append((bubble, None, meta, is_me))
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    def add_voice(self, data, is_me):
        row = CTkFrame(self.chat_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)

        container = CTkFrame(row, fg_color="transparent")
        container.pack(anchor="e" if is_me else "w", padx=10)

        bubble = CTkFrame(container, fg_color=self.mine if is_me else self.other, corner_radius=15)
        bubble.pack()

        CTkLabel(bubble, text="🎤 Voice message", text_color=self.text).pack(padx=10, pady=(8, 2))

        CTkButton(
            bubble,
            text="▶ Play",
            width=80,
            command=lambda: self.play(data)
        ).pack(pady=(0, 8))

        meta = CTkLabel(container, text=self.time(), font=("Arial", 9), text_color=self.text)
        meta.pack(anchor="e" if is_me else "w", padx=5)

        self.message_widgets.append((bubble, None, meta, is_me))
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    def send_text(self):
        msg = self.input.get().strip()
        if not msg:
            return

        self.username = self.name_entry.get() if self.name_entry.get() else "Me"

        self.add_message(self.username, msg, True)

        try:
            self.sock.sendall(f"TEXT@{self.username}@{msg}\n".encode())
        except:
            pass

        self.input.delete(0, END)

    def send_image(self):
        from tkinter import filedialog

        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if not path:
            return

        with open(path, "rb") as f:
            data = f.read()

        self.add_image(data, True)

        try:
            self.sock.sendall(f"IMG@{self.username}@{base64.b64encode(data).decode()}\n".encode())
        except:
            pass

    def toggle_voice(self):
        if not self.recording:
            self.record()
        else:
            self.stop()

    def record(self):
        self.recording = True
        self.audio_chunks = []
        self.voice_btn.configure(text="■")

        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            callback=self.cb
        )
        self.stream.start()

    def cb(self, indata, frames, time, status):
        self.audio_chunks.append(indata.copy())

    def stop(self):
        self.recording = False
        self.voice_btn.configure(text="🎙")

        self.stream.stop()
        self.stream.close()

        audio = np.concatenate(self.audio_chunks)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio.tobytes())

        data = buf.getvalue()

        self.add_voice(data, True)

        try:
            self.sock.sendall(f"VOICE@{self.username}@{base64.b64encode(data).decode()}\n".encode())
        except:
            pass

    def play(self, data):
        def run():
            with wave.open(io.BytesIO(data), "rb") as wf:
                audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
                sd.play(audio, wf.getframerate())
                sd.wait()

        threading.Thread(target=run, daemon=True).start()

    def recv_loop(self):
        buf = ""
        while True:
            try:
                data = self.sock.recv(4096).decode(errors="ignore")
                if not data:
                    break
                buf += data

                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    self.handle(line)
            except:
                break

    def handle(self, line):
        parts = line.split("@", 2)
        if len(parts) < 3:
            return

        t, user, data = parts

        if user == self.username:
            return

        if t == "TEXT":
            self.incoming.put(("text", user, data))
        elif t == "IMG":
            self.incoming.put(("img", user, base64.b64decode(data)))
        elif t == "VOICE":
            self.incoming.put(("voice", user, base64.b64decode(data)))

    def poll(self):
        try:
            while True:
                item = self.incoming.get_nowait()

                if item[0] == "text":
                    self.add_message(item[1], item[2], False)
                elif item[0] == "img":
                    self.add_image(item[2], False)
                elif item[0] == "voice":
                    self.add_voice(item[2], False)

        except queue.Empty:
            pass

        self.after(50, self.poll)


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()