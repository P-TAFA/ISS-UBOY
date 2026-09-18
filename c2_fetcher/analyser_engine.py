import sqlite3
import json
import csv
import os
import time
from bs4 import BeautifulSoup

DB_PATH = "c2_queue.db"
RULES_PATH = "keyword_rules.json"

def get_keyword_rules():
    if not os.path.exists(RULES_PATH):
        default_rules = {
            "Suspicious/Phishing": ["verify your account", "urgent action required", "seed phrase", "claim your prize"],
            "E-Commerce": ["add to cart", "proceed to checkout", "out of stock", "shipping policy"],
            "Blog/News": ["published on", "read time", "leave a comment", "subscribe to our newsletter"],
            "Tech/Software": ["documentation", "api reference", "open source", "release notes"]
        }
        with open(RULES_PATH, "w") as f:
            json.dump(default_rules, f, indent=4)
        return default_rules
        
    with open(RULES_PATH, "r") as f:
        return json.load(f)

def init_analyser_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
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

def categorize_website(text, rules):
    text_lower = text.lower()
    category_scores = {}
    
    for category, keywords in rules.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > 0:
            category_scores[category] = score
            
    if category_scores:
        primary_category = max(category_scores, key=category_scores.get)
        return primary_category, f"Matched {category_scores[primary_category]} keywords"
    
    return "Uncategorized", "No defining keywords found"

def extract_page_data(raw_html, rules):
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
        
    title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"
    h1_tag = soup.find("h1")
    h1_text = h1_tag.get_text().strip() if h1_tag else "No H1"
    links = [a.get("href") for a in soup.find_all("a", href=True)]
    visible_text = soup.get_text(separator=" ", strip=True)
    word_count = len(visible_text.split())
    
    category, reason = categorize_website(visible_text, rules)
    
    return {
        "title": title,
        "h1": h1_text,
        "link_count": len(links),
        "word_count": word_count,
        "category": category,
        "match_reason": reason
    }

def process_unanalysed_jobs(progress_callback=None, reanalyse_all=False):
    init_analyser_db()
    rules = get_keyword_rules()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if reanalyse_all:
        cursor.execute("DELETE FROM analysis_results")
        conn.commit()
        cursor.execute("""
            SELECT j.id, j.target_url, j.response_data 
            FROM jobs j 
            WHERE j.response_data IS NOT NULL
        """)
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
                data = extract_page_data(raw_html, rules)
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
    init_analyser_db()
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

def export_to_csv(filepath):
    rows = get_all_results()
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Job ID", "URL", "Page Title", "Category", "Match Reason", "Link Count", "Word Count", "Analysed At"])
        writer.writerows(rows)