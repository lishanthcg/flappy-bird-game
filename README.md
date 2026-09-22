# Flappy Bird Deluxe

A Pygame game with sound effects, animated backgrounds, pause controls, and browser high scores.

## Run on Windows

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Play in a browser locally

```powershell
powershell -File .\start-web.ps1
```

Open http://localhost:8000 and click the page to enable audio. Use the Pygbag server; a plain HTTP server cannot provide its local runtime dependencies.

Controls: Space, Up, X, or click to flap; P or Escape to pause/resume.

## Build the website

```powershell
powershell -File .\start-web.ps1 -BuildOnly
```

Output is in `build/web`. Copy its contents into `docs` to update the published version.

## GitHub Pages

The `docs` folder contains the tested browser build. In repository Settings > Pages, select Deploy from a branch, branch `main`, folder `/docs`, then Save.

The expected URL after enabling Pages is https://lishanthcg.github.io/flappy-bird-game/ .

The browser downloads its Python runtime from the Pygbag CDN, so the first load requires internet access and may take longer. Browser high scores use local storage; desktop scores use the ignored `highscore.txt` file.
