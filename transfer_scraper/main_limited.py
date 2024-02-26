import json
import html
import sys
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def normalize_class_name(input):
    text = list(input)
    for i in range(1, len(text)):
        if (text[i - 1] == " ") or (text[i - 1] == text[i] == "I"):
            continue
        text[i] = text[i].lower()
    return "".join(text)

options = webdriver.FirefoxOptions()
#options.add_argument("--headless")
driver = webdriver.Firefox(options=options)

driver.get(
    "https://tes.collegesource.com/publicview/TES_publicview01.aspx?rid=f080a477-bff8-46df-a5b2-25e9affdd4ed&aid=27b576bb-cd07-4e57-84d0-37475fde70ce"
)

institutions = {}

num_pages = int(
    driver.find_element("id", "lblInstWithEQPaginationInfo").text.split()[-1]
)
print(f"{num_pages} pages detected")

for curr_page in range(1, num_pages):
    # WebDriverWait(driver,10).until(EC.text_to_be_present_in_element(("id", "lblInstWithEQPaginationInfo"), str(curr_page)))
    print(driver.find_element("id", "lblInstWithEQPaginationInfo").text)

    page = driver.find_element("id", f"gdvInstWithEQ")

    inst_list = page.find_elements(
        By.CSS_SELECTOR, "a[id^=gdvInstWithEQ_btnCreditFromInstName_]"
    )
    for i in range(0, len(inst_list)):
        institution_link = driver.find_element("id", "gdvInstWithEQ").find_elements(
            By.CSS_SELECTOR, "a[id^=gdvInstWithEQ_btnCreditFromInstName_]"
        )[i]
        fields = institution_link.find_element(By.XPATH, "../..").find_elements(
            By.CSS_SELECTOR, ".gdv_boundfield_uppercase"
        )
        inst_name = institution_link.text.title().strip()
        city = fields[0].text.title().strip()
        state = fields[1].text.strip()

        institution_link.click()
        WebDriverWait(driver, 30).until(EC.staleness_of(institution_link))
        # num_pages_inst = int(driver.find_element("id", "lblInstWithEQPaginationInfo").text.split()[-1])
        courses = []
        for course_link in driver.find_element("id", "gdvCourseEQ").find_elements(
            By.CSS_SELECTOR, "a[id^=gdvCourseEQ_btnViewCourseEQDetail_]"
        ):
            course_fields = course_link.find_element(By.XPATH, "../..").find_elements(
                By.CSS_SELECTOR, ".gdv_boundfield_uppercase"
            )

            begin_date = course_fields[1].text.strip()
            end_date = course_fields[2].text.strip()
            courses_full = course_link.get_attribute("innerHTML").split("<br>")
            transfer = []
            for r in courses_full:
                s = html.unescape(r).split()
                # Figure out course code and credit count delimiters
                k = 0
                while not bool(re.search(r"\d", s[k])):
                    k += 1
                k += 1
                c = -1
                while not bool(re.search(r"\(", s[c])) and -c < len(s):
                    c -= 1

                course_name = normalize_class_name(" ".join(s[k:])).strip()
                course_credit = ""
                if -c < len(s):
                    course_name = normalize_class_name(" ".join(s[k:c])).strip()
                    course_credit = " ".join(s[c:])[1:-1]
                transfer.append({
                    "id": " ".join(s[0:k]),
                    "name": course_name,
                    "credits": course_credit
                })

            rpi_courses_full = course_fields[0].find_element(By.CSS_SELECTOR, "span").get_attribute("innerHTML").split("<br>")
            rpi = []
            for r in rpi_courses_full:
                s = html.unescape(r).split()
                rpi.append({
                    "id": " ".join(s[0:2]),
                    "name": normalize_class_name(" ".join(s[2:-1])).strip()
                })

            partial_courses = [
                {
                    "transfer": transfer,
                    "rpi": rpi,
                    "begin": begin_date,
                    "end": end_date
                }
            ]
            json.dump(partial_courses, sys.stdout, indent=4)
            courses += partial_courses

        driver.find_element("id", "btnSwitchView").click()
        WebDriverWait(driver, 10).until(
            EC.text_to_be_present_in_element(
                ("id", "lblInstWithEQPaginationInfo"), str(curr_page)
            )
        )

        partial = {
            inst_name: {
                "city": city,
                "state": state,
                "courses": courses
            }
        }
        json.dump(partial, sys.stdout, indent=4)
        print("")
        institutions.update(partial)

    if curr_page < num_pages:
        driver.find_element(
            By.CSS_SELECTOR,
            """a[href="javascript:__doPostBack('gdvInstWithEQ','Page$"""
            + str(curr_page + 1)
            + """')"]""",
        ).click()
        WebDriverWait(driver, 10).until(EC.staleness_of(page))

json.dump(institutions, sys.stdout, indent=4)
print("")

driver.quit()
