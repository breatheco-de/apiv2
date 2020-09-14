
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