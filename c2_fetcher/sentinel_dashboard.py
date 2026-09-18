import sqlite3
import csv
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import json
import time
from bs4 import BeautifulSoup

DB_PATH = "c2_queue.db"
RULES_PATH = "keyword_rules.json"

def setup_environment():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_url TEXT,
            response_data TEXT,
            status TEXT DEFAULT 'completed'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL UNIQUE,
            url TEXT,
            title TEXT,
            h1 TEXT,
            link_count INTEGER,
            word_count INTEGER,
            category TEXT DEFAULT 'Unknown',
            match_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

    if not os.path.exists(RULES_PATH):
        default_rules = {
            "E-Commerce & Retail": ["add to cart", "proceed to checkout", "shipping and returns", "customer reviews"],
            "News & Digital Media": ["breaking news", "latest headlines", "read full article", "subscribe"],
            "Corporate SaaS": ["book a demo", "request a quote", "case studies", "pricing plans"],
            "High-Risk: Phishing": ["verify your account", "urgent action required", "unusual login attempt", "claim your prize"],
            "High-Risk: Controlled Substances": ["fentanyl", "fent", "oxycodone", "oxy", "research-chemical", "rc-vendor", "synthesis", "analogue"],
            "High-Risk: Dark Logistics": ["stealth shipping", "vacuum sealed", "mylar", "reship", "no-sign"]
        }
        with open(RULES_PATH, "w", encoding="utf-8") as f:
            json.dump(default_rules, f, indent=4)

def get_keyword_rules():
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def categorize_url_and_text(url, text, rules):
    combined_content = f"{url} {text}".lower()
    category_scores = {}
    
    for category, keywords in rules.items():
        score = sum(1 for kw in keywords if kw.lower() in combined_content)
        if score > 0:
            category_scores[category] = score
            
    if category_scores:
        primary_category = max(category_scores, key=category_scores.get)
        hits = category_scores[primary_category]
        
        for kw in rules.get(primary_category, []):
            if kw.lower() in url.lower():
                hits += 2 
                
        if "High-Risk" in primary_category:
            if hits >= 2:
                return f"🚨 {primary_category}", f"Strong match: {hits} indicators (URL/Text hit)"
            else:
                return f"⚠️ Suspicious ({primary_category})", f"Weak match: {hits} indicator"
                
        return primary_category, f"Matched {hits} indicators"
    
    return "Uncategorized", "No defining keywords found"

def extract_page_data(target_url, raw_html, rules):
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
        
    title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"
    h1_tag = soup.find("h1")
    h1_text = h1_tag.get_text().strip() if h1_tag else "No H1"
    links = [a.get("href") for a in soup.find_all("a", href=True)]
    visible_text = soup.get_text(separator=" ", strip=True)
    word_count = len(visible_text.split())
    
    category, reason = categorize_url_and_text(target_url, visible_text, rules)
    
    return {
        "title": title[:50],
        "h1": h1_text[:50],
        "link_count": len(links),
        "word_count": word_count,
        "category": category,
        "match_reason": reason
    }

def process_unanalysed_jobs(progress_callback=None, reanalyse_all=False):
    rules = get_keyword_rules()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if reanalyse_all:
        cursor.execute("DELETE FROM analysis_results")
        conn.commit()
        cursor.execute("SELECT j.id, j.target_url, j.response_data FROM jobs j WHERE j.response_data IS NOT NULL")
    else:
        cursor.execute("""
            SELECT j.id, j.target_url, j.response_data 
            FROM jobs j
            WHERE j.response_data IS NOT NULL 
              AND j.id NOT IN (SELECT job_id FROM analysis_results)
        """)
        
    unprocessed = cursor.fetchall()
    total_jobs = len(unprocessed)
    
    if total_jobs == 0:
        conn.close()
        return 0

    processed_count = 0
    total_time_spent = 0.0

    for idx, (job_id, target_url, raw_html) in enumerate(unprocessed):
        item_start = time.perf_counter()
        
        if raw_html:
            try:
                data = extract_page_data(target_url, raw_html, rules)
                cursor.execute("""
                    INSERT OR REPLACE INTO analysis_results 
                    (job_id, url, title, h1, link_count, word_count, category, match_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (job_id, target_url, data["title"], data["h1"], data["link_count"], data["word_count"], data["category"], data["match_reason"]))
                processed_count += 1
            except Exception as e:
                print(f"Failed to analyse job {job_id}: {e}")
        
        item_duration = time.perf_counter() - item_start
        total_time_spent += item_duration
        avg_time = total_time_spent / (idx + 1)
        
        if progress_callback:
            progress_callback(idx + 1, total_jobs, avg_time)
            
    conn.commit()
    conn.close()
    return processed_count

def get_all_results():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT job_id, url, title, category, match_reason, link_count, word_count, created_at 
        FROM analysis_results 
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_job_detail(job_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT j.id, j.target_url, j.response_data, ar.title, ar.h1, ar.category, ar.match_reason, ar.link_count, ar.word_count, ar.created_at
        FROM jobs j
        LEFT JOIN analysis_results ar ON j.id = ar.job_id
        WHERE j.id = ?
    """, (job_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def export_to_csv(filepath):
    rows = get_all_results()
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Job ID", "URL", "Page Title", "Category Flag", "Trigger Reason", "Link Count", "Word Count", "Analysed At"])
        writer.writerows(rows)

class AnalyserGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Data Analyser & Site Inspector Agent")
        self.root.geometry("1150x700")
        self.root.minsize(900, 550)

        self.reanalyse_var = tk.BooleanVar(value=False)

        self.notebook = ttk.Notebook(root)
        self.tab_results = ttk.Frame(self.notebook)
        self.tab_rules = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_results, text="Triage Results")
        self.notebook.add(self.tab_rules, text="Edit Keywords")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self._setup_results_tab()
        self._setup_rules_tab()
        self.load_table_data()

    def _setup_results_tab(self):
        top_frame = ttk.Frame(self.tab_results, padding=10)
        top_frame.pack(fill=tk.X)

        self.btn_run = ttk.Button(top_frame, text="▶ Run Analysis", command=self.start_analysis_thread)
        self.btn_run.pack(side=tk.LEFT, padx=4)

        self.chk_reanalyse = ttk.Checkbutton(top_frame, text="Re-triage all", variable=self.reanalyse_var)
        self.chk_reanalyse.pack(side=tk.LEFT, padx=8)

        self.btn_refresh = ttk.Button(top_frame, text="🔄 Refresh", command=self.load_table_data)
        self.btn_refresh.pack(side=tk.LEFT, padx=4)

        self.btn_import = ttk.Button(top_frame, text="📥 Import Dataset CSV", command=self.import_dataset_file)
        self.btn_import.pack(side=tk.LEFT, padx=10)

        self.btn_inspect = ttk.Button(top_frame, text="🔍 Inspect Selected Site", command=self.inspect_selected_row)
        self.btn_inspect.pack(side=tk.LEFT, padx=4)

        self.btn_download = ttk.Button(top_frame, text="📥 Download CSV", command=self.download_csv)
        self.btn_download.pack(side=tk.RIGHT, padx=4)

        metrics_frame = ttk.Frame(self.tab_results, padding=(10, 0, 10, 8))
        metrics_frame.pack(fill=tk.X)

        self.progress_bar = ttk.Progressbar(metrics_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 4))

        info_subframe = ttk.Frame(metrics_frame)
        info_subframe.pack(fill=tk.X)

        self.lbl_percentage = ttk.Label(info_subframe, text="Progress: 0%", font=("Arial", 9, "bold"))
        self.lbl_percentage.pack(side=tk.LEFT)

        self.lbl_timing = ttk.Label(info_subframe, text="Speed: -- ms/site | Status: Ready (Double-click any row to inspect)", font=("Arial", 9, "italic"))
        self.lbl_timing.pack(side=tk.RIGHT)

        table_frame = ttk.Frame(self.tab_results, padding=10)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("job_id", "url", "title", "category", "reason", "links", "words")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        self.tree.heading("job_id", text="ID")
        self.tree.heading("url", text="URL")
        self.tree.heading("title", text="Page Title")
        self.tree.heading("category", text="Category Flag")
        self.tree.heading("reason", text="Trigger Reason")
        self.tree.heading("links", text="Links")
        self.tree.heading("words", text="Words")

        self.tree.column("job_id", width=45, anchor=tk.CENTER)
        self.tree.column("url", width=220, anchor=tk.W)
        self.tree.column("title", width=160, anchor=tk.W)
        self.tree.column("category", width=140, anchor=tk.CENTER)
        self.tree.column("reason", width=200, anchor=tk.W)
        self.tree.column("links", width=50, anchor=tk.CENTER)
        self.tree.column("words", width=50, anchor=tk.CENTER)

        self.tree.bind("<Double-1>", lambda event: self.inspect_selected_row())

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _setup_rules_tab(self):
        ctrl_frame = ttk.Frame(self.tab_rules, padding=10)
        ctrl_frame.pack(fill=tk.X)
        
        ttk.Label(ctrl_frame, text="Define heuristic keywords using JSON format:").pack(side=tk.LEFT)
        btn_save = ttk.Button(ctrl_frame, text="💾 Save Rules", command=self.save_rules)
        btn_save.pack(side=tk.RIGHT)

        text_frame = ttk.Frame(self.tab_rules, padding=10)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text_rules = tk.Text(text_frame, wrap=tk.WORD, font=("Courier", 10))
        self.text_rules.pack(fill=tk.BOTH, expand=True)
        
        rules = get_keyword_rules()
        self.text_rules.insert(tk.END, json.dumps(rules, indent=4))

    def save_rules(self):
        try:
            raw_json = self.text_rules.get("1.0", tk.END)
            parsed_json = json.loads(raw_json)
            with open(RULES_PATH, "w", encoding="utf-8") as f:
                json.dump(parsed_json, f, indent=4)
            messagebox.showinfo("Success", "Keyword rules updated successfully.")
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON Error", f"Invalid JSON format:\n\n{e}")

    def import_dataset_file(self):
        filepath = filedialog.askopenfilename(
            title="Select Dataset CSV",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not filepath:
            return

        self.lbl_timing.config(text="Status: Importing CSV into queue...")
        self.root.update_idletasks()

        def background_import():
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                injected = 0
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    reader = csv.DictReader(f)
                    for idx, row in enumerate(reader):
                        url = row.get("url", row.get("URL", f"http://dataset.local/site_{idx}"))
                        html_content = row.get("text", row.get("html", row.get("content", str(row))))
                        cursor.execute("""
                            INSERT INTO jobs (target_url, response_data, status)
                            VALUES (?, ?, 'completed')
                        """, (url, html_content))
                        injected += 1
                conn.commit()
                conn.close()
                self.root.after(0, lambda: messagebox.showinfo("Import Successful", f"Successfully imported {injected} records into the queue."))
                self.root.after(0, lambda: self.lbl_timing.config(text=f"Status: Imported {injected} sites ready for analysis."))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Import Failed", str(e)))

        threading.Thread(target=background_import, daemon=True).start()

    def inspect_selected_row(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select a website record from the table to inspect.")
            return

        item_values = self.tree.item(selected_items[0], "values")
        job_id = item_values[0]

        record = get_job_detail(job_id)
        if not record:
            messagebox.showerror("Error", "Could not retrieve details for this record.")
            return

        job_id, target_url, response_data, title, h1, category, match_reason, link_count, word_count, created_at = record

        # Create detailed popup window for individual site inspection
        top = tk.Toplevel(self.root)
        top.title(f"Site Inspector — Record #{job_id}")
        top.geometry("850x600")
        top.minsize(650, 450)

        # Metadata Header Frame
        header_frame = ttk.LabelFrame(top, text="Triage & Structural Metadata", padding=12)
        header_frame.pack(fill=tk.X, padx=12, pady=12)

        meta_info = [
            ("Target URL:", target_url),
            ("Category Flag:", category or "Uncategorized"),
            ("Trigger Reason:", match_reason or "N/A"),
            ("Page Title:", title or "N/A"),
            ("H1 Heading:", h1 or "N/A"),
            ("Metrics:", f"Word Count: {word_count} | Link Count: {link_count} | Analysed At: {created_at}")
        ]

        for idx, (label, val) in enumerate(meta_info):
            lbl_key = ttk.Label(header_frame, text=label, font=("Arial", 9, "bold"))
            lbl_key.grid(row=idx, column=0, sticky=tk.W, padx=4, pady=2)
            lbl_val = ttk.Label(header_frame, text=str(val), font=("Arial", 9))
            lbl_val.grid(row=idx, column=1, sticky=tk.W, padx=4, pady=2)

        # Raw Content / Text View Frame
        body_frame = ttk.LabelFrame(top, text="Raw Source Content & Payload", padding=12)
        body_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        txt_content = tk.Text(body_frame, wrap=tk.WORD, font=("Courier", 10), bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
        txt_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(body_frame, orient=tk.VERTICAL, command=txt_content.yview)
        txt_content.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        txt_content.insert(tk.END, response_data if response_data else "[No payload found]")
        txt_content.config(state=tk.DISABLED)

    def update_progress_ui(self, current, total, avg_time):
        percent = int((current / total) * 100)
        self.progress_bar['value'] = percent
        self.lbl_percentage.config(text=f"Progress: {percent}% ({current}/{total})")
        
        time_display = f"{avg_time * 1000:.1f}ms" if avg_time < 1.0 else f"{avg_time:.2f}s"
        est_rem = avg_time * (total - current)
        self.lbl_timing.config(text=f"Speed: {time_display}/site | Est. Remaining: {est_rem:.1f}s")
        self.root.update_idletasks()

    def start_analysis_thread(self):
        self.btn_run.config(state=tk.DISABLED)
        self.progress_bar['value'] = 0
        self.lbl_percentage.config(text="Progress: Starting...")
        self.lbl_timing.config(text="Status: Processing queue...")
        
        reanalyse = self.reanalyse_var.get()
        threading.Thread(target=self._run_analysis_worker, args=(reanalyse,), daemon=True).start()

    def _run_analysis_worker(self, reanalyse):
        count = process_unanalysed_jobs(
            progress_callback=lambda cur, tot, avg_t: self.root.after(0, self.update_progress_ui, cur, tot, avg_t),
            reanalyse_all=reanalyse
        )
        self.root.after(0, self._on_analysis_complete, count)

    def _on_analysis_complete(self, count):
        self.btn_run.config(state=tk.NORMAL)
        self.lbl_timing.config(text=f"Status: Completed {count} jobs")
        self.load_table_data()

    def load_table_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            records = get_all_results()
            for row in records:
                self.tree.insert("", tk.END, values=row[:-1])
        except Exception as e:
            self.lbl_timing.config(text=f"Error reading DB: {e}")

    def download_csv(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filepath:
            export_to_csv(filepath)

if __name__ == "__main__":
    setup_environment()
    root = tk.Tk()
    app = AnalyserGUI(root)
    root.mainloop()