import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import json
import analyser_engine

class AnalyserGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Data Analyser & Triage Agent")
        self.root.geometry("1050x650")
        self.root.minsize(850, 500)

        self.reanalyse_var = tk.BooleanVar(value=False)

        # Tabbed Layout
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
        # Action Toolbar Frame
        top_frame = ttk.Frame(self.tab_results, padding=10)
        top_frame.pack(fill=tk.X)

        self.btn_run = ttk.Button(top_frame, text="▶ Run Analysis", command=self.start_analysis_thread)
        self.btn_run.pack(side=tk.LEFT, padx=4)

        self.chk_reanalyse = ttk.Checkbutton(top_frame, text="Re-triage all", variable=self.reanalyse_var)
        self.chk_reanalyse.pack(side=tk.LEFT, padx=8)

        self.btn_refresh = ttk.Button(top_frame, text="🔄 Refresh", command=self.load_table_data)
        self.btn_refresh.pack(side=tk.LEFT, padx=4)

        self.btn_download = ttk.Button(top_frame, text="📥 Download CSV", command=self.download_csv)
        self.btn_download.pack(side=tk.RIGHT, padx=4)

        # Metrics & Progress Bar Frame
        metrics_frame = ttk.Frame(self.tab_results, padding=(10, 0, 10, 8))
        metrics_frame.pack(fill=tk.X)

        self.progress_bar = ttk.Progressbar(metrics_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 4))

        # Status text indicators
        info_subframe = ttk.Frame(metrics_frame)
        info_subframe.pack(fill=tk.X)

        self.lbl_percentage = ttk.Label(info_subframe, text="Progress: 0%", font=("Arial", 9, "bold"))
        self.lbl_percentage.pack(side=tk.LEFT)

        self.lbl_timing = ttk.Label(info_subframe, text="Speed: -- ms/site | Status: Ready", font=("Arial", 9, "italic"))
        self.lbl_timing.pack(side=tk.RIGHT)

        # Results Table
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
        self.tree.column("url", width=190, anchor=tk.W)
        self.tree.column("title", width=160, anchor=tk.W)
        self.tree.column("category", width=130, anchor=tk.CENTER)
        self.tree.column("reason", width=180, anchor=tk.W)
        self.tree.column("links", width=50, anchor=tk.CENTER)
        self.tree.column("words", width=50, anchor=tk.CENTER)

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
        
        rules = analyser_engine.get_keyword_rules()
        self.text_rules.insert(tk.END, json.dumps(rules, indent=4))

    def save_rules(self):
        try:
            raw_json = self.text_rules.get("1.0", tk.END)
            parsed_json = json.loads(raw_json)
            with open(analyser_engine.RULES_PATH, "w") as f:
                json.dump(parsed_json, f, indent=4)
            messagebox.showinfo("Success", "Keyword rules updated successfully.")
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON Error", f"Invalid JSON format:\n\n{e}")

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
        count = analyser_engine.process_unanalysed_jobs(
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
            records = analyser_engine.get_all_results()
            for row in records:
                self.tree.insert("", tk.END, values=row[:-1])
        except Exception as e:
            self.lbl_timing.config(text=f"Error reading DB: {e}")

    def download_csv(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filepath:
            analyser_engine.export_to_csv(filepath)

if __name__ == "__main__":
    analyser_engine.init_analyser_db()
    root = tk.Tk()
    app = AnalyserGUI(root)
    root.mainloop()