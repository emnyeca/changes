# Third-party notices

This file records third-party software that is bundled with, linked into, or otherwise distributed as part of EUB Changes release builds.

## ireal-musicxml

- Repository: <https://github.com/infojunkie/ireal-musicxml>
- Author: Karim Ratib / infojunkie
- License: GNU General Public License v3.0 only (GPL-3.0-only)
- Purpose in EUB Changes: Converts iReal Pro song or playlist data to MusicXML for import.
- Bundled version: 2.1.1 (`@music-i18n/ireal-musicxml` npm package)

The repository does not contain the converter payload itself; release builds bundle it after staging with `scripts/PrepareBundledIRealMusicXML.ps1`. EUB Changes invokes the converter as an external tool through `tools/eub-ireal-wrapper.mjs` (part of EUB Changes, GPL-3.0) without modifying the upstream sources. The corresponding source code is available from the upstream repository above at the bundled version tag.

## Node.js

- Repository: <https://github.com/nodejs/node>
- License: MIT License and other licenses; see the LICENSE file included in the Node.js distribution
- Purpose in EUB Changes: Runtime used to execute the bundled ireal-musicxml converter.
- Bundled version: portable Windows runtime staged at build time by `scripts/PrepareBundledIRealMusicXML.ps1 -IncludeNode` (default 22.14.0; the exact version is recorded by the staged `tools/bundled/node/LICENSE`)

## Streamlit

- Repository: <https://github.com/streamlit/streamlit>
- License: Apache License 2.0
- Purpose in EUB Changes: Web UI framework used to build the application interface.

## streamlit-desktop-app

- Repository: <https://github.com/whitphx/streamlit-desktop-app>
- Author: Yuichiro Tachibana (whitphx)
- License: MIT License
- Purpose in EUB Changes: Packages the Streamlit app as a standalone Windows desktop executable for distribution.
