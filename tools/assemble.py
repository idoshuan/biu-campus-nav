# Builds the app from src/app.html + data/campus.json:
#   index.html    full standalone document (open locally or host on GitHub Pages; GPS works there)
#   artifact.html body-only version for publishing as a claude.ai Artifact
import json, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
data = json.dumps(json.loads((root / "data/campus.json").read_text()), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
body = (root / "src/app.html").read_text().replace("/*CAMPUS_DATA*/", data)
(root / "artifact.html").write_text(body)
head, sep, rest = body.partition("</style>")
doc = ('<!doctype html>\n<html lang="he" dir="rtl">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
       '<meta name="theme-color" content="#0d6e46">\n' + head + sep + '\n</head>\n<body>\n' + rest + '\n</body>\n</html>\n')
(root / "index.html").write_text(doc)
print("index.html", len(doc.encode()) // 1024, "KB; artifact.html", len(body.encode()) // 1024, "KB")
