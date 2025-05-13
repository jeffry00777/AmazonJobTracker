from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage
import time
import os

# ---------------- CONFIG ----------------
JOB_SEARCH_URL = "https://www.amazon.jobs/en/search?base_query=Software+Engineer&loc_query=Greater+Boston%2C+MA%2C+United+States&latitude=&longitude=&loc_group_id=greater-boston&invalid_location=false&country=&city=&region=&county="
JOB_KEYWORD = "Software Development Engineer"
SEEN_JOBS_FILE = "seen_jobs.txt"

EMAIL_SENDER = "stiffler00777@gmail.com"
EMAIL_PASSWORD = "********************"
EMAIL_RECEIVER = "jeffrylivingston5@gmail.com"
# ----------------------------------------

def fetch_recently_updated_jobs():
    recent_jobs = {}
    cutoff = datetime.now() - timedelta(days=7)
    offset = 0
    max_offset = 1000  # Safety limit to avoid infinite loop

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    while offset < max_offset:
        url = (
            f"https://www.amazon.jobs/en/search?"
            f"offset={offset}&result_limit=10&sort=relevant&distanceType=Mi&radius=24km"
            f"&loc_group_id=greater-boston&latitude=&longitude=&loc_group_id=greater-boston"
            f"&loc_query=Greater%20Boston%2C%20MA%2C%20United%20States"
            f"&base_query=Software%20Engineer&city=&country=&region=&county=&query_options=&"
        )
        print(f"Scraping offset {offset}...")

        driver.get(url)
        time.sleep(5)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        job_cards = soup.find_all("div", class_="job-tile")

        if not job_cards:
            print("No more jobs found. Stopping.")
            break

        for card in job_cards:
            title_elem = card.find("h3", class_="job-title")
            link_elem = title_elem.find("a") if title_elem else None
            job_id_elem = card.find(string=lambda s: s and "Job ID:" in s)
            location_elem = card.find(string=lambda s: s and "USA" in s)
            update_elem = card.find("p", string=lambda s: s and "Updated" in s)

            if not (title_elem and job_id_elem and location_elem and update_elem and link_elem):
                continue

            if "USA" not in location_elem:
                continue

            title = title_elem.get_text(strip=True)
            job_id = job_id_elem.strip().split("Job ID:")[-1].strip()
            location = location_elem.strip()
            job_url = "https://www.amazon.jobs" + link_elem["href"]

            days_ago = int([s for s in update_elem.get_text(strip=True).split() if s.isdigit()][0])
            update_date = datetime.now() - timedelta(days=days_ago)

            if JOB_KEYWORD.lower() in title.lower() and update_date >= cutoff:
                key = f"{title} | Job ID: {job_id} | {location} | {job_url}"
                recent_jobs[key] = update_date.strftime("%Y-%m-%d")

        offset += 10

    driver.quit()
    return recent_jobs

def load_seen_jobs():
    seen = {}
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            for line in f:
                parts = line.strip().split("|||")
                if len(parts) == 3:
                    title, date, status = parts
                elif len(parts) == 2:
                    title, date = parts
                    status = "Pending"
                else:
                    continue
                seen[title] = (date, status)
    return seen

def save_seen_jobs(jobs):
    with open(SEEN_JOBS_FILE, "w") as f:
        for title, (date, status) in jobs.items():
            f.write(f"{title}|||{date}|||{status}\n")

def send_email_notification(jobs):
    msg = EmailMessage()
    msg["Subject"] = f"Amazon Job Updates: {JOB_KEYWORD}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    body = "Recently updated or new jobs:\n\n"
    for job in jobs:
        body += f"- {job}\n"

    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)

def main():
    recent_jobs = fetch_recently_updated_jobs()
    seen_jobs = load_seen_jobs()

    changes = {}

    for title, date in recent_jobs.items():
        if title not in seen_jobs:
            changes[title] = date
        else:
            seen_date, status = seen_jobs[title]
            if seen_date != date and status.strip().lower() != "applied":
                changes[title] = date

    if changes:
        print(f"Found {len(changes)} new or updated (not-applied) jobs.")
        send_email_notification(changes.keys())

        # Update seen_jobs with new entries and preserve Applied flags
        for title, date in recent_jobs.items():
            status = seen_jobs[title][1] if title in seen_jobs else "Pending"
            seen_jobs[title] = (date, status)

        save_seen_jobs(seen_jobs)
    else:
        print("No new or updated (not-applied) jobs in the past 7 days.")


if __name__ == "__main__":
    main()
