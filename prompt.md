# Refactor Request

Look at packages/api, restructure this code to make it more AI navigable:

Group the files by domain not by technical terms. For example, right now you have models, routers, schemas, services, etc. This is not fine. The new structure should be:

- app
  - users
    - models.py
    - router.py
    - schema.py
    - services.py
      ...

The domains I think are: users, documents, highlitghts and export.
There should also be a shared folder at the same level as all other domains.
