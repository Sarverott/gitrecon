# Getting started

The core objects of gitrecon, each with a concrete constructor call:

1. `Config` and `load_env()`: paths and credentials
2. `GitHubClient`: REST calls with ETag, pagination and rate-limit waiting
3. models: `User.from_api(...)`, `Repository.from_api(...)`, built by hand too
4. `stars.starred(client, "sarverott")`: repositories a user has starred
5. `RawBuffer`: append-only storage of everything collected

```sh
task launch    # open in Jupyter
task run       # execute headless
```

Next: [activity-labels](../activity-labels/).
