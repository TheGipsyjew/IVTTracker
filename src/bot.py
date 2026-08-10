from botasaurus.browser import browser, Driver
from dotenv import load_dotenv
import os
import time
import json

load_dotenv(override=True)

USERNAME = os.getenv("IVT_USERNAME")
PASSWORD = os.getenv("IVT_PASSWORD")

@browser(
    headless=True,
    profile="ivt_tracker_main", 
    block_images=True,
    cache=False
)
def login_and_scrape(driver: Driver, data):
    url = "https://app.interactivtrading.com/"
    print(f"Navigating to {url}...")
    driver.get(url)

    # Check if we are already logged in
    if driver.is_element_present('input[type="text"]', wait=5):
        print("Login form detected. Logging in...")
        
        # Input username
        driver.type('input[type="text"]', USERNAME)
        
        # Input password
        driver.type('input[type="password"]', PASSWORD)
        
        # Click login
        # Try to find the button by type="submit" or specific class
        login_btn = driver.select('button[type="submit"]')
        if not login_btn:
            login_btn = driver.select('button.kXHAcR')
        
        if login_btn:
            print("Login button found. Clicking...")
            login_btn.click()
        else:
            print("Could not find login button!")
            driver.save_screenshot("login_fail.png")
            return
        
        # Wait for navigation/login success
        # Wait for the inputs to disappear
        for _ in range(20):
            if not driver.is_element_present('input[type="text"]', wait=0.5):
                print("Login input disappeared. Login likely successful.")
                break
            time.sleep(1)
        else:
            print("Warning: Login input still present after 20s.")
            
    else:
        print("Already logged in (or login form not found immediately).")

    # Wait for the main app to load
    time.sleep(5) # Give it some time to load posts
    
    # Scrape posts
    print("Scraping posts...")
    posts = []
    
    # ROBUST SELECTOR: Use ID pattern that starts with "alert-" instead of dynamic classes
    # This is much more stable as the ID appears to be consistent per notification
    post_elements = driver.select_all('div[id^="alert-"]')
    
    print(f"Found {len(post_elements)} posts.")
    
    for post in post_elements:
        try:
            # Find the header container first (contains author, date, title)
            # Based on structure: div.sc-hScZsb > div.sc-gHsaLt (header) + div.sc-iBNCcx (category) + div.sc-hlcNoQ (content wrapper)
            # We rely on structure, not specific sc- class names for inner elements
            
            # Extract Author: 
            # Strategy: Look for the first span in the header section that is NOT a date and NOT an @handle wrapper if possible
            # Better Strategy based on HTML provided: 
            # The header div contains: [Span: Name] [Div: Badge] [Span: @Handle] [Small: Date]
            # Let's find all direct spans in the post, the first one is usually the Display Name
            all_spans = post.select_all('span')
            author = "Unknown"
            
            # Robust Author Extraction:
            # The first span in the notification block is typically the Display Name (e.g., "Xavier")
            # We verify it doesn't look like a date or contain "@"
            for span in all_spans:
                text = span.text.strip()
                if text and not text.startswith('@') and ':' not in text and len(text) < 50:
                    # Check if this span is likely the name (usually short, no special chars)
                    # In the provided HTML, the first span is "Xavier"
                    author = text
                    break
            
            # If the simple method failed or picked up something else, try looking for the @ handle and clean it
            if author == "Unknown":
                for span in all_spans:
                    text = span.text.strip()
                    if text.startswith('@'):
                        author = text[1:] # Remove the @
                        break
            
            # Extract Date:
            # Strategy: Find the <small> tag. It's unique enough in this context.
            date_el = post.select('small')
            date = date_el.text.strip() if date_el else "Unknown"
            
            # Extract Category/Title:
            # Strategy: The title is in a div immediately following the header, often containing short text.
            # In the HTML: <div class="sc-iBNCcx">Briefing du matin</div>
            # We look for a div with short text (< 100 chars) that isn't the content body
            all_divs = post.select_all('div')
            category = "Unknown"
            for div in all_divs:
                text = div.text.strip()
                # Heuristic: Title is short, single line, no newlines usually
                if text and len(text) < 100 and '\n' not in text and text != date:
                    # Avoid picking up the content body or buttons
                    if len(div.select_all('*')) == 0 or len(div.select_all('*')) < 5: # Simple div
                         # Check if it's not the author name we already found
                        if text != author and not text.startswith('@'):
                            category = text
                            break
            
            # Extract Content:
            # Strategy: The main content is in a span with a lot of text, usually after the title
            # It often contains newlines and is longer than the title
            content = "No content"
            # Re-scan spans for the longest text block that looks like a message
            longest_text = ""
            for span in all_spans:
                text = span.text.strip()
                # Content is usually long, contains newlines, or is significantly longer than title/author
                if len(text) > len(longest_text) and len(text) > 50: 
                    longest_text = text
            
            if longest_text:
                content = longest_text
            
            # Extract Images:
            # Strategy: Find all img tags where src contains 'cloudfront.net' (stable domain)
            images = []
            img_elements = post.select_all('img')
            for img in img_elements:
                src = img.attrs.get('src', '')
                if 'cloudfront.net' in src:
                    images.append(src)
            
            post_data = {
                "author": author,
                "date": date,
                "category": category,
                "content": content,
                "images": images
            }
            posts.append(post_data)
            
        except Exception as e:
            print(f"Error scraping a post: {e}")
            
    # Save to JSON
    with open("posts.json", "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully saved {len(posts)} posts to posts.json")

if __name__ == "__main__":
    login_and_scrape()
