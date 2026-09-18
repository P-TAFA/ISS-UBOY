import sqlite3
import os
import tkinter as tk
from tkinterweb import HtmlFrame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "c2_queue.db")

current_selected_id = None
last_loaded_count = -1

def init_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_url TEXT NOT NULL,
                target_selector TEXT DEFAULT 'FULL_PAGE',
                status TEXT DEFAULT 'pending',
                response_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[!] DB Init Error: {e}")

def load_completed_jobs():
    global current_selected_id, last_loaded_count
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Pull ONLY completed jobs, newest finishes at the top
        cursor.execute("SELECT id, target_url, response_data FROM jobs WHERE status = 'completed' ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()

        if len(rows) != last_loaded_count:
            last_loaded_count = len(rows)
            
            selected_indices = job_listbox.curselection()
            selected_id_str = None
            if selected_indices:
                sel_text = job_listbox.get(selected_indices[0])
                if "ID:" in sel_text:
                    selected_id_str = sel_text.split("ID:")[1].split("|")[0].strip()

            job_listbox.delete(0, tk.END)
            
            if not rows:
                job_listbox.insert(tk.END, "Waiting for worker to complete jobs...")
            else:
                for row in rows:
                    job_id, url, _ = row
                    display_text = f"[COMPLETED] ID: {job_id} | {url}"
                    job_listbox.insert(tk.END, display_text)
                    
                    if selected_id_str and str(job_id) == str(selected_id_str):
                        idx = job_listbox.size() - 1
                        job_listbox.selection_set(idx)

    except Exception as e:
        print(f"[!] Polling error: {e}")
    
    # Check for new worker completions every 1 second
    root.after(1000, load_completed_jobs)

def view_selected_snapshot(event):
    global current_selected_id
    selection = job_listbox.curselection()
    if not selection:
        return
    
    selected_text = job_listbox.get(selection[0])
    if "ID:" not in selected_text:
        return
        
    try:
        id_part = selected_text.split("ID:")[1]
        job_id = id_part.split("|")[0].strip()
        current_selected_id = job_id
    except Exception:
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT response_data FROM jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    conn.close()

    if job and job[0]:
        # Instantly render the completed worker HTML visually
        browser_frame.load_html(job[0])
    else:
        browser_frame.load_html("<h3>Error: No response data found for this job.</h3>")

# --- Build GUI ---
root = tk.Tk()
root.title("C2 Completed Worker Stream & Snapshot Viewer")
root.geometry("1100x750")
root.config(bg="#2b2b2b")

title_label = tk.Label(root, text="Live Completed Worker Snapshots", fg="white", bg="#2b2b2b", font=("Arial", 14, "bold"))
title_label.pack(pady=8)

top_frame = tk.Frame(root, bg="#2b2b2b")
top_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

left_container = tk.Frame(top_frame, bg="#2b2b2b")
left_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

tk.Label(left_container, text="Completed Jobs Stream:", fg="#aaaaaa", bg="#2b2b2b", font=("Arial", 9, "bold")).pack(anchor="w")

list_scroll = tk.Scrollbar(left_container)
list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

job_listbox = tk.Listbox(left_container, width=45, height=35, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 8), yscrollcommand=list_scroll.set)
job_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
list_scroll.config(command=job_listbox.yview)
job_listbox.bind("<<ListboxSelect>>", view_selected_snapshot)

right_container = tk.Frame(top_frame, bg="#2b2b2b")
right_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))

tk.Label(right_container, text="Rendered Website Visual Snapshot:", fg="#aaaaaa", bg="#2b2b2b", font=("Arial", 9, "bold")).pack(anchor="w")

browser_frame = HtmlFrame(right_container, horizontal_scrollbar="auto")
browser_frame.pack(fill=tk.BOTH, expand=True, pady=3)
browser_frame.load_html("<h2>Select a completed job from the stream to view its visual snapshot.</h2>")

btn_frame = tk.Frame(root, bg="#2b2b2b")
btn_frame.pack(pady=10)

refresh_btn = tk.Button(btn_frame, text="🔄 Force Refresh", command=load_completed_jobs, bg="#0275d8", fg="white", font=("Arial", 10, "bold"), padx=12, pady=5)
refresh_btn.pack()

init_db()
root.after(1000, load_completed_jobs)

root.mainloop()