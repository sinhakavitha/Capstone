# Module 2 — Analytics Pipeline

`01_eda.ipynb` loads the Titanic data once, saves `titanic.csv`, cleans it,
and builds the EDA story. `02_modeling.ipynb` reads that same CSV and runs
the modeling pipeline on top of it.

## Missing values

| Column | % missing | Decision |
|---|---|---|
| `deck` | 77.22% | dropped the column — too sparse to impute, unused downstream |
| `age` | 19.87% | imputed with median (robust to age's skew) |
| `embarked` / `embark_town` | 0.22% | dropped the 2 affected rows |

Threshold used: <5% → drop rows, 5–30% → impute, too sparse → drop column.

## Univariate (age, fare)

IQR outliers: 65 for `age`, 114 for `fare`. Fare's mean (32.10) > median
(14.45) > mode (8.05) → right-skewed, which also explains its higher outlier
count.

## Bivariate

Survival rate: male 18.9% / female 74.0%; 1st 62.6% / 2nd 47.3% / 3rd 24.2%;
combined female/1st 96.7% down to male/3rd 13.5%. Sex dominates within every
class.

Correlation matrix (`survived`, `pclass`, `age`, `sibsp`, `parch`, `fare` —
`adult_male`/`alone` excluded as derived flags). Strongest pairs: `fare`–`pclass`
(r ≈ -0.55), `sibsp`–`parch` (r ≈ 0.41).

## Data story (4 charts)

1. **Sex × class:** women survive 96.7%/92.1%/50.0% across classes vs. men's
   36.9%/15.7%/13.5% — sex is the dominant factor, class secondary.
2. **Fare by outcome:** survivors' median fare (26.0) is 2.5x non-survivors'
   (10.5), shifted across the whole distribution, not just outliers.
3. **Age vs. fare:** survival falls steadily with age (58.0% → 19.0%),
   consistent with a "children first" priority.
4. **Family size:** non-monotonic — small families (1–3) survive at 57.9%,
   nearly double solo travelers (30.1%) and large families (16.1%).

## Standardization check

After z-scoring `age`/`fare`: mean ≈ 0, std ≈ 1.0006 (population-vs-sample-std
rounding). EDA-only — modeling does its own train-only scaling.

## Modeling

Stratified split (survival is 62/38 imbalanced). `ColumnTransformer` +
`Pipeline`, fit only on train. Features: `pclass`, `sex`, `age`, `sibsp`,
`parch`, `fare`, `embarked`.

| Model | Accuracy | Precision | Recall | F1 | AUC |
|---|---|---|---|---|---|
| Logistic Regression | 0.804 | 0.793 | 0.667 | 0.724 | 0.844 |
| Decision Tree | 0.816 | 0.790 | 0.710 | 0.748 | 0.790 |
| Random Forest | 0.816 | 0.800 | 0.696 | 0.744 | 0.829 |
| Random Forest (tuned) | 0.816 | 0.875 | 0.609 | 0.718 | 0.846 |

**Imbalance handling (Random Forest):** baseline 0.800/0.696/0.744 (P/R/F1);
`class_weight='balanced'` identical to baseline; SMOTE (train fold only)
0.758/0.725/0.741 — trades precision for recall. I'd lean SMOTE since missing
a survivor seems costlier than a false alarm.

**Tuning:** `GridSearchCV` (5-fold, F1) → `max_depth=5, max_features='sqrt',
n_estimators=100`, OOB score 0.826.

## Regression side-task (predicting fare)

MAE 20.90, RMSE 30.53, R² 0.398, Adjusted R² 0.362. RMSE ≫ MAE points to a
few large misses, consistent with fare's skew.

**Heteroscedasticity:** residual std by predicted-fare bin: 1.38 → 11.55 →
12.52 → 16.73 → 47.72 (~34x spread) — model is precise on cheap fares, much
less so on expensive ones.

## Recommendation

Classification and regression metrics are kept as separate tables (different
scales). I'd deploy the tuned Random Forest — best AUC (0.846) and precision
(0.875) — but its recall (0.609) trails the untuned forest (0.696) and
decision tree (0.710); if missing survivors matters more than false alarms,
I'd pick one of those instead. Logistic Regression is a solid, simpler
fallback given its near-identical AUC (0.844).

## Saved pipeline

Full pipeline (preprocessing + tuned Random Forest) saved via `joblib.dump`
to `best_titanic_pipeline.joblib`, reloaded and confirmed to predict
identically on raw, unprocessed input.
