<?php
header('Content-Type: text/html; charset=utf-8');
header('X-Content-Type-Options: nosniff');header('X-Frame-Options: DENY');header('Referrer-Policy: no-referrer');header('Cache-Control: no-store');
header("Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://*.tile.openstreetmap.org https://server.arcgisonline.com https://mapsneu.wien.gv.at; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'");
readfile(__DIR__.'/view.html');
