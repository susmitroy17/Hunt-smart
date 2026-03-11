"""
naukri_applier.py
Selenium bot for applying to jobs on Naukri.com.
Handles login, job search, and one-click apply flows.
"""

import time
import random
import json
import os
from datetime import datetime

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


def human_delay(min_sec: float = 0.8, max_sec: float = 2.5) -> None:
    time.sleep(random.uniform(min_sec, max_sec))


def type_like_human(element, text: str) -> None:
    element.clear()
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.04, 0.13))


def naukri_login(driver, email: str, password: str) -> bool:
    '''
    Logs into Naukri.com.
    Returns True if login succeeded.
    '''
    try:
        driver.get("https://www.naukri.com/nlogin/login")
        human_delay(2, 4)

        # Accept cookies if prompted
        try:
            cookie_btn = driver.find_element(By.ID, "acceptCookies")
            cookie_btn.click()
            human_delay(0.5, 1)
        except Exception:
            pass

        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "usernameField"))
        )
        type_like_human(email_field, email)
        human_delay(0.5, 1.2)

        pass_field = driver.find_element(By.ID, "passwordField")
        type_like_human(pass_field, password)
        human_delay(0.5, 1.0)

        login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_btn.click()
        human_delay(3, 6)

        if "naukri.com" in driver.current_url and "login" not in driver.current_url:
            print("✅ Naukri login successful")
            return True
        else:
            print("⚠️  Naukri login may need verification — check browser")
            return False

    except Exception as e:
        print(f"❌ Naukri login error: {e}")
        return False


def update_naukri_profile_resume(driver, resume_path: str) -> bool:
    '''
    Updates the resume on Naukri profile page.
    Naukri shows your profile to recruiters — keeping it updated triggers
    "Apply" to go through smoothly.
    Returns True if successful.
    '''
    try:
        driver.get("https://www.naukri.com/mnjuser/profile")
        human_delay(3, 5)

        # Find resume upload button
        upload_btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        upload_btn.send_keys(os.path.abspath(resume_path))
        human_delay(2, 4)

        # Confirm upload
        try:
            save_btn = driver.find_element(By.CSS_SELECTOR, ".saveProfileBtn, [class*='save']")
            save_btn.click()
            human_delay(2, 3)
        except Exception:
            pass

        print("✅ Naukri profile resume updated")
        return True

    except Exception as e:
        print(f"⚠️  Could not update Naukri resume: {e}")
        return False


def search_and_apply_naukri(driver, profile: dict, search_config: dict,
                              max_applications: int = 15,
                              pause_before_apply: bool = True) -> list[dict]:
    '''
    Searches for jobs on Naukri based on profile keywords and applies
    using the "Apply" button (1-click apply where available).
    Returns list of application records.
    '''
    applied_jobs = []
    roles = profile.get("target_roles", [])[:3]
    location = search_config.get("naukri_location", "India")
    experience_years = int(profile.get("years_of_experience", 2))

    for role in roles:
        if len(applied_jobs) >= max_applications:
            break

        print(f"\n  🔍 Naukri search: {role} in {location}")

        # Build search URL
        search_url = (
            f"https://www.naukri.com/{role.lower().replace(' ', '-')}-jobs-in-{location.lower()}"
            f"?experience={experience_years}"
        )

        try:
            driver.get(search_url)
            human_delay(2, 4)

            # Get job cards
            job_cards = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR,
                    ".jobTuple, article.jobTupleHeader, .job-container"))
            )

            print(f"    Found {len(job_cards)} jobs")

            for card in job_cards[:10]:
                if len(applied_jobs) >= max_applications:
                    break

                try:
                    title_el = card.find_element(By.CSS_SELECTOR, ".title, a.title, .jobTitle")
                    company_el = card.find_element(By.CSS_SELECTOR, ".subTitle, .companyName, .company-name")
                    title = title_el.text.strip()
                    company = company_el.text.strip()

                    print(f"\n    📋 {title} @ {company}")

                    # Click to open job
                    title_el.click()
                    human_delay(1.5, 3)

                    # Switch to new tab if opened
                    if len(driver.window_handles) > 1:
                        driver.switch_to.window(driver.window_handles[-1])

                    # Find Apply button
                    apply_btn = None
                    try:
                        apply_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR,
                                ".apply-button, button[type='button'][class*='apply'], #apply-button"))
                        )
                    except TimeoutException:
                        print(f"    ℹ️  No direct apply button found")
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        continue

                    if pause_before_apply:
                        inp = input(f"    ⏸️  Apply to {title} @ {company}? (y/n/q): ").strip().lower()
                        if inp == "q":
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                            return applied_jobs
                        if inp != "y":
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                            continue

                    apply_btn.click()
                    human_delay(1.5, 3)

                    # Handle any confirmation modals
                    try:
                        confirm = driver.find_element(By.CSS_SELECTOR,
                            ".apply-button-modal button, [class*='confirm']")
                        confirm.click()
                        human_delay(1, 2)
                    except Exception:
                        pass

                    print(f"    ✅ APPLIED: {title} @ {company}")
                    applied_jobs.append({
                        "title": title,
                        "company": company,
                        "source": "Naukri",
                        "status": "applied",
                        "applied_at": datetime.now().isoformat(),
                        "url": driver.current_url
                    })

                    human_delay(3, 7)

                    # Close tab and go back
                    if len(driver.window_handles) > 1:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])

                except Exception as e:
                    print(f"    ⚠️  Error processing job card: {e}")
                    try:
                        if len(driver.window_handles) > 1:
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                    except Exception:
                        pass
                    continue

        except Exception as e:
            print(f"  ❌ Search error for '{role}': {e}")
            continue

    return applied_jobs


def run_naukri_applier(profile: dict, search_config: dict, secrets: dict,
                        resume_path: str, max_applications: int = 15,
                        pause_before_apply: bool = True) -> list[dict]:
    '''
    Main Naukri apply pipeline.
    Returns list of application records.
    '''
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium not available. Install with: pip install undetected-chromedriver selenium")
        return []

    options = uc.ChromeOptions()
    options.add_argument("--window-size=1280,900")
    driver = uc.Chrome(options=options)

    applied_jobs = []

    try:
        login_ok = naukri_login(
            driver,
            secrets.get("NAUKRI_EMAIL"),
            secrets.get("NAUKRI_PASSWORD")
        )

        if not login_ok:
            input("Please log in manually in the browser, then press ENTER...")

        # Update profile resume first
        update_naukri_profile_resume(driver, resume_path)

        # Apply to jobs
        applied_jobs = search_and_apply_naukri(
            driver, profile, search_config, max_applications, pause_before_apply
        )

    except KeyboardInterrupt:
        print("\n⏹️  Stopped by user")
    finally:
        driver.quit()

    print(f"\n🎉 Naukri: Applied to {len(applied_jobs)} jobs")
    return applied_jobs
