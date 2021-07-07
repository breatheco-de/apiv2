# BreatheCode.Admissions

This module take care of the academic side of breathecode: Students, Cohorts, Course (aka: Certificate), Syllabus, etc. These are some of the things you can do with the breathecode.admissions API:

1. Manage Academies (BreatheCode let's you divide the academic operations into several academies normally based on territory, for example: 4Geeks Academy Miami vs 4Geeks Academy Madrid).
2. Manage Academy Staff: There are multiple roles surroing an academy, here you can invite users to one or many academies and assign them roles based on their responsabilities.
4. Manage Students (invite and delete students).
5. Manage Cohorts: Every new batch of students that starts in a classroom with a start and end date is called a "Cohort".

TODO: finish this documentation.


# Commands

#### Sync academies
```
python manage.py sync_admissions academies 
```

Override previous academies
```
python manage.py sync_admissions academies --override
```

#### Sync courses
```
python manage.py sync_admissions certificates
```
#### Sync cohorts
```
python manage.py sync_admissions cohorts
```
#### Sync students
```
python manage.py sync_admissions students --limit=3
```
Limit: the number of students to sync
