// Package web embeds the static frontend assets (single origin, no CDN).
package web

import "embed"

//go:embed index.html app.js style.css
var FS embed.FS
