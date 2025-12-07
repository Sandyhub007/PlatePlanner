# 📊 Diagram Preview Guide

This document shows what the TikZ diagrams in your report will look like when compiled.

---

## Figure 1: System Architecture (4-Layer Design)

```
┌────────────────────────────────────────────────────────────┐
│           API Layer (FastAPI)                              │
├────────────────────────────────────────────────────────────┤
│  /suggest_recipes  /substitute  /shopping-lists  /meal-plans│
└─────────────────────┬──────────────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────────────┐
│           Service Layer (Business Logic)                   │
├────────────────────────────────────────────────────────────┤
│  Recipe Service  Neo4j Service  Shopping Service  Meal Plan│
└─────────────────────┬──────────────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────────────┐
│           Data Layer (Persistence)                         │
├────────────────────────────────────────────────────────────┤
│      Neo4j Graph    PostgreSQL Relational    Redis Cache   │
└─────────────────────┬──────────────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────────────┐
│           ML Layer (Models & Inference)                    │
├────────────────────────────────────────────────────────────┤
│  FAISS Index  SentenceTransformer  Embeddings  Normalizer  │
└────────────────────────────────────────────────────────────┘
```

**Visual Style:**
- Blue boxes for layers (with shadow effects)
- Green rounded rectangles for services
- Orange cylinders for databases
- Purple ellipses for ML models
- Solid arrows connecting layers
- Dashed lines showing specific service-to-data connections

---

## Figure 2: Data Flow Pipeline with Timing

```
Client Request
      │ (5ms)
      ▼
  FastAPI Validation
      │ (25ms)
      ▼
  Embedding Generation
      │ (12ms)
      ▼
  FAISS Search
      │ (3ms)
      ▼
  Metadata Lookup
      │ (8ms)
      ▼
  Overlap Computation
      │ (5ms)
      ▼
  Hybrid Reranking
      │ (4ms)
      ▼
  Response Serialization
      │
      ▼
  Client Response

┌────────────────────────────────────────┐
│  Total: 62ms (median) | 78ms (p95)     │
└────────────────────────────────────────┘
```

**Visual Style:**
- Blue rounded boxes for each step
- Red timing annotations above/below each step
- Thick blue arrows showing flow
- Green summary box at bottom
- Labels indicating which layer (API/Service/ML)

---

## Figure 3: Hybrid Scoring Algorithm

```
         User Query
         (ingredients)
              │
        ┌─────┴─────┐
        │           │
        ▼           ▼
    Semantic    Ingredient
    Similarity   Overlap
     S_sem       S_over
        │           │
        ▼           ▼
    Weight      Weight
    (1-w)         (w)
     0.4         0.6
        │           │
        ▼           ▼
       [×]         [×]
        │           │
        └─────┬─────┘
              │
              ▼
            [+]
              │
              ▼
      ┌───────────────┐
      │ Hybrid Score  │
      │  S_hybrid     │
      └───────────────┘
```

**Visual Style:**
- Blue box for input (query)
- Green boxes for similarity components
- Yellow boxes for weights
- Purple circles for operations (×, +)
- Green box for final score
- Gray annotations for context

---

## Color Scheme

The diagrams use a professional academic color palette:

| Element | Color | Usage |
|---------|-------|-------|
| **Layers** | Light Blue (`blue!10`) | Main architectural layers |
| **Services** | Light Green (`green!15`) | Business logic services |
| **Databases** | Light Orange (`orange!20`) | Data storage |
| **ML Models** | Light Purple (`purple!15`) | AI/ML components |
| **Timing** | Light Red (`red!10`) | Performance metrics |
| **Operations** | Various | Mathematical operations |
| **Arrows** | Dark Blue (`blue!70`) | Data flow |
| **Annotations** | Gray | Supporting text |

---

## How They'll Appear in PDF

✅ **Sharp and Clear**: Vector graphics scale perfectly  
✅ **Professional**: Drop shadows, rounded corners  
✅ **Colorful but Print-Friendly**: Light colors work in B&W too  
✅ **Consistent**: Uniform styling across all figures  
✅ **Annotated**: Labels and timing information included  

---

## Customization Tips

### Change Colors:
```latex
% In TikZ code, find the style definitions
layer/.style={..., fill=blue!10, ...}

% Change to:
layer/.style={..., fill=green!10, ...}  % Light green instead
```

### Adjust Sizes:
```latex
% Change text width
text width=8cm  →  text width=10cm  % Wider boxes

% Change minimum height
minimum height=1.2cm  →  minimum height=1.5cm  % Taller boxes
```

### Add More Elements:
```latex
% Add a new node
\node[service, below=of existing_node] (new_node) {New Service};

% Connect it
\draw[arrow] (existing_node) -- (new_node);
```

### Remove Drop Shadows:
```latex
% Find: drop shadow
% Replace with nothing or comment out
% drop shadow
```

---

## Compilation Notes

⏱️ **First Compilation**: May take 10-15 seconds (TikZ rendering)  
⚡ **Subsequent Compilations**: Faster (~5 seconds)  
💾 **Memory**: TikZ uses ~200MB RAM during compilation  
🎯 **Quality**: Output is publication-ready vector graphics  

---

## Alternative: Export as Standalone PDFs

If you want individual diagram files:

```latex
% Add to each figure environment
\tikzexternalize[figure name=architecture]
% This creates architecture.pdf

% Or compile standalone:
\documentclass{standalone}
\usepackage{tikz}
\begin{document}
% ... your TikZ code here ...
\end{document}
```

Then use in main document:
```latex
\includegraphics{architecture.pdf}
```

---

## Quick Test

Want to see if your LaTeX setup works? Try this minimal example:

```latex
\documentclass{article}
\usepackage{tikz}
\begin{document}
\begin{tikzpicture}
\node[draw, fill=blue!20] {Test};
\end{tikzpicture}
\end{document}
```

Save as `test.tex` and compile:
```bash
pdflatex test.tex
```

If this works, your full report will compile successfully! ✅

---

**Happy Compiling! 🎨**

