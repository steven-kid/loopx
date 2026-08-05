# LoopX Public Website

This directory owns the React/Vite, public-safe homepage published at the root
of the LoopX GitHub Pages site. The dashboard exporter builds the dashboard
application for `/frontstage/`, then builds this white-mode homepage for the
Pages root.

The Vite base is set by the exporter so links and assets work both at the
repository Pages base (`/loopx/`) and in root-base local previews.

The language switch keeps English as the default entry, then applies a
public-safe Chinese locale in the React app.

The default render intentionally preserves the original dark homepage UI.
White mode is opt-in for local review and future links through `?theme=light`.

The first-run CTA is agent-first. It copies the localized, public-safe setup
contract from the React component so the current agent can install or repair
LoopX, identify its exact host, preserve existing project state, and complete
the host-specific activation packet. The terminal block lower on the page
remains the manual fallback; it does not claim that project connection alone
activates a host loop.

The homepage control-plane diagrams are synthetic UI. The tabbed terminal
replays summarize two public README trajectories; they are curated projections,
not raw session logs. The evidence links use only the two explicitly copied
`docs/assets/long-running-loop-*-trajectory.png` files. The site must not
consume live LoopX state, local status feeds, private registries, raw logs, or
write APIs.
