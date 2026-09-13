# tests/

- `test_jarvis.py` — automated regression tests. Run from the repo root:
  `python -m unittest discover tests`
- `manual/` — hands-on video-pipeline checks that need real media files and
  installed dependencies. Run from the repo root, e.g.
  `python tests/manual/test_trim.py`, after editing the file paths inside to
  point at your own `workspace/` files.
