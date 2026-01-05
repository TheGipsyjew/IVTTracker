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
    
    # The container class seems to be 'sc-embLYd' based on the HTML dump
    post_elements = driver.select_all('.sc-embLYd')
    
    print(f"Found {len(post_elements)} posts.")
    
    for post in post_elements:
        try:
            # Extract category
            category_el = post.select('h3')
            category = category_el.text if category_el else "Unknown"
            
            # Extract content
            container_el = post.select('.sc-fMfAsl')
            content = container_el.text if container_el else "No content"
            
            # Extract Author and Date
            author_container_el = post.select('.sc-kXXgDA')
            if author_container_el:
                # The text of the container includes author and date usually, 
                # but date is in a child p tag.
                date_el = author_container_el.select('p')
                date = date_el.text if date_el else ""
                
                # Author name is the text node of the container, might need cleaning
                # We can get all text and replace the date text
                full_text = author_container_el.text
                author = full_text.replace(date, "").strip()
            else:
                author = "Unknown"
                date = "Unknown"
                
            post_data = {
                "author": author,
                "date": date,
                "category": category,
                "content": content
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
