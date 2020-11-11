The only certificates the application can generate right now are based on specialties, that is why they are generated under the table UserSpecialty.

- [ ] A certificate can only by issued to a student (no teachers, staff, etc.).
- [ ] A certificate can only be issued to students with status GRADUATED on a cohort that was teaching a syllabus with the same associated certificate.
- [ ] The status of the cohort has to be ENDED for any certificate to be issues to any student.
- [ ] If the cohort language is in spanish, the certificate must be in spanish.
- [ ] The cohort must have a teacher before any certificate can be issue.
- [ ] The Cohort.current_day must be equal to the Certificate.duration_in_days in order to be able to issue a certificate.
- [ ] The student status must be UP_TO_DATE or FULLY_PAID to be able to receive a certificate.
- [ ] The student must have 0 tasks with task_type='PROJECT' and task_status PENDING to be able to receive a certificate.
- [ ] After a certificate has been issues a png must exist on a google bucket.
- [ ] Each certificate must have a unique key.