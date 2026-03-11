"""
linkedin_applier.py
Selenium bot that automates LinkedIn Easy Apply for matched jobs.
Uses undetected-chromedriver to reduce bot detection.
"""

import time
import json
import os
import random
from datetime import datetime

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import (
        NoSuchElementException, TimeoutException,
        ElementNotInteractableException
    )
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️  Selenium not installed. Run: pip install undetected-chromedriver selenium")


def human_delay(min_sec: float = 0.5, max_sec: float = 2.0) -> None:
    '''
    Adds a randomized human-like delay between actions.
    '''
    time.sleep(random.uniform(min_sec, max_sec))


def type_like_human(element, text: str) -> None:
    '''
    Types text character by character with random delays to mimic human typing.
    '''
    element.clear()
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.03, 0.12))


def init_driver(headless: bool = False) -> object:
    '''
    Initializes an undetected Chrome WebDriver.
    headless=False recommended to handle CAPTCHAs manually.
    '''
    if not SELENIUM_AVAILABLE:
        raise ImportError("undetected-chromedriver not installed")

    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")

    driver = uc.Chrome(options=options)
    return driver


def linkedin_login(driver, email: str, password: str) -> bool:
    '''
    Logs into LinkedIn with the given credentials.
    Returns True if login succeeded, False otherwise.
    '''
    try:
        driver.get("https://www.linkedin.com/login")
        human_delay(2, 4)

        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        type_like_human(email_field, email)
        human_delay(0.5, 1.5)

        pass_field = driver.find_element(By.ID, "password")
        type_like_human(pass_field, password)
        human_delay(0.5, 1.0)

        pass_field.send_keys(Keys.RETURN)
        human_delay(3, 6)

        # Check if login succeeded
        if "feed" in driver.current_url or "mynetwork" in driver.current_url:
            print("✅ LinkedIn login successful")
            return True
        else:
            print("⚠️  Login may have failed — check for CAPTCHA or verification")
            return False

    except Exception as e:
        print(f"❌ Login error: {e}")
        return False


def answer_form_question(driver, element, question_text: str, answers_config: dict, profile: dict) -> bool:
    '''
    Attempts to answer a form question using the answers config and profile data.
    Returns True if answered, False if unknown.
    '''
    tag = element.tag_name.lower()
    q_lower = question_text.lower()

    # Build answer lookup from config + profile
    lookup = {
        "phone": profile.get("phone", ""),
        "mobile": profile.get("phone", ""),
        "city": profile.get("location", "").split(",")[0],
        "location": profile.get("location", ""),
        "years of experience": str(profile.get("years_of_experience", "")),
        "experience": str(profile.get("years_of_experience", "")),
        "notice period": answers_config.get("notice_period", "30"),
        "current salary": answers_config.get("current_salary", ""),
        "expected salary": answers_config.get("expected_salary", ""),
        "linkedin": profile.get("linkedin", ""),
        "github": profile.get("github", ""),
        "cover letter": answers_config.get("cover_letter", ""),
        "summary": answers_config.get("summary", profile.get("summary", "")),
        "visa": answers_config.get("visa_status", "Citizen"),
        "authorized": answers_config.get("work_authorization", "Yes"),
        "sponsor": answers_config.get("require_sponsorship", "No"),
        "relocate": answers_config.get("willing_to_relocate", "Yes"),
        "remote": answers_config.get("prefer_remote", "Yes"),
    }

    # Find best matching answer
    answer = None
    for key, val in lookup.items():
        if key in q_lower and val:
            answer = str(val)
            break

    # Check custom answers config
    if not answer:
        for key, val in answers_config.get("custom_answers", {}).items():
            if key.lower() in q_lower:
                answer = str(val)
                break

    if tag in ["input", "textarea"] and answer:
        try:
            type_like_human(element, answer)
            return True
        except Exception:
            pass

    if tag == "select" and answer:
        try:
            sel = Select(element)
            # Try exact match first, then partial
            for opt in sel.options:
                if answer.lower() in opt.text.lower():
                    sel.select_by_visible_text(opt.text)
                    return True
        except Exception:
            pass

    return False  # Unknown question — will pause if configured


def apply_to_job_linkedin(driver, job: dict, profile: dict,
                           answers_config: dict, resume_path: str,
                           pause_before_submit: bool = True) -> str:
    '''
    Applies to a single LinkedIn Easy Apply job.
    Returns status: "applied", "skipped", "failed", "manual_required"
    '''
    apply_link = job.get("apply_link", "")

    if "linkedin.com" not in apply_link:
        return "skipped"  # Not a LinkedIn job

    try:
        driver.get(apply_link)
        human_delay(2, 4)

        # Find Easy Apply button
        try:
            easy_apply_btn = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR,
                    "button.jobs-apply-button, [aria-label*='Easy Apply']"))
            )
            easy_apply_btn.click()
            human_delay(1.5, 3)
        except TimeoutException:
            print(f"    ℹ️  No Easy Apply button found for: {job.get('title')}")
            return "skipped"

        # Handle multi-step form
        max_steps = 10
        for step in range(max_steps):
            human_delay(1, 2)

            # Check for file upload (resume)
            try:
                file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
                for fi in file_inputs:
                    if fi.is_displayed() or not fi.get_attribute("style"):
                        fi.send_keys(os.path.abspath(resume_path))
                        human_delay(1, 2)
            except Exception:
                pass

            # Answer visible form questions
            try:
                form_groups = driver.find_elements(By.CSS_SELECTOR,
                    ".jobs-easy-apply-form-section__grouping, .fb-form-element")
                for group in form_groups:
                    try:
                        label = group.find_element(By.TAG_NAME, "label").text.strip()
                        inputs = group.find_elements(By.CSS_SELECTOR, "input, textarea, select")
                        for inp in inputs:
                            answer_form_question(driver, inp, label, answers_config, profile)
                    except Exception:
                        pass
            except Exception:
                pass

            # Look for Next / Review / Submit button
            try:
                # Submit button
                submit_btn = driver.find_elements(By.CSS_SELECTOR,
                    "button[aria-label*='Submit application']")
                if submit_btn:
                    if pause_before_submit:
                        input(f"\n⏸️  PAUSE: Review application for {job.get('title')} @ {job.get('company')}. Press ENTER to submit...")
                    submit_btn[0].click()
                    human_delay(2, 4)
                    print(f"    ✅ APPLIED: {job.get('title')} @ {job.get('company')}")
                    return "applied"

                # Next/Review button
                next_btn = driver.find_elements(By.CSS_SELECTOR,
                    "button[aria-label='Continue to next step'], button[aria-label='Review your application']")
                if next_btn:
                    next_btn[0].click()
                    continue

                # Generic "Next" or "Continue"
                btns = driver.find_elements(By.CSS_SELECTOR,
                    ".artdeco-button--primary")
                for btn in btns:
                    txt = btn.text.strip().lower()
                    if txt in ["next", "continue", "review"]:
                        btn.click()
                        human_delay(1, 2)
                        break
                else:
                    break

            except Exception as e:
                print(f"    ⚠️  Step error: {e}")
                break

        return "manual_required"

    except Exception as e:
        print(f"    ❌ Failed: {job.get('title')} — {e}")
        return "failed"


def run_linkedin_applier(apply_list: list[dict], profile: dict,
                          answers_config: dict, secrets: dict,
                          resume_path: str, max_applications: int = 20,
                          pause_before_submit: bool = True) -> list[dict]:
    '''
    Main LinkedIn apply loop. Iterates through apply_list and applies to
    LinkedIn Easy Apply jobs up to max_applications.
    Returns updated apply_list with status field set.
    '''
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium not available. Install with: pip install undetected-chromedriver selenium")
        return apply_list

    linkedin_jobs = [j for j in apply_list if "linkedin.com" in j.get("apply_link", "")]
    print(f"\n🔗 Found {len(linkedin_jobs)} LinkedIn Easy Apply jobs")
    print(f"   Will apply to up to {max_applications} jobs\n")

    driver = init_driver(headless=False)
    applied_count = 0

    try:
        login_ok = linkedin_login(
            driver,
            secrets.get("LINKEDIN_EMAIL"),
            secrets.get("LINKEDIN_PASSWORD")
        )

        if not login_ok:
            print("❌ Login failed. Please log in manually in the browser window.")
            input("Press ENTER when logged in...")

        for job in linkedin_jobs:
            if applied_count >= max_applications:
                print(f"\n🛑 Reached max applications limit ({max_applications})")
                break

            print(f"\n  Applying: [{job.get('match_score')}/100] {job.get('title')} @ {job.get('company')}")

            status = apply_to_job_linkedin(
                driver, job, profile, answers_config,
                resume_path, pause_before_submit
            )

            job["status"] = status
            job["applied_at"] = datetime.now().isoformat() if status == "applied" else None

            if status == "applied":
                applied_count += 1
                print(f"   📊 Progress: {applied_count}/{max_applications}")
                human_delay(3, 8)  # Longer gap between applications

    except KeyboardInterrupt:
        print("\n⏹️  Stopped by user")
    finally:
        driver.quit()

    print(f"\n🎉 Done! Applied to {applied_count} jobs on LinkedIn")
    return apply_list
