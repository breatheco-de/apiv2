from datetime import datetime, timedelta

from django.utils import timezone


def days_ago_to_date(findings, string_date):
    number_of_days = int(findings.pop())
    return timezone.now() - timedelta(days=number_of_days)


def today():
    return timezone.now()


def change_format_to_date(findings, string_date):
    dtz = datetime.strptime(string_date, "%B %d, %Y")

    return timezone.make_aware(dtz)


def location_format(findings, string_loc):
    job_id_fecth = list(findings.pop())
    v = "".join(job_id_fecth[1])
    result = v.split(",")
    location = [job_id_fecth[0].replace(".", "").strip().capitalize()]
    loc = location

    for tag in result:
        loc.append(
            tag.replace(" o ", ",")
            .replace(";", ",")
            .replace("-", "', '")
            .replace("'", "")
            .replace("temporarily remote", "Remote")
            .strip()
        )
    return loc


def get_remote_from_strin(findings, string_loc):
    if string_loc == "." or string_loc == ")" or string_loc == "(" or string_loc == "" or string_loc == None:
        string_loc = "Remote"

    return [string_loc.strip()]


def salary(findings, string_salary):
    salary = findings.pop()
    val = []

    for sal in salary:
        val += [sal.replace("$", "").replace("K", "").replace(",", "").strip()]

    return val


def salary_month(findings, string_salary):
    salary = findings.pop()
    val = []

    for sal in salary:
        val += [sal.replace("$", "").replace("K", "").strip()]

    return val


def salary_month_only_one(findings, string_salary):
    salary = findings
    val = []

    for sal in salary:
        val += [sal.replace("$", "").replace("K", "").replace(",", "").strip()]

    val += "0"
    return val


_cases_date = {
    r"^(?:Active\s)?(\d{1,2})\+? days? ago": days_ago_to_date,
    r"(.*\s?\d{1,2}\+?,? \d{1,4})": change_format_to_date,
    r"^today": lambda *args, **kwargs: today(),
    r"^Today": lambda *args, **kwargs: today(),
    r"^Just posted": lambda *args, **kwargs: today(),
    r"^just posted": lambda *args, **kwargs: today(),
}

_cases_location = {
    r"(.*\s)?\((.*)\)": location_format,
    r"^\s?(.*)": get_remote_from_strin,
}

_cases_salary = {
    r"^(.*)\s?-\s(.*)\+? a? year": salary,
    r"^(.*)\s?to\s(.*)\+? per? year": salary,
    r"^(.*)\s?-\s(.*)\+? USD/month": salary_month,
    r"^(.*)\s?\+? USD/month": salary_month_only_one,
}
