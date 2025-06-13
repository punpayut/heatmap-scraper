import requests
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from datetime import datetime
import re
import os

class TradingViewHeatmapScraper:
    def __init__(self, headless=True):
        self.setup_driver(headless)
        
    def setup_driver(self, headless):
        """Setup Chrome WebDriver with options"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
    def scrape_heatmap_data(self, market="stock", screener="america"):
        """
        Scrape heatmap data from TradingView
        
        Args:
            market: 'stock', 'crypto', 'forex'
            screener: 'america', 'global', etc.
        """
        try:
            # Navigate to TradingView heatmap
            url = f"https://www.tradingview.com/heatmap/{market}/?color=change&dataset={screener}&group=sector&size=market_cap_basic"
            self.driver.get(url)
            
            # Wait for the heatmap to load
            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "heatmap-container")))
            
            time.sleep(5)  # Additional wait for data to fully load
            
            # Execute JavaScript to extract heatmap data
            heatmap_data = self.driver.execute_script("""
                let data = [];
                
                // Find all heatmap rectangles/cells
                const cells = document.querySelectorAll('[data-symbol]');
                
                cells.forEach(cell => {
                    try {
                        const symbol = cell.getAttribute('data-symbol');
                        const rect = cell.getBoundingClientRect();
                        
                        // Extract text content and attributes
                        const textElements = cell.querySelectorAll('text, tspan');
                        let name = '';
                        let change = '';
                        let price = '';
                        
                        textElements.forEach(text => {
                            const content = text.textContent.trim();
                            if (content.includes('%')) {
                                change = content;
                            } else if (content.match(/^\d+\.\d+$/)) {
                                price = content;
                            } else if (content.length > 0 && !content.includes('$')) {
                                name = content;
                            }
                        });
                        
                        // Get color/fill for change indication
                        const style = window.getComputedStyle(cell);
                        const fill = cell.getAttribute('fill') || style.fill;
                        
                        if (symbol) {
                            data.push({
                                symbol: symbol,
                                name: name || symbol,
                                change: change,
                                price: price,
                                color: fill,
                                area: rect.width * rect.height
                            });
                        }
                    } catch (e) {
                        console.log('Error processing cell:', e);
                    }
                });
                
                return data;
            """)
            
            return heatmap_data
            
        except Exception as e:
            print(f"Error scraping heatmap: {e}")
            return []
    
    def get_stock_details(self, symbols):
        """Get additional stock details using TradingView's API-like endpoints"""
        stock_data = []
        
        for symbol in symbols:
            try:
                # This is a simplified approach - TradingView's actual API requires authentication
                # You may need to inspect network requests for the exact endpoints
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                # Note: This endpoint may not work without proper authentication
                # It's included as an example of how you might structure API calls
                url = f"https://scanner.tradingview.com/symbol"
                params = {
                    'symbol': symbol,
                    'fields': 'name,close,change,change_abs,volume,market_cap_basic'
                }
                
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    stock_data.append(data)
                    
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
                
        return stock_data
    
    def parse_change_value(self, change_str):
        """Extract numeric value from change string"""
        if not change_str:
            return 0.0
        # Extract number from string like "+2.45%" or "-1.23%"
        match = re.search(r'([+-]?\d+\.?\d*)', change_str.replace('%', ''))
        return float(match.group(1)) if match else 0.0
    
    def get_color_from_change(self, change_value):
        """Generate color based on change value"""
        if change_value > 0:
            # Green shades for positive
            intensity = min(abs(change_value) * 10, 100)
            return f"rgba(34, 197, 94, {0.3 + intensity/200})"
        elif change_value < 0:
            # Red shades for negative
            intensity = min(abs(change_value) * 10, 100)
            return f"rgba(239, 68, 68, {0.3 + intensity/200})"
        else:
            return "rgba(156, 163, 175, 0.3)"  # Gray for no change
    
    def generate_html_output(self, data, filename="heatmap_output.html"):
        """Generate interactive HTML page with heatmap visualization"""
        if not data:
            print("No data to generate HTML")
            return
        
        # Process data for visualization
        processed_data = []
        for item in data:
            change_value = self.parse_change_value(item.get('change', '0%'))
            processed_item = {
                'symbol': item.get('symbol', 'N/A'),
                'name': item.get('name', 'N/A'),
                'change': item.get('change', '0%'),
                'change_value': change_value,
                'price': item.get('price', 'N/A'),
                'area': item.get('area', 100),
                'color': self.get_color_from_change(change_value)
            }
            processed_data.append(processed_item)
        
        # Sort by area (market cap) descending
        processed_data.sort(key=lambda x: x['area'], reverse=True)
        
        # Generate HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Heatmap - {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: white;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .header p {{
            color: #94a3b8;
            font-size: 1.1rem;
        }}
        
        .stats {{
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }}
        
        .stat-item {{
            text-align: center;
            padding: 15px 25px;
            background: rgba(51, 65, 85, 0.5);
            border-radius: 10px;
            border: 1px solid rgba(71, 85, 105, 0.3);
        }}
        
        .stat-number {{
            font-size: 1.8rem;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            color: #94a3b8;
            font-size: 0.9rem;
        }}
        
        .positive {{ color: #22c55e; }}
        .negative {{ color: #ef4444; }}
        .neutral {{ color: #6b7280; }}
        
        .heatmap-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .stock-tile {{
            background: var(--tile-color);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }}
        
        .stock-tile:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
            border-color: rgba(255, 255, 255, 0.2);
        }}
        
        .stock-tile::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--accent-color);
        }}
        
        .stock-symbol {{
            font-size: 1.4rem;
            font-weight: bold;
            margin-bottom: 8px;
            color: white;
        }}
        
        .stock-name {{
            font-size: 0.9rem;
            color: #cbd5e1;
            margin-bottom: 15px;
            line-height: 1.3;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        
        .stock-metrics {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .stock-change {{
            font-size: 1.2rem;
            font-weight: bold;
        }}
        
        .stock-price {{
            font-size: 0.9rem;
            color: #94a3b8;
        }}
        
        .legend {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 40px;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid rgba(71, 85, 105, 0.3);
            color: #64748b;
        }}
        
        @media (max-width: 768px) {{
            .heatmap-container {{
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 10px;
            }}
            
            .stock-tile {{
                padding: 15px;
            }}
            
            .stats {{
                gap: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📈 Stock Market Heatmap</h1>
        <p>Live data from TradingView • Updated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
    </div>
    
    <div class="stats">
        <div class="stat-item">
            <div class="stat-number">{len(processed_data)}</div>
            <div class="stat-label">Total Stocks</div>
        </div>
        <div class="stat-item">
            <div class="stat-number positive">{len([x for x in processed_data if x['change_value'] > 0])}</div>
            <div class="stat-label">Gainers</div>
        </div>
        <div class="stat-item">
            <div class="stat-number negative">{len([x for x in processed_data if x['change_value'] < 0])}</div>
            <div class="stat-label">Losers</div>
        </div>
        <div class="stat-item">
            <div class="stat-number neutral">{len([x for x in processed_data if x['change_value'] == 0])}</div>
            <div class="stat-label">Unchanged</div>
        </div>
    </div>
    
    <div class="heatmap-container">
"""
        
        # Add stock tiles
        for stock in processed_data:
            change_class = "positive" if stock['change_value'] > 0 else "negative" if stock['change_value'] < 0 else "neutral"
            accent_color = "#22c55e" if stock['change_value'] > 0 else "#ef4444" if stock['change_value'] < 0 else "#6b7280"
            
            html_content += f"""
        <div class="stock-tile" style="--tile-color: {stock['color']}; --accent-color: {accent_color};">
            <div class="stock-symbol">{stock['symbol']}</div>
            <div class="stock-name" title="{stock['name']}">{stock['name']}</div>
            <div class="stock-metrics">
                <div class="stock-change {change_class}">{stock['change']}</div>
                <div class="stock-price">${stock['price']}</div>
            </div>
        </div>
"""
        
        # Close HTML
        html_content += f"""
    </div>
    
    <div class="legend">
        <div class="legend-item">
            <div class="legend-color" style="background: rgba(34, 197, 94, 0.6);"></div>
            <span>Positive Change</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: rgba(239, 68, 68, 0.6);"></div>
            <span>Negative Change</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: rgba(156, 163, 175, 0.6);"></div>
            <span>No Change</span>
        </div>
    </div>
    
    <div class="footer">
        <p>Data scraped from TradingView • Generated by Python Stock Heatmap Scraper</p>
        <p>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <script>
        // Add click functionality to tiles
        document.querySelectorAll('.stock-tile').forEach(tile => {{
            tile.addEventListener('click', function() {{
                const symbol = this.querySelector('.stock-symbol').textContent;
                const url = `https://www.tradingview.com/symbols/${{symbol}}`;
                window.open(url, '_blank');
            }});
        }});
        
        // Add keyboard navigation
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'r' || e.key === 'R') {{
                location.reload();
            }}
        }});
        
        console.log('Stock Heatmap loaded with {len(processed_data)} stocks');
        console.log('Press R to refresh • Click any tile to view on TradingView');
    </script>
</body>
</html>
"""
        
        # Write to file
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"Interactive HTML heatmap saved to {filename}")
            print(f"Open the file in your browser to view the visualization")
            return filename
        except Exception as e:
            print(f"Error saving HTML file: {e}")
    def save_to_csv(self, data, filename="heatmap_data.csv"):
        """Save scraped data to CSV"""
        if data:
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False)
            print(f"Data saved to {filename}")
        else:
            print("No data to save")
    
    def close(self):
        """Close the WebDriver"""
        if hasattr(self, 'driver'):
            self.driver.quit()

# Usage example
def main():
    print("DEBUG: Starting main function...") # เพิ่ม log
    scraper = TradingViewHeatmapScraper(headless=True)
    heatmap_data = [] # khởi tạoเป็น list ว่าง
    html_file_generated = False # flag

    try:
        print("DEBUG: Scraping TradingView heatmap...")
        heatmap_data = scraper.scrape_heatmap_data(market="stock", screener="america")

        if heatmap_data:
            print(f"DEBUG: Found {len(heatmap_data)} stocks.")
            # ... (ส่วนแสดงผลและ save_to_csv เหมือนเดิม) ...
            scraper.save_to_csv(heatmap_data, "heatmap_data.csv") # ตรวจสอบให้แน่ใจว่าชื่อไฟล์ถูกต้อง
            print(f"DEBUG: CSV data saved to heatmap_data.csv")

            print("DEBUG: Attempting to generate HTML output...")
            # เรียก generate_html_output โดยตรงด้วยชื่อไฟล์ที่คาดหวัง
            html_filename = "heatmap_output.html"
            actual_html_file = scraper.generate_html_output(heatmap_data, html_filename)
            if actual_html_file and os.path.exists(actual_html_file):
                print(f"DEBUG: HTML report successfully generated at {os.path.abspath(actual_html_file)}")
                html_file_generated = True
            else:
                print(f"DEBUG: HTML report generation failed or file not found at expected location: {html_filename}")
        else:
            print("DEBUG: No heatmap data found. Scraper might have failed to retrieve data.")
            # คุณอาจจะยังต้องการสร้าง HTML เปล่าๆ หรือ report ที่บอกว่าไม่มีข้อมูล
            print("DEBUG: Attempting to generate an empty/error HTML report...")
            html_filename = "heatmap_no_data.html" # หรือชื่ออื่น
            # ส่ง list ว่างไปก็ได้ หรือสร้าง data dummy
            actual_html_file = scraper.generate_html_output([], html_filename)
            if actual_html_file and os.path.exists(actual_html_file):
                print(f"DEBUG: Empty/Error HTML report successfully generated at {os.path.abspath(actual_html_file)}")
                # html_file_generated = True # ตั้งค่าตามต้องการ
            else:
                print(f"DEBUG: Empty/Error HTML report generation failed.")


    except Exception as e:
        print(f"CRITICAL ERROR in main: {e}") # ทำให้ error นี้เด่นขึ้น
        import traceback
        traceback.print_exc() # พิมพ์ stack trace เต็มๆ

    finally:
        print("DEBUG: In finally block. Closing scraper.")
        scraper.close()
        print(f"DEBUG: Scraper closed. HTML file generated status: {html_file_generated}")

if __name__ == "__main__":
    main()