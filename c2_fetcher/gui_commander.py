import sqlite3
import subprocess
import sys
import os
import tkinter as tk
from tkinter import messagebox, scrolledtext

DB_FILE = "c2_queue.db"
server_process = None
worker_process = None
snapshot_process = None
generator_process = None

# Get the absolute directory where this script is saved
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_url TEXT NOT NULL,
            target_selector TEXT DEFAULT 'h1',
            status TEXT DEFAULT 'pending',
            response_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def start_engines():
    global server_process, worker_process, snapshot_process, generator_process
    
    # 1. Start Mock Website Server
    if server_process is None or server_process.poll() is not None:
        try:
            path = os.path.join(BASE_DIR, "mock_site.py")
            server_process = subprocess.Popen([sys.executable, path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not start mock_site.py: {e}")
            return

    # 2. Start Background Worker
    if worker_process is None or worker_process.poll() is not None:
        try:
            path = os.path.join(BASE_DIR, "worker.py")
            worker_process = subprocess.Popen([sys.executable, path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not start worker.py: {e}")
            return

    # 3. Automatically launch Snapshot Viewer GUI
    if snapshot_process is None or snapshot_process.poll() is not None:
        try:
            path = os.path.join(BASE_DIR, "gui_snapshots.py")
            snapshot_process = subprocess.Popen([sys.executable, path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not start gui_snapshots.py: {e}")
            return

    # 4. Automatically launch Test URL Generator GUI
    if generator_process is None or generator_process.poll() is not None:
        try:
            path = os.path.join(BASE_DIR, "gui_generator.py")
            generator_process = subprocess.Popen([sys.executable, path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not start gui_generator.py: {e}")
            return

    engine_status_label.config(text="All Engines & UIs: RUNNING", fg="green")
    start_btn.config(state="disabled", bg="#555555")
    stop_btn.config(state="normal", bg="#d9534f")

def stop_engines():
    global server_process, worker_process, snapshot_process, generator_process
    
    if server_process and server_process.poll() is None:
        server_process.terminate()
        server_process = None

    if worker_process and worker_process.poll() is None:
        worker_process.terminate()
        worker_process = None

    if snapshot_process and snapshot_process.poll() is None:
        snapshot_process.terminate()
        snapshot_process = None

    if generator_process and generator_process.poll() is None:
        generator_process.terminate()
        generator_process = None

    engine_status_label.config(text="All Engines & UIs: STOPPED", fg="#ff4444")
    start_btn.config(state="normal", bg="#0275d8")
    stop_btn.config(state="disabled", bg="#555555")
    status_label.config(text="Status: All systems shut down.", fg="#aaaaaa")

def set_selector(preset):
    selector_entry.delete(0, tk.END)
    selector_entry.insert(0, preset)

def send_command():
    url = url_entry.get().strip()
    selector = selector_entry.get().strip()
    
    if not url:
        messagebox.showerror("Error", "Please enter a valid URL!")
        return
    if not selector:
        messagebox.showerror("Error", "Please enter a CSS selector!")
        return
    
    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO jobs (target_url, target_selector) VALUES (?, ?)", (url, selector))
    conn.commit()
    conn.close()
    
    status_label.config(text=f"Status: Command sent for {url} [Target: {selector}]", fg="#00ff00")
    url_entry.delete(0, tk.END)
    url_entry.insert(0, "http://localhost:8000")

def send_bulk_commands():
    raw_text = bulk_text.get("1.0", tk.END).strip()
    selector = selector_entry.get().strip()

    if not raw_text:
        messagebox.showerror("Error", "Please enter at least one URL in the bulk box!")
        return
    if not selector:
        messagebox.showerror("Error", "Please enter a CSS selector for the batch!")
        return

    urls = [line.strip() for line in raw_text.splitlines() if line.strip()]
    
    if not urls:
        messagebox.showerror("Error", "No valid URLs found.")
        return

    init_db()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    for url in urls:
        cursor.execute("INSERT INTO jobs (target_url, target_selector) VALUES (?, ?)", (url, selector))
        
    conn.commit()
    conn.close()
    
    status_label.config(text=f"Status: Queued {len(urls)} URLs with selector '{selector}'!", fg="#00ff00")
    bulk_text.delete("1.0", tk.END)

def poll_database():
    if os.path.exists(DB_FILE):
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT id, target_url, target_selector, status, response_data FROM jobs ORDER BY id DESC LIMIT 10")
            rows = cursor.fetchall()
            conn.close()

            results_box.config(state="normal")
            results_box.delete("1.0", tk.END)
            for row in rows:
                job_id, url, selector, status, data = row
                if len(str(data)) > 150:
                    data_preview = str(data)[:150] + " ... [truncated]"
                else:
                    data_preview = data
                    
                line = f"[ID: {job_id}] Status: {status.upper()}\nTarget: {url} | Selector: {selector}\nResult: {data_preview}\n" + "-"*52 + "\n"
                results_box.insert(tk.END, line)
            results_box.config(state="disabled")
        except Exception:
            pass
    
    root.after(1000, poll_database)

def on_closing():
    stop_engines()
    root.destroy()

# --- Build the Control Center Window ---
root = tk.Tk()
root.title("C2 Master Control Center")
root.geometry("560x870")
root.config(bg="#2b2b2b")
root.protocol("WM_DELETE_WINDOW", on_closing)

title_label = tk.Label(root, text="C2 Scraper Master Panel", fg="white", bg="#2b2b2b", font=("Arial", 14, "bold"))
title_label.pack(pady=8)

# Engine Section
btn_frame = tk.Frame(root, bg="#2b2b2b")
btn_frame.pack(pady=3)

start_btn = tk.Button(btn_frame, text="🚀 Start Engines", command=start_engines, bg="#0275d8", fg="white", font=("Arial", 10, "bold"), padx=8, pady=4)
start_btn.pack(side=tk.LEFT, padx=5)

stop_btn = tk.Button(btn_frame, text="🛑 Stop Engines", command=stop_engines, bg="#555555", fg="white", font=("Arial", 10, "bold"), padx=8, pady=4, state="disabled")
stop_btn.pack(side=tk.LEFT, padx=5)

engine_status_label = tk.Label(root, text="All Engines & UIs: STOPPED", fg="#ff4444", bg="#2b2b2b", font=("Arial", 9, "bold"))
engine_status_label.pack(pady=2)

tk.Label(root, text="----------------------------------------------------------------", fg="#666666", bg="#2b2b2b").pack(pady=2)

# Selector Section
selector_main_frame = tk.Frame(root, bg="#2b2b2b")
selector_main_frame.pack(pady=2)

tk.Label(selector_main_frame, text="Selector / Target:", fg="white", bg="#2b2b2b", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
selector_entry = tk.Entry(selector_main_frame, width=32, font=("Arial", 10))
selector_entry.insert(0, "h1")
selector_entry.pack(side=tk.LEFT, padx=5)

# Presets
preset_frame_1 = tk.Frame(root, bg="#2b2b2b")
preset_frame_1.pack(pady=3)
tk.Label(preset_frame_1, text="Layout:", fg="#aaaaaa", bg="#2b2b2b", font=("Arial", 9)).pack(side=tk.LEFT, padx=3)
tk.Button(preset_frame_1, text="FULL_PAGE", command=lambda: set_selector("FULL_PAGE"), bg="#444444", fg="white", font=("Arial", 8)).pack(side=tk.LEFT, padx=2)
tk.Button(preset_frame_1, text="h1", command=lambda: set_selector("h1"), bg="#444444", fg="white", font=("Arial", 8)).pack(side=tk.LEFT, padx=2)
tk.Button(preset_frame_1, text="h1, h2", command=lambda: set_selector("h1, h2"), bg="#444444", fg="white", font=("Arial", 8)).pack(side=tk.LEFT, padx=2)
tk.Button(preset_frame_1, text="p", command=lambda: set_selector("p"), bg="#444444", fg="white", font=("Arial", 8)).pack(side=tk.LEFT, padx=2)

preset_frame_2 = tk.Frame(root, bg="#2b2b2b")
preset_frame_2.pack(pady=3)
tk.Label(preset_frame_2, text="Elements:", fg="#aaaaaa", bg="#2b2b2b", font=("Arial", 9)).pack(side=tk.LEFT, padx=3)
tk.Button(preset_frame_2, text="a", command=lambda: set_selector("a"), bg="#444444", fg="white", font=("Arial", 8)).pack(side=tk.LEFT, padx=2)
tk.Button(preset_frame_2, text="img", command=lambda: set_selector("img"), bg="#444444", fg="white", font=("Arial", 8)).pack(side=tk.LEFT, padx=2)
tk.Button(preset_frame_2, text=".title", command=lambda: set_selector(".title"), bg="#444444", fg="white", font=("Arial", 8)).pack(side=tk.LEFT, padx=2)
tk.Button(preset_frame_2, text=".price", command=lambda: set_selector(".price"), bg="#444444", fg="white", font=("Arial", 8)).pack(side=tk.LEFT, padx=2)

# Single URL
url_label = tk.Label(root, text="Single Target URL:", fg="white", bg="#2b2b2b", font=("Arial", 9))
url_label.pack(anchor="w", padx=25, pady=(5, 0))

url_frame = tk.Frame(root, bg="#2b2b2b")
url_frame.pack(pady=2)

url_entry = tk.Entry(url_frame, width=38, font=("Arial", 10))
url_entry.insert(0, "http://localhost:8000")
url_entry.pack(side=tk.LEFT, padx=5)

fire_button = tk.Button(url_frame, text="🎯 Fire Single", command=send_command, bg="#5cb85c", fg="white", font=("Arial", 9, "bold"), padx=5, pady=2)
fire_button.pack(side=tk.LEFT)

# Bulk URLs
bulk_label = tk.Label(root, text="Bulk URLs (Paste one per line below):", fg="white", bg="#2b2b2b", font=("Arial", 9, "bold"))
bulk_label.pack(anchor="w", padx=25, pady=(5, 0))

bulk_text = scrolledtext.ScrolledText(root, width=60, height=4, bg="#1e1e1e", fg="white", font=("Consolas", 9))
bulk_text.pack(pady=3)

bulk_button = tk.Button(root, text="📦 Queue All Bulk URLs", command=send_bulk_commands, bg="#f0ad4e", fg="black", font=("Arial", 10, "bold"), padx=8, pady=4)
bulk_button.pack(pady=2)

status_label = tk.Label(root, text="Status: Ready", fg="#aaaaaa", bg="#2b2b2b", font=("Arial", 9))
status_label.pack(pady=2)

# Live Feed
feed_label = tk.Label(root, text="Live Database Feed (Recent Jobs):", fg="white", bg="#2b2b2b", font=("Arial", 10, "bold"))
feed_label.pack(anchor="w", padx=25, pady=(5, 0))

results_box = scrolledtext.ScrolledText(root, width=60, height=8, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 9))
results_box.pack(pady=3)
results_box.config(state="disabled")

root.after(1000, poll_database)
root.mainloop()