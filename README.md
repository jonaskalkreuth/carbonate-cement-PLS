# carbonate-cement-PLS

> 🚧 Work in progress — scaffolding stage. Full README lands at the end (step 4.6).

Reproduce a peer-reviewed **ATR-IR + PLS** method for quantifying CaCO₃ in
carbonated cement paste — in open-source Python instead of Bruker's commercial
OPUS Quant 2 — hit the same published accuracy, then show *why* the multivariate
model is needed.

Based on the open-access paper (user is first author):
Kalkreuth et al., *J. Am. Ceram. Soc.* 2023, [doi:10.1111/jace.19546](https://doi.org/10.1111/jace.19546).

## Layout

| Path | What |
|------|------|
| `src/` | the package (OPUS loader, preprocessing, PLS, baseline, interpretation) |
| `scripts/` | regenerate figures/tables |
| `tests/` | pytest suite |
| `notebooks/` | narrative walkthrough |
| `reports/` | committed figures/tables |
| `models/` | persisted trained models (gitignored) |
| `data/` | minimal ATR-IR spectra subset (Excel kept local, not published) |

See `SPEC.md` and `design-tree.md` for the plan.

## License

Code: [MIT](LICENSE). Spectral data under `data/`: [CC-BY-4.0](LICENSE-DATA) — cite the paper.

## Setup

```bash
pip install -r requirements.txt
```
