import sqlite3
import os
import time
import urllib.request
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "c2_queue.db")

# Control flag for starting/stopping engines remotely
is_running = False
worker_thread = None

def worker_loop():
    global is_running
    print(f"[!] Worker engine online. Polling database at: {DB_FILE}")
    
    while is_running:
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # Grab one pending job
            cursor.execute("SELECT id, target_url FROM jobs WHERE status = 'pending' LIMIT 1")
            job = cursor.fetchone()
            
            if job:
                job_id, url = job
                print(f"[+] Processing Job #{job_id}: {url}")
                
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        html_content = response.read().decode('utf-8', errors='ignore')
                    
                    cursor.execute("UPDATE jobs SET status = 'completed', response_data = ? WHERE id = ?", (html_content, job_id))
                    conn.commit()
                    print(f"[✔] Completed Job #{job_id}")
                except Exception as e:
                    print(f"[X] Failed Job #{job_id}: {e}")
                    cursor.execute("UPDATE jobs SET status = 'failed', response_data = ? WHERE id = ?", (str(e), job_id))
                    conn.commit()
            
            conn.close()
        except Exception as e:
            print(f"[!] Worker database error: {e}")
            
        time.sleep(1)
    
    print("[!] Worker engines stopped.")

def start_worker():
    global is_running, worker_thread
    if not is_running:
        is_running = True
        worker_thread = threading.Thread(target=worker_loop, daemon=True)
        worker_thread.start()
        print("[✔] Worker started via control signal.")

def stop_worker():
    global is_running
    is_running = False
    print("[!] Stop signal sent to worker.")

if __name__ == "__main__":
    # If run directly from terminal for standalone testing, 
    # you can choose to auto-start or wait. Let's make standalone auto-start 
    # UNLESS imported by a GUI control panel.
    print("Standalone Worker Mode. Press Ctrl+C to exit.")
    is_running = True
    try:
        worker_loop()
    except KeyboardInterrupt:
        stop_worker()