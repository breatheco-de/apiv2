from unittest.mock import patch, call, MagicMock
from ...actions import save_data
from ..mixins import JobsTestCase
from breathecode.tests.mocks import (
    REQUESTS_PATH,
    apply_requests_post_mock,
)

JOBS = [{
    'Searched_job': 'junior web developer',
    'Job_title': 'Desarrollador Full-Stack',
    'Location': 'Santiago (temporarily remote)',
    'Company_name': 'Centry',
    'Post_date': 'January 19, 2022',
    'Extract_date': '2022-01-30',
    'Job_description': '',
    'Salary': '$1800 - 2100 USD/month',
    'Tags': ['api', 'back-end', 'full-stack', 'git', 'java', 'mvc', 'python', 'ruby'],
    'Apply_to':
    'https://www.getonbrd.com/jobs/programming/desarrollador-full-stack-developer-centry-santiago',
    '_type': 'dict'
}, {
    'Searched_job':
    'junior web developer',
    'Job_title':
    'Desarrollador Full-Stack Python/React',
    'Location':
    'Remote',
    'Company_name':
    'Alluxi',
    'Post_date':
    'January 14, 2022',
    'Extract_date':
    '2022-01-30',
    'Job_description':
    'Al menos 1 año de experiencia trabajando con Python y Django Al menos 1 año de experiencia trabajando con React.js Experiencia desarrollando APIs REST Ingles Conversacional Buscamos un desarrollador responsable, autodidacta, proactivo, eficiente y organizado.',
    'Salary':
    '$1800 - 2000 USD/month',
    'Tags':
    ['api', 'back-end', 'django', 'english', 'front-end', 'full-stack', 'javascript', 'python', 'react'],
    'Apply_to':
    'https://www.getonbrd.com/jobs/programming/desarrollodor-fullstack-python-react-alluxi-remote',
    '_type':
    'dict'
}, {
    'Searched_job':
    'junior web developer',
    'Job_title':
    'Full-Stack Developer',
    'Location':
    'Santiago',
    'Company_name':
    'AAXIS Commerce',
    'Post_date':
    'January 17, 2022',
    'Extract_date':
    '2022-01-30',
    'Job_description':
    'Four-year degree in any computer science-related field or equivalent experience. At least 3-year solid front-end developer as well as back-end full stack developer. Relevant experience working with PHP/Symfony (if it is in Magento or Oro Commerce, even better). Familiar with responsive/adaptive design and mobile development best practices. Web and mobile development, familiar with front+back end developing and data interaction.  Experience with Express, Redis. and Node.js, mainframe (React, Angular, Knockout) preferred for React.',
    'Salary':
    'Not supplied',
    'Tags': [
        'angularjs', 'back-end', 'express', 'front-end', 'full-stack', 'javascript', 'magento',
        'mobile development', 'node.js', 'php', 'react', 'redis', 'responsive', 'symfony', 'ui design'
    ],
    'Apply_to':
    'https://www.getonbrd.com/jobs/programming/full-stack-developer-aaxis-commerce-santiago-3c8e',
    '_type':
    'dict'
}, {
    'Searched_job': 'junior web developer',
    'Job_title': 'Pentester Cybersecurity',
    'Location': 'Remote (Chile)',
    'Company_name': 'Rule 1 Ventures',
    'Post_date': 'November 05, 2021',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'Salary': 'Not supplied',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.getonbrd.com/jobs/cybersecurity/security-engineer-rule-1-ventures-remote',
    '_type': 'dict'
}, {
    'Searched_job': 'junior web developer',
    'Job_title': 'Pentester Cybersecurity',
    'Location': 'Remote (Chile, Venezuela)',
    'Company_name': 'Rule 1 Ventures',
    'Post_date': 'November 05, 2021',
    'Extract_date': '2022-01-30',
    'Job_description': 'Vuln exploitation Security reports',
    'Salary': '$1800 - 2000 a year',
    'Tags': ['back-end', 'cybersecurity', 'english', 'pentesting', 'python'],
    'Apply_to': 'https://www.getonbrd.com/jobs/cybersecurity/security-engineer-rule-1-ventures-remote',
    '_type': 'dict'
}, {
    'Searched_job': 'junior web developer',
    'Job_title': 'Front-end Developer',
    'Location': '.',
    'Company_name': 'ID Business Intelligence',
    'Post_date': 'January 24, 2022',
    'Extract_date': '2022-01-30',
    'Job_description':
    'Manejo de Git Flow. (~°-°)~ Dominar a profundidad CSS y JS (mínimo 1 año) Experiencia con React Experiencia consumiendo Web Service (Rest) Preocuparse por entregar productos de calidad.',
    'Salary': '$1800 - k2000 per year',
    'Tags': ['api', 'css', 'front-end', 'git', 'javascript', 'react'],
    'Apply_to': 'https://www.getonbrd.com/jobs/programming/fronted-developer-id-business-intelligence-remote',
    '_type': 'dict'
}, {
    'Searched_job':
    'junior web developer',
    'Job_title':
    'Junior Web Developer',
    'Location':
    None,
    'Company_name':
    'Reign',
    'Post_date':
    'January 29, 2022',
    'Extract_date':
    '2022-01-30',
    'Job_description':
    '',
    'Salary':
    '18000 USD/month',
    'Tags': [
        'angularjs', 'api', 'back-end', 'ci/cd', 'css', 'docker', 'front-end', 'html5', 'javascript', 'json',
        'mongodb', 'node.js', 'nosql', 'postgresql', 'react', 'responsive', 'ui design', 'virtualization'
    ],
    'Apply_to':
    'https://www.getonbrd.com/jobs/programming/junior-web-developer-reign-remote',
    '_type':
    'dict'
}]

spider = {'name': 'getonboard', 'zyte_spider_number': 3, 'zyte_job_number': 0}
zyte_project = {'zyte_api_key': 1234567, 'zyte_api_deploy': 11223344}
platform = {'name': 'getonboard'}


class ActionSaveDataTestCase(JobsTestCase):
    @patch('breathecode.jobs.actions.save_data', MagicMock())
    def test_save_data__without_spider(self):

        model = self.bc.database.create(spider=spider, zyte_project=zyte_project, platform=platform)

        result = save_data(model.spider, JOBS)
        self.assertEqual(result, 6)
