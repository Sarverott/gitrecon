# User namespace

> Usernames across platforms, grouped by numeronym paths.

## What it is

`user-namespace/NS/<a12y(user)>/<a12y(platform)>/<md5>.json` - for `UserName` on `github.com`: `NS/u8e/g6-3m/6784ce76fa5dbf3d7e73f94cc2df055f.json`. The platform numeronym is the first character, label lengths joined by `-`, last character (`github.com` -> `g6-3m`). The hash is the MD5 of `"username@platform\n"` lowercased - what `echo "username@github.com" | md5sum` prints. `index.json` maps each username to its identity files. Paths stay in full form; shortening to the bare hash once no collision shows up is left for later. Only public platform accounts are added automatically - no e-mail harvesting.

## Where

`gitrecon.atlas.namespace` (`UserNamespace`, `Identity`, `identity_path()`); the dataset's `user-namespace/README.md`. CLI: `gitrecon atlas update --stars sarverott`.

## Relations

Holds [[identity|identities]]; names use [[a12y]]; an [[area]] of the [[atlas]].
