# Registry

The registry is breathecode's main catalog of learning content and it's divided [in 4 types](https://github.com/breatheco-de/apiv2/blob/master/breathecode/registry/models.py#L34): Project, Exercise, Lesson, Quiz, Video.

Each of those types has a different behavior.

The mayority of the content is original from breathecode but there are other third party content coming from 4Geeks Academy or some other partners, there is also content from anywere on the internet, speciffically if we really like it and consider the content very effective as a learning tool.

You can retrieve the entire registry with: `GET /registry/asset`, [here is an example](https://breathecode.herokuapp.com/v1/registry/asset).

## Learn.json

All the assets originally made by breathecode or its partners contain a learnp.json file that contains meta-information about the content like title, slug, translation languages, descripcion, difficulty, etc. Here is an example of learn.json file:

```json
{
  "slug": "starwars-data-model-typeorm-node",
  "title": "Data Modeling a StarWars Blog using Node and Typescript",
  "lang": "typescript",
  "difficulty": "easy",
  "duration": 3,
  "graded": false,
  "preview": "https://github.com/breatheco-de/starwars-data-model-typeorm-node/blob/master/assets/preview.png?raw=true",
  "solution": "https://youtube.com?v=asdASD43EF",
  "intro": "https://youtube.com?v=asdASD43EF",
  "technologies": [ "js", "node", "sql"]
}
```

Note: The `solution` and `intro` properties above are optional.


### Enhancing of the learn.json

When breathecode finally syncs the asset with tis main repository it ads new properties to describe the content further, specifically it ads properties like `asset_type` or `visibility` and it renames some other properties like `solution_video_url` instead of just `solution` or `intro_video_url` instead of just `intro`.

```json
{
  "slug": "starwars-data-model-typeorm-node",
  "title": "Data Modeling a StarWars Blog using Node and Typescript",
  "lang": "typescript",
  "asset_type": "PROJECT",
  "visibility": "PUBLIC",
  "url": "https://github.com/breatheco-de/starwars-data-model-typeorm-node",
  "readme_url": "https://raw.githubusercontent.com/breatheco-de/starwars-data-model-typeorm-node/master/README.md",
  "difficulty": "easy",
  "duration": 3,
  "status": "OK",
  "graded": false,
  "gitpod": true,
  "preview": "https://github.com/breatheco-de/starwars-data-model-typeorm-node/blob/master/assets/preview.png?raw=true",
  "solution_video_url": null,
  "intro_video_url": null,
  "translations": [ "us", "es" ],
  "technologies": [ "js", "node", "sql"]
}
```

### Replacing the original learn.json

If a breathecode user contains Github credentials inside the database, it is also possible to validate and sanitize the original project learn.json file and add or fix more properties into it, we don't like to do this a lot because it will make contents dependand of this feature but it makes sense in jsut a few cases like the `translations` property.
