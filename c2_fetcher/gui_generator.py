import tkinter as tk
from tkinter import scrolledtext, messagebox

def generate_urls(count=1000):
    url_textbox.delete("1.0", tk.END)
    urls = [f"http://localhost:8000/?item={i}" for i in range(1, count + 1)]
    url_textbox.insert(tk.END, "\n".join(urls))
    status_label.config(text=f"Generated {count} URLs. Ready to copy.", fg="#00ff00")

def copy_to_clipboard():
    text = url_textbox.get("1.0", tk.END).strip()
    if not text:
        messagebox.showwarning("Warning", "No URLs to copy. Generate some first!")
        return
    
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()  # Keep clipboard after window closes
    status_label.config(text="✔ All URLs copied to clipboard!", fg="#5cb85c")
    messagebox.showinfo("Copied", f"Copied {len(text.splitlines())} URLs to clipboard!")

root = tk.Tk()
root.title("URL Generator -> Clipboard")
root.geometry("520x620")
root.config(bg="#2b2b2b")

tk.Label(root, text="Sandbox URL List Generator", fg="white", bg="#2b2b2b", font=("Arial", 13, "bold")).pack(pady=10)

btn_frame = tk.Frame(root, bg="#2b2b2b")
btn_frame.pack(fill=tk.X, padx=15, pady=5)

gen_btn = tk.Button(btn_frame, text="⚡ Generate 1,000 URLs", command=lambda: generate_urls(1000), bg="#0275d8", fg="white", font=("Arial", 10, "bold"), padx=8, pady=6)
gen_btn.pack(side=tk.LEFT, padx=(0, 5))

copy_btn = tk.Button(btn_frame, text="📋 Copy All to Clipboard", command=copy_to_clipboard, bg="#5cb85c", fg="white", font=("Arial", 10, "bold"), padx=8, pady=6)
copy_btn.pack(side=tk.LEFT, padx=5)

url_textbox = scrolledtext.ScrolledText(root, width=55, height=26, bg="#1e1e1e", fg="#ffffff", font=("Consolas", 9))
url_textbox.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

status_label = tk.Label(root, text="Click Generate, then Copy All to Clipboard.", fg="#aaaaaa", bg="#2b2b2b", font=("Arial", 9))
status_label.pack(pady=(0, 10))

root.mainloop()