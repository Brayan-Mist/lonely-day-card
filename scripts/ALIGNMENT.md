# LRC alignment

Python 3.11 virtual environment:

```powershell
py -3.11 -m venv .venv-align
.\.venv-align\Scripts\python.exe -m pip install -r requirements-align.txt
```

Generate LRC:

```powershell
.\.venv-align\Scripts\python.exe .\scripts\align_lrc.py `
  .\assets\lonely-day.mp3 `
  .\lyrics.txt `
  -o .\assets\lonely-day.lrc `
  --model base `
  --language en
```

The lyrics text file must contain one sung line per line, in the exact song order.
The page automatically loads `assets/lonely-day.lrc` when it exists.

If the source is copied Genius-style markdown, clean it first:

```powershell
.\.venv-align\Scripts\python.exe .\scripts\clean_genius_markdown.py `
  .\lyrics-raw.md `
  -o .\lyrics.txt
```

Cut a 3-second manual-check clip around a timestamp:

```powershell
.\.venv-align\Scripts\python.exe .\scripts\cut_lrc_preview.py `
  .\assets\lonely-day.mp3 `
  "[00:16.42]Such a lonely day" `
  -o .\preview_00_16.mp3
```

Serve the postcard through local HTTP so the browser can fetch the `.lrc` file:

```powershell
python -m http.server 4173 --bind 127.0.0.1
```

Then open `http://127.0.0.1:4173/`.
