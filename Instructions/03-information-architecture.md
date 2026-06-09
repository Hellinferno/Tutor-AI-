# 03 - Information Architecture

## Top-level surfaces
- **Notebook**: the main workspace; source list, source guides, ask surface, citations.
- **Solve**: verified problem solving with stored step reveal.
- **Artifacts**: summary notes, study guides, planners, timetables, revision cards.
- **Notion Export**: send generated artifacts to private Notion pages.
- **Practice**: quizzes and question papers, later phase.
- **Revise**: spaced repetition, later phase.
- **Progress**: mastery analytics, later phase.
- **Settings**: subject domain, privacy, Notion connection, API keys.

## Navigation tree
```text
Root
|-- Notebook
|   |-- Sources
|   |-- Source guide
|   |-- Ask with citations
|   |-- Citation drawer
|-- Solve
|   |-- Text solve
|   |-- Image/OCR solve
|   |-- Step reveal
|-- Artifacts
|   |-- Summary notes
|   |-- Study guide
|   |-- Planner
|   |-- Timetable
|   |-- Revision cards
|   |-- Export to Notion
|-- Practice
|-- Revise
|-- Progress
|-- Settings
```

## Core domain entities
- **User**: subject domain and preferences.
- **Notebook**: collection of sources and generated artifacts.
- **Source**: uploaded material, extracted text, status, kind.
- **SourceChunk**: chunk text with stable source offsets and vector id.
- **SourceGuide**: summary, key concepts, suggested questions.
- **Citation**: source id, title, chunk index, offsets, snippet, retrieval score.
- **Question**: normalized problem text and hash.
- **Solution**: answer, reveal-ready steps, verification method, citations.
- **Artifact**: summary notes, study guide, planner, timetable, revision cards.
- **NotionExport**: target page, result URL, connection status.

## Content flow
```text
source upload
-> extract text
-> chunk with offsets
-> source guide
-> dense + sparse indexing
-> hybrid retrieve
-> rerank
-> cited answer or insufficient support
```

## IA principles
- Notebook is the primary unit, not a loose material list.
- Sources are inspectable and explainable through source guides.
- Every grounded answer must expose citation evidence.
- Technical answers can be both cited and verified.
- Study artifacts are first-class outputs and can be exported.
