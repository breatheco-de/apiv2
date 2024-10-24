#! /bin/bash

# check this postgres url in environment variables and add-ons
heroku addons:create heroku-postgresql:standard-0 --follow HEROKU_POSTGRESQL_TEAL_URL --app breathecode-test
heroku pg:wait --app breathecode-test
heroku pg:info --app breathecode-test
heroku maintenance:on --app breathecode-test

# check the current maintenance status
heroku maintenance --app breathecode-test

# here appear the follower name
# wait until the follower is behind by 0 commits, this can take some minutes
heroku pg:info --app breathecode-test

# upgrade the follower to the latest version
heroku pg:upgrade HEROKU_POSTGRESQL_FOLLOWER_URL --app breathecode-test

# wait until the new postgres is upgraded
heroku pg:wait --app breathecode-test

# promote the follower to primary
heroku pg:promote HEROKU_POSTGRESQL_FOLLOWER_URL --app breathecode-test

heroku maintenance:off --app breathecode-test

# destroy the old postgres when you are sure that everything is working
heroku addons:destroy HEROKU_POSTGRESQL_TEAL --app breathecode-test
