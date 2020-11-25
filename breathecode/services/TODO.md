Pruebas a los comandos de slack:

- [ ] If one academy wants to integrate with slack, it needs to create an AcademyUser and that user has to connect thru slack, when the connection is finished a new SlackTeam should be created and connected to the academy.
- [ ] Two AcademyUsers can connect to the same slack team, if they belong to different Academies then each SlackTeam will have a different associated academy.
- [ ] If a user reconnects to slack with the same AcademyUser the credentials should be replaced but the SlackTeam should not be deleted, the new credentials should be assigned to the old SlackTeam.
- [ ] 2 or more academies can connect to the same slack but they will have to have separate connections, thru separate AcademyUser, each connection must create a separate SlackTeam that propably will have the same name, the same slack_id, but not the same internal ID.
- [ ] Once the SlackTeam is created the user can import users from slack (SlackUsers), the imported users will be automatically matched with CohortUsers that belong to the same academy than the SlackTeam.
- [ ] If a breathecode user its not in the academy it should not be linked as a SlackTeamUser for that SlackTeam.
- [ ] Once the SlackTeam is created the user can import channels from slack (SlackChannels), the imported channels will be automatically mateched with Cohorts that belong to the same academy.
- [ ] Command student: Returns the information about a student, but only if the command was called by a staff members of the same academy (AcademyUser).
- [ ] If the system breaks in the midle of synching the users the SlackTeam.sync_status should be INCOMPLETE
- [ ] If a slack user is not matched with a breathecode.user its status should be INCOMPLETE
