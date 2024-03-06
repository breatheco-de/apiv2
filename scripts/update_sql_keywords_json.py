import os
import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path

url_source_of_postgres_keywords = 'https://www.postgresql.org/docs/8.1/sql-keywords-appendix.html'

request = requests.get(url_source_of_postgres_keywords, timeout=2)
soup = BeautifulSoup(request.text, features='lxml')

BLACKLIST = {
    'BREAK', 'DBCC', 'DENY', 'OPENDATASOURCE', 'OPENQUERY', 'OPENROWSET', 'SHUTDOWN', 'SP_', 'TRAN', 'WHILE', '—', 'XP_'
}

# https://www.w3schools.com/sql
WHITELIST = [
    'SELECT', 'FROM', 'WHERE', 'AS', 'INNER', 'JOIN', 'ON', 'DISTINCT', 'AND', 'OR', 'NOT', 'ORDER', 'BY', 'IS', 'NULL',
    'TOP', 'LIMIT', 'FETCH', 'FIRST', 'ROWS', 'ONLY', 'PERCENT', 'MIN', 'MAX', 'COUNT', 'AVG', 'SUM', 'LIKE', 'IN',
    'BETWEEN', 'LEFT', 'RIGHT', 'FULL', 'OUTER', 'UNION', 'ALL', 'GROUP', 'HAVING', 'DESC', 'EXISTS', 'ANY', 'CASE',
    'WHEN', 'THEN', 'IFNULL', 'ISNULL', 'COALESCE', 'NVL', 'IIF', 'SOME', 'ASCII', 'CHAR_LENGTH', 'CHARACTER_LENGTH',
    'CONCAT', 'CONCAT_WS', 'FIELD', 'FIND_IN_SET', 'FORMAT', 'INSTR', 'LCASE', 'LENGTH', 'LOCATE', 'LOWER', 'LPAD',
    'LTRIM', 'MID', 'POSITION', 'REPEAT', 'REPLACE', 'REVERSE', 'RPAD', 'RTRIM', 'SPACE', 'STRCMP', 'SUBSTR',
    'SUBSTRING', 'SUBSTRING_INDEX', 'TRIM', 'UCASE', 'UPPER', 'ABS', 'ACOS', 'ASIN', 'ATAN', 'ATAN2', 'CEIL', 'CEILING',
    'COS', 'COT', 'COUNT', 'DEGREES', 'DIV', 'EXP', 'FLOOR', 'GREATEST', 'LEAST', 'LN', 'LOG', 'LOG10', 'LOG2', 'MOD',
    'PI', 'POW', 'POWER', 'RADIANS', 'RAND', 'ROUND', 'SIGN', 'SIN', 'SQRT', 'TAN', 'TRUNCATE', 'ADDDATE', 'ADDTIME',
    'CURDATE', 'CURRENT_DATE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP', 'CURTIME', 'DATE', 'DATEDIFF', 'DATE_ADD',
    'DATE_FORMAT', 'DATE_SUB', 'DAY', 'DAYNAME', 'DAYOFMONTH', 'DAYOFWEEK', 'DAYOFYEAR', 'EXTRACT', 'FROM_DAYS',
    'FROM_DAYS', 'HOUR', 'LAST_DAY', 'LOCALTIME', 'LOCALTIMESTAMP', 'MAKEDATE', 'MAKETIME', 'MICROSECOND', 'MINUTE',
    'MONTH', 'MONTHNAME', 'NOW', 'PERIOD_ADD', 'PERIOD_DIFF', 'QUARTER', 'SECOND', 'SEC_TO_TIME', 'STR_TO_DATE',
    'SUBDATE', 'SUBTIME', 'SYSDATE', 'TIME', 'TIME_FORMAT', 'TIME_TO_SEC', 'TIMEDIFF', 'TIMESTAMP', 'TO_DAYS', 'WEEK',
    'WEEKDAY', 'WEEKOFYEAR', 'YEAR', 'YEARWEEK', 'BIN', 'BINARY', 'CAST', 'CONV', 'CONVERT', 'IF', 'LAST_INSERT_ID',
    'NULLIF'
]

for element in soup.select('td tt'):
    keyword = element.text

    if keyword not in WHITELIST:
        BLACKLIST.add(element.text)

dict = {'whitelist': WHITELIST, 'blacklist': list(BLACKLIST)}

with open(Path(os.getcwd()) / 'breathecode' / 'sql_keywords.json', 'w') as f:
    json.dump(dict, f, indent=4)
