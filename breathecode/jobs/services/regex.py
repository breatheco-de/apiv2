import re
from datetime import datetime, timedelta

#TODO IMPORT TIMEZONE AND INCLUDE IN THE FUNCTIONS MODULO DE DJANGO TIMEZONE


def days_ago_to_date(findings, string_date):
    number_of_days = int(findings.pop())
    return datetime.now() - timedelta(days=number_of_days)


def today():
    return datetime.now()


def change_format_to_date(findings, string_date):
    job_id_fecth = findings
    return datetime.strptime(job_id_fecth[0], '%B %d, %Y')


def format_correct_to_date(string_date):
    return string_date


def location_format(findings, string_loc):
    #TODO CHANGE FUNTION NAME TO FORMAT LOCATION
    #TODO VERIFY LINE 40 HAS REDUNDATION
    job_id_fecth = list(findings.pop())
    v = ''.join(job_id_fecth[1])
    v = v.replace(' o ', ',').replace(';', ',').replace('-', '\', \'').strip()
    result = v.split(',')
    location = [job_id_fecth[0].replace('.', '').strip().capitalize()]
    loc = location

    for tag in result:
        loc.append(
            tag.replace(' o ', ',').replace(';', ',').replace('\'',
                                                              '').replace('temporarily remote',
                                                                          'Remote').strip())
    return loc


def remote_to_strin(findings, string_loc):
    #TODO CHANGE NAME REMOTE TO STRING
    if string_loc == '.' or string_loc == ')' or string_loc == '(' or string_loc == '' or string_loc == None:
        string_loc = 'Remote'

    return [string_loc.strip()]


def salary(findings, string_salary):
    #TODO CONSEGUIR EL TIPO DE MONEDA Y GUARDARLO EN LA TABLA DE DATOS
    salary = findings.pop()
    val = []

    for sal in salary:
        val += [sal.replace('$', '').replace('K', '').replace(',', '').strip()]

    return val


def salary_month(findings, string_salary):
    salary = findings.pop()
    val = []

    for sal in salary:
        val += [sal.replace('$', '').replace('K', '').strip()]

    return val


def salary_month_only_one(findings, string_salary):
    salary = findings
    val = []

    for sal in salary:
        val += [sal.replace('$', '').replace('K', '').replace(',', '').strip()]

    val += '0'
    return val


def fetch_id_job_string_to_list(findings, string_loc):
    return list(findings.pop())


_cases_date = {
    '^(?:Active\s)?(\d{1,2})\+? days? ago': days_ago_to_date,
    '^(\d{1,4}-\d{1,2}-\d{1,2}\s\d{1,2}:\d{1,2}:\d{1,2})$': lambda *args, **kwargs: format_correct_to_date(),
    '(.*\s?\d{1,2}\+?,? \d{1,4})': change_format_to_date,
    '^today': lambda *args, **kwargs: today(),
    '^Just posted': lambda *args, **kwargs: today(),
    '^just posted': lambda *args, **kwargs: today(),
}

_cases_location = {
    '(.*\s)?\((.*)\)': location_format,
    '^\s?(.*)': remote_to_strin,
}

_cases_salary = {
    '^(.*)\s?-\s(.*)\+? a? year': salary,
    '^(.*)\s?to\s(.*)\+? per? year': salary,
    '^(.*)\s?-\s(.*)\+? USD/month': salary_month,
    '^(.*)\s?\+? USD/month': salary_month_only_one,
}


#TODO CHANGE NAME
def get_regex_date_from_string(string_date):
    for regex in _cases_date:
        findings = re.findall(regex, string_date)
        if findings:
            return _cases_date[regex](findings, string_date)


def get_salary_format_from_regex(string_salary):
    for regex in _cases_salary:
        findings = re.findall(regex, string_salary)
        if findings:
            return _cases_salary[regex](findings, string_salary)


def get_regex_location_from_string(string_loc):

    for regex in _cases_location:
        findings = re.findall(regex, string_loc)
        if findings:
            return _cases_location[regex](findings, string_loc)
