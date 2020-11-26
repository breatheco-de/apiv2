## ENDPOINT Tests

* [x]  GET `/cohort/user`: Cohort users can be listed and the following filters must work: `roles` (many roles separated by comma), `cohorts` (many cohort slugs separated by comma, `academy` (many academy slugs separated by comma), `finantial_status` (many comma separated) and `educational_status` (many comma separated).
* [x]  GET `/cohort`: list of cohort objects and the following filters must work: `upcoming=true` (many roles separated by comma), `academy` (many slugs separated by comma, `location` (many slugs separated by comma).
* [ ]  PUT `/user` update basic user info (the email cannot be updated with this endpoint)
* [ ]  PUT `/cohort/<id>` update basic info.
* [x]  POST `/academy/cohort` creates a new cohort, the academy ID will be obtained from the logged user, it cannot be passed on the cohort information.
* [x]  POST `/cohort/<id>/user` creates a new user into a particular cohort, the cohort ID must be specified on the URL and it cannot belong to a different academy than the logged in user.
* [x]  DELETE `/cohort/<id>` deletes a cohort, the cohort must be empty (no students), instead of deleting the cohort it will mark it its status as "DELETED".
* [x]  DELETE `/cohort/<id>/user/<id>` deletes a user from a particular cohort, the authenticated user must be a staff member of the same academy that the cohort belongs to.

## FUNCTION tests
* [ ]  An academy cannot be created without city, and country.
* [ ]  A cohort cannot be created without a certificate, academy.
* [ ]  A student cannot be created without a cohort.
* [ ]  A student cannot be added to a cohort twice.
* [ ]  There can only be one main instructor in a cohort.
* [ ]  A student cannot join a cohort with the same certificate more than once unless it was marked as `POSTPONED` on the previous ones.
* [ ]  A student cannot be marked as 'GRADUATED' if its financial status is 'LATE'
* [ ]  A student cannot be marked as 'GRADUATED" if it has at least 1 assignment with task_type=PROJECT and status TASK_STATUS= PENDING.

## Integration with notify app
* [ ]  When a cohort is created a new slack channel must be created as well.
* [ ]  When a students its added into a cohort, the application must add him/her to the cohort channel on slack.
* [ ]  When a new students gets added into breathecode, it needs to receive a slack invitation automatically, and automatically it needs to get added to the cohort as well.
* [ ]  When a cohort slug its modified, the corresponding slack channel needs to get modified as well.
