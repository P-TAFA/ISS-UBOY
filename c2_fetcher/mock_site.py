from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import random
import os

class MockSiteHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        query_params = parse_qs(parsed_path.query)
        item_id = int(query_params.get("item", ["1"])[0])
        
        template_id = item_id % 100
        random.seed(item_id)
        
        bg_colors = ["bg-slate-900", "bg-zinc-950", "bg-neutral-900", "bg-stone-900", "bg-gray-950", "bg-[#0b0e14]", "bg-[#121212]"]
        text_colors = ["text-blue-400", "text-emerald-400", "text-purple-400", "text-amber-400", "text-cyan-400", "text-rose-400", "text-lime-400"]
        border_colors = ["border-slate-800", "border-zinc-800", "border-emerald-900/50", "border-purple-900/40", "border-amber-900/40"]
        
        chosen_bg = random.choice(bg_colors)
        chosen_text = random.choice(text_colors)
        chosen_border = random.choice(border_colors)
        
        random_price = f"${random.randint(15, 2500)}.{random.choice(['00', '49', '99'])}"
        random_stock = random.randint(3, 142)
        img_seed = item_id * 37

        if template_id == 0:
            html_content = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>CloudScale AI #{item_id}</title><script src="https://cdn.tailwindcss.com"></script></head>
            <body class="{chosen_bg} text-slate-100 font-sans p-10">
            <span class="text-xs font-mono bg-blue-500/20 {chosen_text} px-3 py-1 rounded border {chosen_border}">Node #{item_id} (Stock: {random_stock})</span>
            <h1 class="text-4xl font-bold {chosen_text} mt-4">CloudScale Enterprise Hub #{item_id}</h1>
            <p class="text-slate-400 mt-2">Autonomous cloud infrastructure pipeline with randomized telemetry.</p>
            <img src="https://picsum.photos/seed/{img_seed}/800/400" class="rounded-xl mt-6 border {chosen_border} shadow-2xl">
            <span class="price text-3xl font-bold {chosen_text} block mt-6">{random_price}/mo</span>
            </body></html>"""
        else:
            categories = [
                "Cloud Infrastructure", "Luxury Apparel", "Global Telemetry", "Craft Roastery", 
                "Architectural Asset", "Cybernetic Gear", "Indie Game Hub", "DeFi Liquidity Pool", 
                "Exotic Specimen", "Roguelite Devlog", "Amsterdam Coffeeshop", "Electric Vehicle", 
                "Naval Architecture", "Landscaping Service", "Space Extractor", "Vinyl Release"
            ]
            category = categories[template_id % len(categories)]
            
            html_content = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>{category} #{item_id}</title><script src="https://cdn.tailwindcss.com"></script></head>
            <body class="{chosen_bg} text-slate-100 font-sans p-10">
            <div class="flex justify-between items-center">
                <span class="text-xs font-mono bg-slate-800 {chosen_text} px-3 py-1 rounded border {chosen_border}">Category: {category}</span>
                <span class="text-xs text-slate-400 font-mono">Node ID: #{item_id} (Batch: {random_stock})</span>
            </div>
            <h1 class="text-4xl font-extrabold text-white mt-4">{category} System Model #{item_id}</h1>
            <p class="text-slate-400 mt-2">Automated node telemetry, verified transaction gateway, and encrypted data package.</p>
            <img src="https://picsum.photos/seed/{img_seed}/800/400" class="rounded-xl shadow-2xl mt-6 border {chosen_border}">
            <div class="mt-6 flex items-center justify-between">
                <span class="price text-3xl font-bold {chosen_text}">{random_price}</span>
                <button class="bg-slate-800 hover:bg-slate-700 text-white font-bold px-6 py-3 rounded-lg text-sm border {chosen_border}">Inspect Node</button>
            </div>
            </body></html>"""

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html_content.encode("utf-8"))

def run_server(server_class=HTTPServer, handler_class=MockSiteHandler, port=8000):
    server_address = ('localhost', port)
    httpd = server_class(server_address, handler_class)
    print(f"Mock Server running at http://localhost:{port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()