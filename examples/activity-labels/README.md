# From events to labels

The core pipeline in one notebook, in a throwaway data directory:

1. `EventPoller(client, Feed.parse("public"))`: listen to an Events API feed
2. `gharchive.download_hour(...)`: one hour of all public GitHub events
3. `ActivityGraph`: who touches what, with evidence
4. `Labeler(Thresholds(...))`: labels like `burst`, `push-flood`, `repo-spree`, `bot-like-cadence`

```sh
task launch
task run
```
