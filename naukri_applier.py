"""
naukri_applier.py
Selenium bot for applying to jobs on Naukri.com.
Fixed: search selectors, safe quit, verbose error logging.
"""

import time
import random
import os
from datetime import datetime

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import (
        TimeoutException, NoSuchElementException,
        StaleElementReferenceException
    )
    SELENIUM_AVAILABLE = True
except ImportError as e:
    SELENIUM_AVAILABLE = False
    print(f"⚠️  Selenium import failed: {e}")
    print("    Run: pip install undetected-chromedriver selenium setuptools")


def human_delay(min_sec: float = 0.8, max_sec: float = 2.5) -> None:
    time.sleep(random.uniform(min_sec, max_sec))


def type_like_human(element, text: str) -> None:
    try:
        element.clear()
        for char in str(text):
            element.send_keys(char)
            time.sleep(random.uniform(0.04, 0.13))
    except Exception:
        pass


def safe_quit(driver) -> None:
    try:
        driver.quit()
    except Exception:
        pass


def get_button(driver, *keywords):
    """Find visible, enabled button matching any keyword."""
    try:
        for btn in driver.find_elements(By.TAG_NAME, "button"):
            try:
                if not btn.is_displayed() or not btn.is_enabled():
                    continue
                label = (btn.get_attribute("aria-label") or "").lower()
                text  = (btn.text or "").strip().lower()
                for kw in keywords:
                    if kw.lower() in label or kw.lower() in text:
                        return btn
            except StaleElementReferenceException:
                continue
    except Exception:
        pass
    return None


# ── Login ──────────────────────────────────────────────────────────────────

def naukri_login(driver, email: str, password: str) -> bool:
    try:
        driver.get("https://www.naukri.com/nlogin/login")
        human_delay(2, 4)

        # Accept cookies if prompted
        try:
            driver.find_element(By.ID, "acceptCookies").click()
            human_delay(0.5, 1)
        except Exception:
            pass

        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "usernameField"))
        )
        type_like_human(email_field, email)
        human_delay(0.5, 1.2)

        type_like_human(driver.find_element(By.ID, "passwordField"), password)
        human_delay(0.5, 1.0)

        driver.find_element(By.XPATH, "//button[@type='submit']").click()
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


# ── Profile resume update ──────────────────────────────────────────────────

def update_naukri_profile_resume(driver, resume_path: str) -> bool:
    try:
        driver.get("https://www.naukri.com/mnjuser/profile")
        human_delay(3, 5)

        upload = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        upload.send_keys(os.path.abspath(resume_path))
        human_delay(2, 4)

        try:
            save = driver.find_element(
                By.CSS_SELECTOR, ".saveProfileBtn, [class*='save']")
            save.click()
            human_delay(2, 3)
        except Exception:
            pass

        print("✅ Naukri profile resume updated")
        return True

    except Exception as e:
        print(f"⚠️  Could not update Naukri resume: {e}")
        return False


# ── Search and apply ───────────────────────────────────────────────────────

def search_and_apply_naukri(driver, profile: dict, search_config: dict,
                             max_applications: int = 15,
                             pause_before_apply: bool = False) -> list:
    """
    Searches for jobs on Naukri and applies using 1-click apply.
    Returns list of application records.
    """
    applied_jobs = []
    roles        = profile.get("target_roles", [])[:3]
    location     = search_config.get("naukri_location", "India")
    exp_years    = int(profile.get("years_of_experience", 2))

    for role in roles:
        if len(applied_jobs) >= max_applications:
            break

        print(f"\n  🔍 Naukri search: {role} in {location}")

        search_url = (
            f"https://www.naukri.com/{role.lower().replace(' ', '-')}"
            f"-jobs-in-{location.lower()}?experience={exp_years}"
        )

        try:
            driver.get(search_url)
            human_delay(2, 4)

            # ── Get job cards ──────────────────────────────────────────────
            # Try multiple selector variants for Naukri's evolving UI
            job_cards = []
            for card_sel in [
                ".jobTuple",
                "article.jobTupleHeader",
                ".job-container",
                ".srp-jobtuple-wrapper",
                "[class*='jobTuple']",
            ]:
                try:
                    job_cards = WebDriverWait(driver, 8).until(
                        EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, card_sel)
                        )
                    )
                    if job_cards:
                        break
                except TimeoutException:
                    continue

            if not job_cards:
                print(f"    ⚠️  No job cards found for '{role}' — "
                      "Naukri UI may have changed")
                continue

            print(f"    Found {len(job_cards)} jobs")

            for card in job_cards[:10]:
                if len(applied_jobs) >= max_applications:
                    break

                title, company = "", ""
                try:
                    # Try multiple title selectors
                    for t_sel in [".title", "a.title", ".jobTitle",
                                  "[class*='title']", "a[title]"]:
                        try:
                            title_el = card.find_element(By.CSS_SELECTOR, t_sel)
                            title    = title_el.text.strip()
                            if title:
                                break
                        except Exception:
                            continue

                    # Try multiple company selectors
                    for c_sel in [".subTitle", ".companyName",
                                  ".company-name", "[class*='company']"]:
                        try:
                            company = card.find_element(
                                By.CSS_SELECTOR, c_sel).text.strip()
                            if company:
                                break
                        except Exception:
                            continue

                    if not title:
                        continue

                    print(f"\n    📋 {title} @ {company}")

                    # Click job title to open
                    for t_sel in [".title", "a.title", ".jobTitle",
                                  "[class*='title']"]:
                        try:
                            card.find_element(By.CSS_SELECTOR, t_sel).click()
                            human_delay(1.5, 3)
                            break
                        except Exception:
                            continue

                    # Switch to new tab
                    if len(driver.window_handles) > 1:
                        driver.switch_to.window(driver.window_handles[-1])

                    # Find Apply button
                    apply_btn = None
                    for a_sel in [
                        ".apply-button",
                        "button[type='button'][class*='apply']",
                        "#apply-button",
                        "[class*='applyBtn']",
                        "button[class*='Apply']",
                    ]:
                        try:
                            apply_btn = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable(
                                    (By.CSS_SELECTOR, a_sel)
                                )
                            )
                            break
                        except TimeoutException:
                            continue

                    if not apply_btn:
                        apply_btn = get_button(driver, "apply")

                    if not apply_btn:
                        print(f"    ℹ️  No apply button found for: {title}")
                        if len(driver.window_handles) > 1:
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                        continue

                    if pause_before_apply:
                        inp = input(
                            f"    ⏸️  Apply to {title} @ {company}? (y/n/q): "
                        ).strip().lower()
                        if inp == "q":
                            if len(driver.window_handles) > 1:
                                driver.close()
                                driver.switch_to.window(driver.window_handles[0])
                            return applied_jobs
                        if inp != "y":
                            if len(driver.window_handles) > 1:
                                driver.close()
                                driver.switch_to.window(driver.window_handles[0])
                            continue

                    apply_btn.click()
                    human_delay(1.5, 3)

                    # Handle confirmation modal
                    try:
                        confirm = driver.find_element(
                            By.CSS_SELECTOR,
                            ".apply-button-modal button, [class*='confirm']"
                        )
                        confirm.click()
                        human_delay(1, 2)
                    except Exception:
                        pass

                    print(f"    ✅ APPLIED: {title} @ {company}")
                    applied_jobs.append({
    "title":       title,
    "company":     company,
    "location":    location,
    "source":      "Naukri",
    "status":      "applied",
    "applied_at":  datetime.now().isoformat(),
    "apply_link":  driver.current_url,
    "match_score": None,
    "match_reason": "",
    "job_id":      "",
})

                    human_delay(3, 7)

                    if len(driver.window_handles) > 1:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])

                except StaleElementReferenceException:
                    continue
                except Exception as e:
                    print(f"    ⚠️  Error on job card: {e}")
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


# ── Main ───────────────────────────────────────────────────────────────────

def run_naukri_applier(profile: dict, search_config: dict, secrets: dict,
                        resume_path: str, max_applications: int = 15,
                        pause_before_apply: bool = False) -> list:
    """
    Main Naukri apply pipeline.
    Returns list of application records.
    """
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium not available. "
              "Run: pip install undetected-chromedriver selenium setuptools")
        return []

    options = uc.ChromeOptions()
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = uc.Chrome(options=options)
    driver.implicitly_wait(3)

    applied_jobs = []

    try:
        login_ok = naukri_login(
            driver,
            secrets.get("NAUKRI_EMAIL", ""),
            secrets.get("NAUKRI_PASSWORD", "")
        )
        if not login_ok:
            input("Please log in manually in the browser, then press ENTER...")

        update_naukri_profile_resume(driver, resume_path)

        applied_jobs = search_and_apply_naukri(
            driver, profile, search_config,
            max_applications, pause_before_apply
        )

    except KeyboardInterrupt:
        print("\n⏹️  Stopped by user")
    finally:
        safe_quit(driver)

    print(f"\n🎉 Naukri: Applied to {len(applied_jobs)} jobs")
    return applied_jobs
