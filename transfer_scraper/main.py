import json
import html
import sys
import re
import os.path
from time import sleep
import random
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException


def normalize_class_name(input):
    text = list(input)
    for i in range(1, len(text)):
        if (text[i - 1] == " ") or (text[i - 1] == text[i] == "I"):
            continue
        text[i] = text[i].lower()
    return "".join(text)


def wait(ec):
    WebDriverWait(
        driver, 20, ignored_exceptions=[StaleElementReferenceException]
    ).until(ec)
    sleep(random.uniform(400, 1900) / 1000)


def scrape_course_card(html_id, i, note):
    trs = (
        driver.find_element("id", html_id)
        .find_elements(By.CSS_SELECTOR, ".course-detail")[i]
        .find_elements(By.TAG_NAME, "tr")
    )
    course_name_and_id = trs[0].text.split()
    course_desc = trs[1].text
    course_department = (
        next((x for x in trs if x.text.strip().startswith("Department:")))
        .find_elements(By.TAG_NAME, "td")[1]
        .text.title()
    )
    course_catalog = (
        next((x for x in trs if x.text.strip().startswith("Source catalog:")))
        .find_elements(By.TAG_NAME, "td")[1]
        .text
    )

    k = 1 + next(
        i for i, v in enumerate(course_name_and_id) if bool(re.search(r"\d", v))
    )
    course_id = " ".join(course_name_and_id[0:k])
    course_name = normalize_class_name(" ".join(course_name_and_id[k:]))
    if not note:
        course_credits = ""
        try:
            course_credits = (
                next((x for x in trs if x.text.strip().startswith("Units:")))
                .find_elements(By.TAG_NAME, "td")[1]
                .text.strip()
            )
        except:
            pass

        return {
            "id": course_id,
            "name": course_name,
            "credits": course_credits,
            "desc": course_desc,
            "department": course_department,
            "catalog": course_catalog,
        }
    else:
        course_note = driver.find_element("id", "lblCommentsPublic").text.strip()
        return {
            "id": course_id,
            "name": course_name,
            "note": course_note,
            "desc": course_desc,
            "department": course_department,
            "catalog": course_catalog,
        }


options = webdriver.FirefoxOptions()
user_agent = UserAgent().random
print(f"Using randomized user agent {user_agent}")
options.add_argument("--headless")
options.set_preference("general.useragent.override", user_agent)
driver = webdriver.Firefox(options=options)
driver.get(
    "https://tes.collegesource.com/publicview/TES_publicview01.aspx?rid=f080a477-bff8-46df-a5b2-25e9affdd4ed&aid=27b576bb-cd07-4e57-84d0-37475fde70ce"
)

num_pages = int(
    driver.find_element("id", "lblInstWithEQPaginationInfo").text.split()[-1]
)
print(f"{num_pages} pages detected")

state = {"inst_pg": 1, "inst_idx": 0, "course_pg": 1, "course_idx": 0}
institutions = {}
if os.path.isfile("state.json"):
    with open("state.json", "r") as statejson:
        state = json.load(statejson)
if os.path.isfile("transfer.json"):
    with open("transfer.json", "r") as transferjson:
        institutions = json.load(transferjson)

print("Loaded state: ", end="")
json.dump(state, sys.stdout, indent=4)
print("")

try:
    while state["inst_pg"] <= num_pages:
        if state["inst_pg"] != 1:
            driver.find_element(
                By.CSS_SELECTOR,
                """a[href="javascript:__doPostBack('gdvInstWithEQ','Page$"""
                + str(state["inst_pg"])
                + """')"]""",
            ).click()
            wait(EC.staleness_of(page))
            sleep(random.uniform(16, 25))

        print(driver.find_element("id", "lblInstWithEQPaginationInfo").text)
        page = driver.find_element("id", f"gdvInstWithEQ")

        inst_list_len = len(
            page.find_elements(
                By.CSS_SELECTOR, "a[id^=gdvInstWithEQ_btnCreditFromInstName_]"
            )
        )
        while state["inst_idx"] < inst_list_len:
            institution_link = driver.find_element("id", "gdvInstWithEQ").find_elements(
                By.CSS_SELECTOR, "a[id^=gdvInstWithEQ_btnCreditFromInstName_]"
            )[state["inst_idx"]]
            fields = institution_link.find_element(By.XPATH, "../..").find_elements(
                By.CSS_SELECTOR, ".gdv_boundfield_uppercase"
            )
            inst_name = institution_link.text.title().strip()
            city = fields[0].text.title().strip()
            us_state = fields[1].text.strip()

            institution_link.click()
            wait(EC.staleness_of(institution_link))

            course_pages_len = 1
            try:
                course_pages_len = int(
                    driver.find_element(
                        "id", "lblInstWithEQPaginationInfo"
                    ).text.split()[-1]
                )
            except NoSuchElementException:
                pass

            courses = []
            try:
                courses = institutions[inst_name]["courses"]
            except:
                pass

            while state["course_pg"] <= course_pages_len:
                print(f"Scraping {inst_name}, page {state['course_pg']}/{course_pages_len}")
                course_links_len = len(
                    driver.find_element("id", "gdvCourseEQ").find_elements(
                        By.CSS_SELECTOR, "a[id^=gdvCourseEQ_btnViewCourseEQDetail_]"
                    )
                )
                while state["course_idx"] < course_links_len:
                    course_link = driver.find_element(
                        "id", "gdvCourseEQ"
                    ).find_elements(
                        By.CSS_SELECTOR, "a[id^=gdvCourseEQ_btnViewCourseEQDetail_]"
                    )[
                        state["course_idx"]
                    ]
                    course_link.click()

                    try:
                        wait(
                            EC.element_to_be_clickable(
                                (By.CSS_SELECTOR, ".modal-header button")
                            )
                        )

                        transfer = [
                            scrape_course_card("lblSendCourseEQDetail", i, False)
                            for i in range(
                                0,
                                len(
                                    driver.find_element(
                                        "id", "lblSendCourseEQDetail"
                                    ).find_elements(By.CSS_SELECTOR, ".course-detail")
                                ),
                            )
                        ]

                        rpi = [
                            scrape_course_card("lblReceiveCourseEQDetail", i, True)
                            for i in range(
                                0,
                                len(
                                    driver.find_element(
                                        "id", "lblReceiveCourseEQDetail"
                                    ).find_elements(By.CSS_SELECTOR, ".course-detail")
                                ),
                            )
                        ]

                        begin_date = driver.find_element(
                            "id", "lblBeginEffectiveDate"
                        ).text
                        end_date = driver.find_element("id", "lblEndEffectiveDate").text

                        driver.find_element(
                            By.CSS_SELECTOR, ".modal-header button"
                        ).click()

                        courses += [
                            {
                                "transfer": transfer,
                                "rpi": rpi,
                                "begin": begin_date,
                                "end": end_date,
                            }
                        ]
                        state["course_idx"] += 1
                    except Exception as e:
                        institutions.update(
                            {
                                inst_name: {
                                    "city": city,
                                    "state": us_state,
                                    "courses": courses,
                                }
                            }
                        )
                        raise e
                state["course_idx"] = 0
                state["course_pg"] += 1
            institutions.update(
                {inst_name: {"city": city, "state": us_state, "courses": courses}}
            )
            state["course_pg"] = 1
            state["inst_idx"] += 1

            driver.find_element("id", "btnSwitchView").click()
            wait(
                EC.text_to_be_present_in_element(
                    ("id", "lblInstWithEQPaginationInfo"), str(state["inst_pg"])
                )
            )
        state["inst_idx"] = 0
        state["inst_pg"] += 1

except Exception:
    print("Program hits exception and will terminate")

print("Program will terminate with state: ", end="")
json.dump(state, sys.stdout, indent=4)
with open(f"transfer.json", "w") as transferjson:
    json.dump(institutions, transferjson, indent=4)
with open(f"state.json", "w") as statejson:
    json.dump(state, statejson, indent=4)
driver.quit()
