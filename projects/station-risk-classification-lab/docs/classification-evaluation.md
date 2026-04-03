# Classification Evaluation Evidence

Evaluation context for the station risk classification lab.

## Classifier Comparison

The lab compares public-safe candidate classifiers for station risk scoring:

| Classifier | Approach | Strengths |
| --- | --- | --- |
| Scorecard | Weighted rule-based scoring | Fully interpretable, no training needed |
| Centroid | Distance to class centroids | Simple geometric intuition |
| Profile-rule | Feature-profile threshold rules | Domain-driven, explicit criteria |

## Evaluation Design

Each classifier is evaluated on a hold-out set using:

- **Accuracy**: fraction of correct risk classifications
- **Precision per class**: reliability of each predicted risk level
- **Recall per class**: completeness of each predicted risk level
- **Confusion matrix**: full classification error breakdown

## Risk Classes

| Class | Meaning | Action |
| --- | --- | --- |
| Low | Station operating normally | Routine monitoring |
| Moderate | Elevated concern | Scheduled review |
| High | Immediate attention needed | Priority triage |

## Explainability

Each classifier produces interpretable explanations for its risk assignment:

- **Scorecard**: shows the weighted factors and their contribution to the total score
- **Centroid**: shows the distance to each class centroid
- **Profile-rule**: shows which threshold rules were triggered

This transparency is critical for operational adoption — analysts need to understand why a station was flagged.

## Expected Results Pattern

On the built-in sample data:

- Scorecard and profile-rule classifiers tend to agree on clear high/low cases
- Centroid classifier may differ on boundary cases where feature profiles are ambiguous
- The evaluation report highlights disagreement cases for analyst review

## Limitations

- Sample dataset is small and synthetic
- Three classifiers are simple by design — more complex models (random forests, gradient boosting) are not included
- Feature vectors are compact snapshots, not full time-series representations
