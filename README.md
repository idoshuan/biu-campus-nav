# מצפן בר־אילן (Bar-Ilan campus navigator)

Single-page app: shows the next class, the walking route on campus, walking time and when to leave.
Classes come from an `.ics` calendar (link, file or pasted text) or are added by hand. Everything is stored in the browser.

- `index.html` – the built app. Open it directly or host it (e.g. GitHub Pages). GPS location works when it is served over https.
- `artifact.html` – same app without the outer HTML shell, for publishing as a claude.ai Artifact (no GPS there).
- `src/app.html` – app source. `data/campus.json` – campus dataset. Rebuild both outputs with `python3 tools/assemble.py`.

## Rebuilding the campus data

`tools/build.py <osm.json> tools/ data/campus.json` turns an OpenStreetMap extract of the campus
(`https://api.openstreetmap.org/api/0.6/map.json?bbox=34.8330,32.0600,34.8575,32.0800`) into the dataset.
Building numbers and names come from the official campus map (`tools/pdf_buildings.py`). Buildings missing from OSM
are placed by a local fit from the illustrated map (typically within 15–35 m) and are shown as dashed circles.

Map data © OpenStreetMap contributors, ODbL.

## Calendar link

The page loads the schedule from an iCal link. Google (and most calendar services) don't let other web pages read
their feeds directly, so deploy `tools/calendar-proxy.js` as a Cloudflare Worker and set `CAL_PROXY` in `src/app.html`
to its URL, then rebuild. The worker only forwards to known calendar hosts. On a claude.ai Artifact the page cannot reach
any outside address, so the calendar link only works on the hosted `index.html`.
