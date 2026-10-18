# Research Frontend

Plain HTML/CSS/JavaScript served by Fastify, embedded unchanged in Streamlit.
No separate bundler or frontend package installation is needed.
Use [the local supervisor](../docs/LOCAL_SETUP.md) for matching API/iframe origins.

The workflow is Select Diseases, Analyze, explicit Review Candidates, Understand
Result. Candidate pagination, Simple/Researcher views and deterministic Research
Takeaway reuse the existing response. Reset clears state and ignores stale results.

`favicon.svg` is the source molecular-network mark. `favicon.ico` contains
16/32/48-pixel versions; `apple-touch-icon.png` is 180x180 and is also the
Streamlit page icon. Fastify serves these under `/frontend/` with binary-safe
MIME types. The mark implies no medical approval.

From root run `node --check frontend/app.js`,
`node --check frontend/explainability.js` and `npm --prefix backend test`.
HTTP/unit checks do not prove visual layout or accessibility; follow
[manual UI acceptance](../docs/sprint6-guided-demo.md).
