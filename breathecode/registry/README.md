# Registry

The registry is breathecode's main catalog of learning content and it's divided [in 4 types](https://github.com/breatheco-de/apiv2/blob/master/breathecode/registry/models.py#L34): Project, Exercise, Lesson, Quiz, Video.

Each of those types has a different behavior.

The mayority of the content is original from breathecode but there are other third party content coming from 4Geeks Academy or some other partners, there is also content from anywere on the internet, speciffically if we really like it and consider the content very effective as a learning tool.

You can retrieve the entire registry with: `GET /registry/asset`, [here is an example](https://breathecode.herokuapp.com/v1/registry/asset).
