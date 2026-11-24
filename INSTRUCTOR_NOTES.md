# Instructor notes

**FIN 4600 · Lab 3 · Financial Data Analytics**

Private notes for running this lab. Delete this file from the student-facing
repository if you would rather they not read it — though most of it is
pedagogy rather than answers, so leaving it in is defensible.

---

## Before the semester

1. **Run everything once.**

   ```bash
   uv sync
   uv run python scripts/run_all_notebooks.py
   ```

   Takes about three minutes. Do this in the week before class, not the night
   before, because `uv sync` resolves to current package versions and the
   occasional upstream change will need a small edit.

2. **Freeze the versions if you want zero surprises.** `uv.lock` is committed,
   so students already get identical versions. If you want to pin harder across
   semesters, do not delete or regenerate the lock file.

3. **Push to GitHub** under your own account or an MTU organisation. Students
   fork it; `SETUP.md` Part 4 walks them through that.

4. **Decide how work comes back.** Three workable options:

   | Approach | How it works | Trade-off |
   |---|---|---|
   | **Fork + link** (documented in SETUP.md) | Students fork, work, push, submit the URL in Canvas | Simplest for you; students own a public portfolio piece |
   | **GitHub Classroom** | Auto-creates a private repo per student from this one as a template | Best roster integration; needs an organisation and 30 minutes of setup |
   | **Notebook upload** | Students attach the `.ipynb` to Canvas | Zero Git friction; loses the version-control learning, which is half the point |

   Whichever you choose, say it once clearly in the syllabus. Mixed instructions
   here generate more email than the Python does.

---

## Timing

Measured on a clean environment; add 50% for a room full of first-time users.

| Notebook | Run time | Class time | Notes |
|---|---|---|---|
| 00 Environment check | 10 s | 15 min | Do this in class. It is where you catch the broken setups. |
| 01 pandas fundamentals | 25 s | 60–75 min | Densest notebook. Consider splitting at §6. |
| 02 Returns and risk | 35 s | 60–75 min | Mostly review of FIN 4000/4500 content in code. Can be assigned. |
| 03 Features and targets | 20 s | 45–60 min | Conceptually hardest. Do §3–4 live. |
| 04 Credit risk ML | 60 s | 75–90 min | The core ML session. §10 is the highest-value part. |
| 05 Market ML | 45 s | 60 min | Largely discussion. Good for a flipped session. |

---

## The first session: triage, not teaching

Expect roughly a third of a class to hit a setup problem. Front-load it.

**Ten minutes before class**, write on the board:

> If you are stuck, open `SETUP.md`, find the **Troubleshooting** section, and
> read the entry matching your error message before raising your hand.

**The failures you will actually see**, in descending order of frequency:

1. **`uv` not found** — they did not open a new terminal. Fix: close and reopen
   the terminal. Resolves about half of all reports.
2. **Wrong kernel selected** — the notebook is on a system Python instead of
   `.venv`, so `import pandas` fails. Cell 1 of notebook 00 detects this and
   prints a warning; teach them to read it.
3. **Opened a file rather than the folder** — `FileNotFoundError` on the first
   `read_csv`. Fix: File → Open Folder → the repository root.
4. **Repository inside OneDrive** — file locking and sync conflicts produce
   bizarre intermittent errors. Fix: move it to a plain local folder. Worth
   saying out loud on day one; it saves a support ticket per class.
5. **Campus network blocking the install** — rare, but `uv sync` can fail behind
   a guest network or an aggressive VPN. Fix: eduroam or a phone hotspot.

**Have a fallback ready.** If a student's machine is genuinely broken 20
minutes in, park them in Google Colab for that session
(`File → Open notebook → GitHub`, paste the repo URL) and fix the local install
in office hours. Colab has pandas and scikit-learn preinstalled; they will only
need to fetch the data files. Do not let one broken laptop consume the session.

---

## What to demonstrate live

If you only have time to run a handful of cells in front of the room, run these.
They are the cells that change how students think.

**Notebook 01 §9 — the Chevron Thanksgiving example.** US markets were closed on
27 November 2014; OPEC met that day and declined to cut production; energy names
gapped down on the Friday. Forward fill puts the last traded price in the hole.
Interpolation puts a number part-way to the post-announcement price — a price
nobody could have known. It is a one-table demonstration of look-ahead bias with
a real event attached, and students remember it.

**Notebook 03 §4 — the cheating feature.** A trailing 5-day average correlates
about −0.01 with tomorrow's return. Change one argument to `center=True` and it
correlates about −0.63. Ask the room what they would have concluded if they had
found the second number in their own project. Then delete the column in front of
them.

**Notebook 04 §10 — the profit curve.** Students arrive believing that better
models come from better hyperparameters. Show them that moving the approval
threshold from 0.5 to about 0.35 is worth more than every model comparison in
the notebook combined, and that the optimum has a closed form, $M/(M+L)$, that
falls out of one line of algebra with the loan amount cancelling.

**Notebook 05 §1 — the table where nothing works.** Let the silence sit for a
moment. Then ask: *if your project produces this table, what do you write up?*
The answer — "you write up exactly this, with the evidence" — is the single most
professionally useful thing in the lab.

---

## Questions students reliably ask

**"Why is the data from 2013–2018? Can we use current prices?"**
Yes, via `scripts/refresh_data.py`, and the script's docstring explains why the
repository ships static files anyway. The honest answer is reproducibility:
committed data means that when your number differs from your neighbour's, it is
your code. Add that free market-data APIs break without notice, and that
"the data source changed" is not an acceptable reason for a risk report to be
late.

**"Couldn't we do better with a neural network?"**
On 1,410 monthly observations and twelve features, no. Deep learning needs data
volume this problem does not have, and notebook 04 already shows gradient
boosting failing to meaningfully beat logistic regression on 1,000 rows. The
useful follow-up question is what data *would* change the answer — and that
leads to a good discussion about alternative data and why it is expensive.

**"So machine learning doesn't work in finance?"**
It works extremely well in fraud detection, credit, AML transaction monitoring,
client churn and next-best-action, document processing, and operational risk —
everywhere the relationship is stable and nobody is competing it away. It works
poorly on price direction, for reasons that are structural rather than
technical. Notebook 05 makes exactly this distinction; it is worth reinforcing.

**"Can I use ChatGPT/Claude for this?"**
Your AI policy governs. Two things worth adding regardless: (a) an LLM will
cheerfully write a backtest with look-ahead bias in it, so notebook 03 is the
skill that lets them catch it; (b) asking a model to explain an error message is
a legitimate and efficient use, and pretending otherwise just moves it
underground.

**"Why logistic regression when random forests are better?"**
Notebook 04 shows the forest is *not* clearly better here once you cross-
validate — the fold-to-fold spread exceeds the gap between models. And under
the Fair Credit Reporting Act a declined applicant is entitled to specific
reasons. A coefficient is a reason; a forest is not.

---

## Assessment: run, read, then quiz

The lab is now **run-and-read**. Every line of Python is commented, the
markdown before each code cell gives the background on the packages and
methods (with the machine-learning algorithms covered in depth in notebook 04),
and every exercise has a worked, commented solution followed by a
**Discussion** cell that interprets the actual output. Students run each
notebook, read it, experiment if they like, and then take that notebook's
**comprehension quiz in Canvas**.

The quizzes live in `quizzes/`, which is git-ignored so the answer keys never
reach the public student repository. See `quizzes/README.md` for how to edit
them, rebuild the Canvas QTI packages (`uv run python scripts/build_quizzes.py`)
and import them.

| Notebook | Quiz questions | Multiple choice | True/false |
|---|---|---|---|
| 00 | 8 | 5 | 3 |
| 01 | 24 | 17 | 7 |
| 02 | 24 | 17 | 7 |
| 03 | 23 | 16 | 7 |
| 04 | 24 | 16 | 8 |
| 05 | 23 | 16 | 7 |

The questions mix three kinds: what specific lines of code do, how the
methods work, and what the results mean for a finance professional. Numbers
quoted in questions come from executing the notebooks with the committed data
and `uv.lock` versions. If you change the data or upgrade packages, re-run
`scripts/run_all_notebooks.py` and spot-check the quizzes.

### What the worked solutions show

Useful for leading discussion, or if you want students to explain a solution
in their own words as a short written follow-up.

| Notebook | Exercise | Result in the worked solution |
|---|---|---|
| 01 | Ex 1 — XOM 2015 filter | 24 days above 20m shares; uses `.dt.year` and a boolean mask, not a loop |
| 01 | Ex 2 — highest average range | BAC, GS, CAT; calmest KO, PG, MCD |
| 01 | Ex 3 — trading days per ticker | All 30 have 1,259 days, which is itself a sign of survivorship bias |
| 02 | Ex 1 — recompute for 2015 | Only 13 of 30 positive Sharpe ratios; rank correlation with the five-year ranking 0.43. The ranking is unstable, which is the point |
| 02 | Ex 2 — Calmar ratio | Computed on a copy so the saved `risk_return_stats.csv` is untouched; UNH moves to first, BAC falls six places |
| 02 | Ex 3 — defensive sector betas | Utilities ≈0.58, Staples ≈0.71, Financials ≈1.37; discussion covers bond-proxy behaviour in 2013–2018 |
| 03 | Ex 1 — leakage triage | **The most diagnostic exercise in the lab.** Item 2 (`close.mean()` over the whole sample) is the leak; items 1 and 3 are fine |
| 03 | Ex 2 — invent a feature | Volatility term spread and a January dummy; the January "signal" is shown to come from two bad months |
| 04 | Ex 1 — add back the protected variable | Test AUC 0.800 → 0.799, so it barely helps; the discussion explains why ECOA prohibits it regardless |
| 04 | Ex 2 — LGD 0.35 | Formula cut-off rises from 0.294 to ≈0.417; approvals 142 → 174 |
| 04 | Ex 3 — depth-3 scorecard | Rules in plain English; AUC cost ≈0.11 on test, ≈0.08 cross-validated |
| 04 | Ex 4 — fixed origination cost | Amount-dependent rule declines 33 small loans and adds ≈1,329 DM; break-even loan size 600 DM |
| 05 | Ex 1 — `min_samples_leaf=1` | Train accuracy 1.00, test ≈0.50 (≈0.51 at the default leaf size): overfitting with no signal to lose |
| 05 | Ex 2 — volatility importances | Own 63-day volatility leads; the VIX features matter in a full-data fit but much less on a held-out fold |
| 05 | Ex 3 — third target | Absolute next-month return; baselines named **before** fitting; the forest beats the best baseline in 4 of 5 folds by under 2% in MAE, with negative R². Honest reporting is the point |

---

## Adapting the lab

- **Shorter version:** notebooks 00, 01, 04. That is a complete arc from raw
  data to a deployed-style decision rule, and drops the market-prediction
  material entirely.
- **Investments-flavoured version (FIN 4000):** notebooks 00, 01, 02 with the
  portfolio-optimisation extension in the further-work list.
- **Risk-flavoured version (FIN 4500):** notebooks 02 and 05 Task B, extended
  to GARCH and VaR backtesting.
- **Adding your own data:** drop a CSV in `data/`, document it in
  `data/README.md`, and follow the existing pattern. The `find_repo_root()`
  helper at the top of each notebook means paths keep working wherever the
  notebook is launched from.

---

## Maintenance

- `scripts/run_all_notebooks.py` exits non-zero on any failure, so it drops
  straight into a GitHub Actions workflow if you want CI on the repository.
- The notebooks are committed **without outputs** so that diffs stay readable
  and students see their own results rather than yours. If you prefer to ship
  executed copies, run `run_all_notebooks.py` and save the results to a
  separate `solutions/` branch.
- The chart style lives in `fin4600.mplstyle`. The colour order in it is
  colour-vision-deficiency safe; if you change the colours, keep that property.
