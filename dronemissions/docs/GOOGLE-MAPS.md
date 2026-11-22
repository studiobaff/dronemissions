# Optional Google Maps

Owner Settings accepts a browser API key and explicit enabled flag. Configure the Maps JavaScript API and billing in Google Cloud, restrict the key to the production website origin and that API. This key is necessarily exposed to authorized browsers; it is stored in private config.json, never in source. Empty input preserves the key, explicit removal deletes it.

Google roadmap, satellite and hybrid appear in the shared project/planner map selector only when enabled. The SDK is loaded on first Google-layer selection. A native Google raster Map stays behind Leaflet route editing, synchronizing center, zoom and resize; native logo and terms remain visible. No undocumented tile endpoint, tile copying or cache is used. Google backgrounds are excluded from the existing PDF-image exporter. Existing base maps remain available on authentication/network errors.

CSP adds a per-response script nonce and Google-specific image/connect/font/frame/worker sources only when enabled. The SDK reuses the nonce. Authentication and API billing must be tested with a configured production key; the browser regression suite uses a synthetic SDK without any real Google request.

Official references:
- https://developers.google.com/maps/documentation/javascript/get-api-key
- https://developers.google.com/maps/documentation/javascript/content-security-policy
- https://developers.google.com/maps/documentation/javascript/maptypes
