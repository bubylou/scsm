# Contributing to SCSM

## Issues and Feature Requests
- Check if an there is an existing issue (open or closed).
- Use the issue and feature templates.
- Issues are not for support questions.

## Pull Requests
- Open a pull request as soon as possible.
  - Avoids duplicate work.
  - Can be review and discussed early.
  - Mark [WIP] if not ready to be pulled.
- Use the pull request template.

## Developing
Install SCSM for development:

```
git clone --recurse-submodules https://github.com/bubylou/scsm.git
cd scsm
pip install -r requirements.txt
pip install -e .
```

Run code style checks:

```
tox -e lint
```

Run tests which also does a code style check:

```
tox
```
