# Flight timing and split regression

Two linked Mavic 3 Cine logs distinguish commanded waypoint speed from whole-flight averages. Reference raster: 222 points, 2651.5 m planned route at 3 m/s, nominal 884 s, recorded whole flight 1289 s, battery 95 to 35 percent. Reference double helix: 118 points, 3303 m, 117 points at 5.1 m/s and one at 5 m/s, nominal 648 s, whole flight 754.4 s, battery 95 to 59 percent. These aggregate values contain no private positions or identifiers.

Do not infer cruise speed from total flight distance divided by total duration: transit, climb, turns and hovering are included in the latter. Do not apply the observed battery use or an arbitrary time multiplier to other aircraft, geometries or conditions. Route time continues to use 3D segment length and actual segment speed limits. Transit and user-selected reserve are counted once per flight. Existing explicit photo pauses remain explicit; zero-pause flights have no invented photo dwell.

Minutes mode no longer applies the legacy 150/200-photo limit; it retains the 5000-point geometry bound. Concave outer-boundary connectors and the double-helix top connector now apply to time mode as well as manual mode. Holes and separate cross-grid passes retain their separation. Legacy point-limit mode and manually selected flight counts are preserved.

The speed reset uses the commanded reference speeds, 3 and 5.1 m/s, instead of whole-flight averages 2.6 and 4.3. Saved speeds and time budgets are not silently rewritten. A 15-minute budget cannot accommodate a 21:29 whole flight.

Validation: flights.php covers legacy-cap independence, automatic continuous helix, concave-boundary continuity, nominal times at anonymized reference dimensions, speed scaling, zero photo dwell, transit/reserve limits, manual count, hole exclusion and XML export consistency.
