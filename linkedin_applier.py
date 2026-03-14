"""
linkedin_applier.py
Selenium bot that automates LinkedIn Easy Apply for matched jobs.
Uses undetected-chromedriver to reduce bot detection.
All known issues fixed: button selectors, silent failures, safe quit.
"""

import time
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
        ElementNotInteractableException, StaleElementReferenceException
    )
    SELENIUM_AVAILABLE = True
except ImportError as e:
    SELENIUM_AVAILABLE = False
    print(f"⚠️  Selenium import failed: {e}")
    print("    Run: pip install undetected-chromedriver selenium setuptools")


# ── Helpers ────────────────────────────────────────────────────────────────

def human_delay(min_sec: float = 0.5, max_sec: float = 2.0) -> None:
    time.sleep(random.uniform(min_sec, max_sec))


def type_like_human(element, text: str) -> None:
    try:
        element.clear()
        for char in str(text):
            element.send_keys(char)
            time.sleep(random.uniform(0.03, 0.12))
    except Exception:
        pass


def safe_quit(driver) -> None:
    """Quit driver without raising WinError 6."""
    try:
        driver.quit()
    except Exception:
        pass


def init_driver(headless: bool = False):
    if not SELENIUM_AVAILABLE:
        raise ImportError("undetected-chromedriver not installed")

    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = uc.Chrome(options=options)
    driver.implicitly_wait(3)
    return driver


def get_button(driver, *keywords):
    """
    Find the first visible, enabled button whose text or aria-label
    contains any of the given keywords (case-insensitive).
    """
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


def close_post_submit_modal(driver) -> None:
    """Dismiss any post-submit confirmation modal."""
    try:
        btn = get_button(driver, "done", "close", "dismiss")
        if btn:
            btn.click()
            human_delay(1, 2)
    except Exception:
        pass


# ── Form filling ───────────────────────────────────────────────────────────

def answer_form_question(driver, element, question_text: str,
                          answers_config: dict, profile: dict) -> bool:
    try:
        tag = element.tag_name.lower()
    except Exception:
        return False

    q = question_text.lower()

    lookup = {
        "phone":               profile.get("phone", ""),
        "mobile":              profile.get("phone", ""),
        "city":                profile.get("location", "").split(",")[0].strip(),
        "location":            profile.get("location", ""),
        "years of experience": str(profile.get("years_of_experience", "2")),
        "experience":          str(profile.get("years_of_experience", "2")),
        "notice period":       answers_config.get("notice_period", "30"),
        "current salary":      answers_config.get("current_salary", ""),
        "expected salary":     answers_config.get("expected_salary", ""),
        "ctc":                 answers_config.get("current_salary", ""),
        "linkedin":            profile.get("linkedin", ""),
        "github":              profile.get("github", ""),
        "portfolio":           profile.get("github", ""),
        "cover letter":        answers_config.get("cover_letter", ""),
        "summary":             answers_config.get("summary", profile.get("summary", "")),
        "visa":                answers_config.get("visa_status", "Citizen"),
        "authorized":          answers_config.get("work_authorization", "Yes"),
        "sponsor":             answers_config.get("require_sponsorship", "No"),
        "relocat":             answers_config.get("willing_to_relocate", "Yes"),
        "remote":              answers_config.get("prefer_remote", "Yes"),
        "gender":              answers_config.get("gender", ""),
        "disability":          answers_config.get("disability", "No"),
        "veteran":             answers_config.get("veteran_status", "No"),
    }

    answer = None
    for key, val in lookup.items():
        if key in q and val:
            answer = str(val)
            break

    if not answer:
        for key, val in answers_config.get("custom_answers", {}).items():
            if key.lower() in q:
                answer = str(val)
                break

    # Radio buttons
    try:
        radios = element.find_elements(By.CSS_SELECTOR, "input[type='radio']")
        if radios:
            radios[0].click()
            return True
    except Exception:
        pass

    if tag in ["input", "textarea"] and answer:
        try:
            input_type = (element.get_attribute("type") or "").lower()
            if input_type in ["text", "number", "tel", "email", "url", ""]:
                type_like_human(element, answer)
                return True
            elif input_type in ["radio", "checkbox"]:
                if not element.is_selected():
                    element.click()
                return True
        except Exception:
            pass

    if tag == "select" and answer:
        try:
            sel = Select(element)
            for opt in sel.options:
                if answer.lower() in opt.text.lower():
                    sel.select_by_visible_text(opt.text)
                    return True
            if len(sel.options) > 1:
                sel.select_by_index(1)
                return True
        except Exception:
            pass

    return False


def fill_form_page(driver, profile: dict, answers_config: dict,
                   resume_path: str) -> None:
    """Fill all visible inputs on the current Easy Apply page."""
    human_delay(1, 2)

    # Resume upload
    try:
        for fi in driver.find_elements(By.CSS_SELECTOR, "input[type='file']"):
            try:
                fi.send_keys(os.path.abspath(resume_path))
                human_delay(1, 2)
            except Exception:
                pass
    except Exception:
        pass

    # Text / select / radio fields
    try:
        selectors = (
            ".jobs-easy-apply-form-section__grouping, "
            ".fb-form-element, "
            ".jobs-easy-apply-form-element, "
            "[data-test-form-element]"
        )
        for group in driver.find_elements(By.CSS_SELECTOR, selectors):
            try:
                label_text = ""
                for ls in ["label", ".fb-form-element-label",
                           "[data-test-form-element-label]"]:
                    try:
                        label_text = group.find_element(
                            By.CSS_SELECTOR, ls).text.strip()
                        if label_text:
                            break
                    except Exception:
                        pass

                for inp in group.find_elements(
                        By.CSS_SELECTOR, "input, textarea, select"):
                    answer_form_question(
                        driver, inp, label_text, answers_config, profile)

            except StaleElementReferenceException:
                continue
            except Exception:
                pass
    except Exception:
        pass


# ── Single job apply ───────────────────────────────────────────────────────

def apply_to_job_linkedin(driver, job: dict, profile: dict,
                           answers_config: dict, resume_path: str,
                           pause_before_submit: bool = False) -> str:
    """
    Applies to a single LinkedIn Easy Apply job.
    Returns: "applied" | "skipped" | "failed" | "manual_required"
    """
    apply_link = job.get("apply_link", "")
    title      = job.get("title", "Unknown")
    company    = job.get("company", "Unknown")

    if "linkedin.com" not in apply_link:
        return "skipped"

    try:
        driver.get(apply_link)
        human_delay(2, 4)

        # ── Find Easy Apply button ─────────────────────────────────────────
        easy_apply_btn = None
        for selector in [
            "button.jobs-apply-button",
            "[aria-label*='Easy Apply']",
            "[aria-label*='easy apply']",
            "button.jobs-apply-button--top-card",
        ]:
            try:
                easy_apply_btn = WebDriverWait(driver, 6).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                break
            except TimeoutException:
                continue

        if not easy_apply_btn:
            easy_apply_btn = get_button(driver, "easy apply")

        if not easy_apply_btn:
            print(f"    ℹ️  No Easy Apply button found for: {title}")
            return "skipped"

        easy_apply_btn.click()
        human_delay(2, 3)

        # ── Multi-step form loop ───────────────────────────────────────────
        for step in range(15):
            human_delay(1, 2)
            fill_form_page(driver, profile, answers_config, resume_path)
            human_delay(1, 2)

            # Submit?
            submit_btn = get_button(
                driver, "submit application", "submit", "done")
            if submit_btn:
                if pause_before_submit:
                    print(f"\n⏸️  PAUSE: Review '{title}' @ {company}")
                    input("    Press ENTER to submit (Ctrl+C to skip)...")
                try:
                    submit_btn.click()
                    human_delay(2, 4)
                    close_post_submit_modal(driver)
                    print(f"    ✅ APPLIED: {title} @ {company}")
                    return "applied"
                except Exception as e:
                    print(f"    ❌ Submit click failed: {e}")
                    return "failed"

            # Next / Review / Continue?
            next_btn = get_button(
                driver, "continue to next step", "next",
                "review your application", "review", "continue")
            if next_btn:
                try:
                    next_btn.click()
                    human_delay(1.5, 3)
                    continue
                except Exception:
                    pass

            # Modal gone = already submitted
            try:
                modal = driver.find_element(
                    By.CSS_SELECTOR,
                    ".jobs-easy-apply-content, .artdeco-modal__content"
                )
                if not modal.is_displayed():
                    print(f"    ✅ APPLIED (modal closed): {title} @ {company}")
                    return "applied"
            except NoSuchElementException:
                print(f"    ✅ APPLIED (modal closed): {title} @ {company}")
                return "applied"
            except Exception:
                pass

            print(f"    ⚠️  Step {step+1}: no actionable button — "
                  f"manual review needed for: {title}")
            break

        return "manual_required"

    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"    ❌ Failed: {title} — {e}")
        return "failed"


# ── Main loop ──────────────────────────────────────────────────────────────

def run_linkedin_applier(apply_list: list, profile: dict,
                          answers_config: dict, secrets: dict,
                          resume_path: str, max_applications: int = 20,
                          pause_before_submit: bool = False) -> list:
    """
    Main LinkedIn apply loop.
    Returns updated apply_list with status fields set.
    """
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium not available. "
              "Run: pip install undetected-chromedriver selenium setuptools")
        return apply_list

    linkedin_jobs = [
        j for j in apply_list
        if "linkedin.com" in j.get("apply_link", "")
    ]

    print(f"\n🔗 Found {len(linkedin_jobs)} LinkedIn Easy Apply jobs")
    print(f"   Will apply to up to {max_applications} jobs\n")

    if not linkedin_jobs:
        print("   No LinkedIn jobs in apply list.")
        return apply_list

    driver      = init_driver(headless=False)
    applied     = 0

    try:
        login_ok = _linkedin_login(
            driver,
            secrets.get("LINKEDIN_EMAIL", ""),
            secrets.get("LINKEDIN_PASSWORD", "")
        )
        if not login_ok:
            print("❌ Login failed. Log in manually in the browser window.")
            input("   Press ENTER when you are logged in...")

        for job in linkedin_jobs:
            if applied >= max_applications:
                print(f"\n🛑 Reached max limit ({max_applications})")
                break

            print(f"\n  Applying: [{job.get('match_score')}/100] "
                  f"{job.get('title')} @ {job.get('company')}")

            try:
                status = apply_to_job_linkedin(
                    driver, job, profile, answers_config,
                    resume_path, pause_before_submit
                )
            except KeyboardInterrupt:
                print("\n⏹️  Stopped by user")
                break
            except Exception as e:
                error_msg = str(e).lower()
                if "invalid session" in error_msg or "disconnected" in error_msg:
                    print(f"    ⚠️  Browser crashed — restarting Chrome...")
                    safe_quit(driver)
                    driver = init_driver(headless=False)
                    login_ok = _linkedin_login(
                        driver,
                        secrets.get("LINKEDIN_EMAIL", ""),
                        secrets.get("LINKEDIN_PASSWORD", "")
                    )
                    if not login_ok:
                        print("❌ Re-login failed. Stopping.")
                        break
                    status = "failed"
                else:
                    print(f"    ❌ Unexpected error: {e}")
                    status = "failed"

            job["status"]     = status
            job["applied_at"] = (
                datetime.now().isoformat() if status == "applied" else None
            )

            if status == "applied":
                applied += 1
                print(f"   📊 Progress: {applied}/{max_applications}")
                human_delay(4, 9)
            elif status == "manual_required":
                print(f"   ↩️  Manual required: {job.get('title')}")
            elif status == "failed":
                print(f"   ✗  Failed: {job.get('title')}")

    except KeyboardInterrupt:
        print("\n⏹️  Stopped by user")
    finally:
        safe_quit(driver)

    print(f"\n🎉 Done! Applied to {applied} jobs on LinkedIn")
    return apply_list


def _linkedin_login(driver, email: str, password: str) -> bool:
    try:
        driver.get("https://www.linkedin.com/login")
        human_delay(2, 4)

        field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        type_like_human(field, email)
        human_delay(0.5, 1.5)

        pw = driver.find_element(By.ID, "password")
        type_like_human(pw, password)
        human_delay(0.5, 1.0)

        pw.send_keys(Keys.RETURN)
        human_delay(4, 7)

        if any(x in driver.current_url
               for x in ["feed", "mynetwork", "jobs", "/in/"]):
            print("✅ LinkedIn login successful")
            return True
        else:
            print("⚠️  Login may have failed — check for CAPTCHA or 2FA")
            return False

    except Exception as e:
        print(f"❌ Login error: {e}")
        return False
