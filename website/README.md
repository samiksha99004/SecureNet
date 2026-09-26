# SecureNet website

The public website of SecureNet — live at **https://samiksha99004.github.io/securenet-site/**.

Plain HTML, CSS and JavaScript (no build step):

| File | What it is |
|---|---|
| `index.html` | the whole site: sidebar navigation + Home, Download, About SecureNet, The two models, The app, Technology timeline, About us, Contact us |
| `styles.css` | the SecureNet dark theme and peach theme (same colours and fonts as the app), phone layout |
| `script.js` | theme switch (remembered), mobile menu, highlights the section in view |
| `favicon.svg` | the SecureNet shield |
| `publish.ps1` | publishes these files to GitHub Pages (samiksha99004.github.io/securenet-site) |
| `publish-cloudflare.ps1` | publishes them to Cloudflare Pages: **https://securenet-ids.pages.dev/** (address without a personal name) |

**Preview**: open `index.html` in a browser.

**Publish** (from the project folder):

```powershell
powershell -ExecutionPolicy Bypass -File website\publish.ps1 "What changed"
```

The SecureNet project repository is private, and GitHub's free plan only serves Pages from public
repositories, so only these website files are published, to the public repository
[`samiksha99004/securenet-site`](https://github.com/samiksha99004/securenet-site) (GitHub Pages from its
`main` branch). The download button is disabled ("coming soon") until a Windows installer exists.

**Cloudflare Pages** (address without a personal name): put `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` in
`.local\cloudflare.env` (never committed), then run
`powershell -ExecutionPolicy Bypass -File website\publish-cloudflare.ps1`.
