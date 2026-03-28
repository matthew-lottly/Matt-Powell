# STRATA Pipeline Flowchart

## Main Pipeline (for publication Figure 1)

```mermaid
flowchart TB
    subgraph INPUT["<b>Input: Heterogeneous Infrastructure Graph</b>"]
        direction LR
        P["🔴 Power Nodes<br/><i>200 substations</i><br/>tree topology"]
        W["🔵 Water Nodes<br/><i>150 treatment plants</i><br/>grid/mesh topology"]
        T["🟢 Telecom Nodes<br/><i>100 hub stations</i><br/>star-hub topology"]
        CE["⟷ Cross-Utility<br/>Coupling Edges"]
    end

    subgraph SPLIT["<b>Data Partitioning</b>"]
        direction LR
        TR["Train (60%)"]
        CAL["Calibration (20%)"]
        TEST["Test (20%)"]
    end

    subgraph GNN["<b>Heterogeneous GNN</b>"]
        direction TB
        IP["Per-Type Input<br/>Projection"]
        MP1["HeteroMessagePassing<br/>Layer 1<br/><i>per-edge-type W<sub>r</sub></i>"]
        MP2["HeteroMessagePassing<br/>Layer 2<br/><i>+ residual connection</i>"]
        MP3["HeteroMessagePassing<br/>Layer 3<br/><i>+ residual connection</i>"]
        OH["Per-Type Output<br/>Heads → ŷ<sub>i</sub>"]
        IP --> MP1 --> MP2 --> MP3 --> OH
    end

    subgraph TRAIN_PHASE["<b>Training Phase</b>"]
        direction TB
        MSE["MSE Loss on<br/>Train Nodes"]
        ES["Early Stopping<br/><i>patience = 20</i>"]
        FR["Freeze Training<br/>Residuals r<sub>j</sub> = |y<sub>j</sub> − ŷ<sub>j</sub>|"]
        MSE --> ES --> FR
    end

    subgraph CALIB["<b>Conformal Calibration</b><br/><i>(choose one)</i>"]
        direction TB
        subgraph CHMP["CHMP (Core Innovation)"]
            direction TB
            AGG["Aggregate Neighbor<br/>Residuals: r̄<sub>N(i)</sub>"]
            FLOOR["Apply Floor:<br/>r̄ ← max(r̄, floor_σ)"]
            SIGMA["Compute σ<sub>i</sub> = 1 + λ · r̄"]
            NORM["Normalize Scores:<br/>s<sub>i</sub> = |y<sub>i</sub> − ŷ<sub>i</sub>| / σ<sub>i</sub>"]
            QHAT["Per-Type Quantile:<br/>q̂<sub>t</sub> from cal scores"]
            AGG --> FLOOR --> SIGMA --> NORM --> QHAT
        end
        
        ADV["<b>Advanced Variants</b><br/>MetaCalibrator (learned σ)<br/>AttentionCalibrator (weighted)<br/>LearnableLambda (per-type λ*)<br/>CQR + propagation<br/>Ensemble (epistemic var)"]
    end

    subgraph PREDICT["<b>Prediction Intervals</b>"]
        direction TB
        INT["C<sub>i</sub> = [ŷ<sub>i</sub> − q̂<sub>τ(i)</sub> · σ<sub>i</sub>,<br/>  ŷ<sub>i</sub> + q̂<sub>τ(i)</sub> · σ<sub>i</sub>]"]
    end

    subgraph EVAL["<b>Evaluation & Diagnostics</b>"]
        direction LR
        COV["Marginal &<br/>Per-Type<br/>Coverage"]
        WIDTH["Mean<br/>Interval<br/>Width"]
        ECE["Expected<br/>Calibration<br/>Error"]
        SPATIAL["Spatial<br/>Diagnostics<br/><i>Moran's I</i><br/><i>Gi* Hotspots</i><br/><i>Kriging</i>"]
        STAT["Statistical<br/>Tests<br/><i>Wilcoxon</i><br/><i>Friedman</i><br/><i>Bootstrap CI</i>"]
    end

    INPUT --> SPLIT
    SPLIT --> GNN
    GNN --> TRAIN_PHASE
    TRAIN_PHASE --> CALIB
    CALIB --> PREDICT
    PREDICT --> EVAL

    style INPUT fill:#f9f0ff,stroke:#7c3aed,stroke-width:2px
    style GNN fill:#eff6ff,stroke:#2563eb,stroke-width:2px
    style TRAIN_PHASE fill:#fef3c7,stroke:#d97706,stroke-width:2px
    style CHMP fill:#ecfdf5,stroke:#059669,stroke-width:3px
    style CALIB fill:#f0fdf4,stroke:#16a34a,stroke-width:2px
    style PREDICT fill:#fef2f2,stroke:#dc2626,stroke-width:2px
    style EVAL fill:#f8fafc,stroke:#475569,stroke-width:2px
```

## Calibrator Comparison (for publication Figure 2)

```mermaid
flowchart LR
    subgraph INPUTS["Frozen Inputs"]
        PRED["Point Predictions ŷ<sub>i</sub>"]
        RESID["Training Residuals r<sub>j</sub>"]
        FEAT["Node Features x<sub>i</sub>"]
        HIDDEN["GNN Hidden Repr. h<sub>i</sub>"]
    end

    subgraph METHODS["Normalization Methods"]
        direction TB
        M1["<b>Mondrian CP</b><br/>σ<sub>i</sub> = 1<br/><i>(uniform)</i>"]
        M2["<b>CHMP</b><br/>σ<sub>i</sub> = 1 + λ · mean(r<sub>N(i)</sub>)<br/><i>(topology-adaptive)</i>"]
        M3["<b>MetaCalibrator</b><br/>σ<sub>i</sub> = MLP(x<sub>i</sub>, ŷ<sub>i</sub>, stats)<br/><i>(learned)</i>"]
        M4["<b>AttentionCalibrator</b><br/>σ<sub>i</sub> = Σ α<sub>ij</sub> · r<sub>j</sub><br/><i>(attention-weighted)</i>"]
        M5["<b>CQR</b><br/>q<sub>lo</sub>, q<sub>hi</sub> from QuantileHead<br/><i>(asymmetric)</i>"]
        M6["<b>Ensemble</b><br/>σ<sub>i</sub> = 1 + λ · √Var<sub>m</sub>[ŷ<sup>(m)</sup>]<br/><i>(epistemic)</i>"]
    end

    subgraph OUTPUT["Prediction Intervals"]
        SYM["Symmetric:<br/>ŷ ± q̂ · σ"]
        ASYM["Asymmetric:<br/>[q<sub>lo</sub> − q̂·σ, q<sub>hi</sub> + q̂·σ]"]
    end

    PRED --> M1 & M2 & M3 & M4 & M6
    RESID --> M2 & M3 & M4
    FEAT --> M3 & M4
    HIDDEN --> M5
    
    M1 & M2 & M3 & M4 & M6 --> SYM
    M5 --> ASYM

    style M2 fill:#ecfdf5,stroke:#059669,stroke-width:3px
    style M5 fill:#fef3c7,stroke:#d97706,stroke-width:2px
```

## CHMP Detail (for publication Figure 3)

```mermaid
flowchart TB
    subgraph GRAPH["Infrastructure Graph Neighborhood"]
        direction TB
        N1["Train Node j₁<br/>r₁ = 0.15"]
        N2["Train Node j₂<br/>r₂ = 0.08"]
        N3["Train Node j₃<br/>r₃ = 0.22"]
        CENTER["Cal/Test Node i<br/>ŷ<sub>i</sub> = 0.65"]
        N4["Train Node j₄<br/>r₄ = 0.03"]
        
        N1 -->|power-water| CENTER
        N2 -->|water-water| CENTER
        N3 -->|power-power| CENTER
        N4 -->|telecom-power| CENTER
    end

    STEP1["<b>Step 1:</b> Aggregate<br/>r̄ = mean(0.15, 0.08, 0.22, 0.03) = 0.12"]
    STEP2["<b>Step 2:</b> Apply Floor<br/>r̄ = max(0.12, 0.10) = 0.12"]
    STEP3["<b>Step 3:</b> Normalize<br/>σ<sub>i</sub> = 1 + 0.3 × 0.12 = 1.036"]
    STEP4["<b>Step 4:</b> Score<br/>s<sub>i</sub> = |y<sub>i</sub> − 0.65| / 1.036"]
    RESULT["<b>Result:</b> Node i gets<br/>slightly wider interval<br/>than average<br/>(neighbors had moderate error)"]

    GRAPH --> STEP1 --> STEP2 --> STEP3 --> STEP4 --> RESULT

    style GRAPH fill:#f9f0ff,stroke:#7c3aed,stroke-width:2px
    style RESULT fill:#ecfdf5,stroke:#059669,stroke-width:2px
```

## Data Flow Architecture (for supplementary)

```mermaid
flowchart TB
    subgraph DATA["Data Sources"]
        SYN["Synthetic Generator<br/>generate_synthetic_infrastructure()"]
        REAL["ACTIVSg200<br/>load_activsg200()<br/><i>200-bus Illinois grid</i>"]
    end

    GRAPH["HeteroInfraGraph<br/>• node_features: Dict[str, Tensor]<br/>• edge_index: Dict[str, Tensor]<br/>• node_positions: Dict[str, ndarray]<br/>• node_labels: Dict[str, ndarray]<br/>• node_masks: Dict[str, Dict]"]

    TENSORS["PyTorch Tensors<br/>_graph_to_tensors()"]
    
    MODEL["HeteroGNN<br/>3 layers, 64 hidden<br/>6 edge types"]
    
    PREDS["Predictions<br/>Dict[type → ndarray]"]

    CALIB_CHOICE{{"Calibrator<br/>Selection"}}

    C1["HeteroConformal"]
    C2["PropagationAware"]
    C3["MetaCalibrator"]
    C4["AttentionCalibrator"]
    C5["LearnableLambda"]
    C6["CQRCalibrator"]
    C7["EnsembleCalibrator"]

    RESULT["ConformalResult<br/>• lower, upper<br/>• point_pred<br/>• alpha, quantiles"]

    METRICS["Metrics Suite<br/>coverage, width, ECE"]
    DIAG["Diagnostics<br/>σ-hitrate, bootstrap CI,<br/>runs test, Moran's I"]
    GEO["Geo Integration<br/>kriging surface,<br/>Gi* hotspots"]

    DATA --> GRAPH --> TENSORS --> MODEL --> PREDS --> CALIB_CHOICE
    CALIB_CHOICE --> C1 & C2 & C3 & C4 & C5 & C6 & C7
    C1 & C2 & C3 & C4 & C5 & C6 & C7 --> RESULT
    RESULT --> METRICS & DIAG & GEO
```
