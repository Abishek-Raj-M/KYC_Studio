# GraphRAG + RAGAS: Automated RAG Testing

> Synthetic test data generation and evaluation for RAG systems using Knowledge Graphs

## 🎯 Overview

Automate RAG testing by:
1. Building a **Knowledge Graph** from your documents (GraphRAG)
2. Generating **synthetic test data** with ground truth (RAGAS)
3. Evaluating your RAG system with **quantitative metrics**



## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install neo4j neo4j-graphrag ragas langchain-openai datasets pandas python-dotenv PyPDF2
```

### 2. Configure Environment
Create `.env` file:
```bash
NEO4J_URI=neo4j+ssc://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
DIAL_API_KEY=your-api-key  # Or OPENAI_API_KEY
```

### 3. Run the Pipeline
```bash
# Step 1: Build Knowledge Graph (5-10 min)
python kg_builder_dynamic.py

# Step 2: Convert to RAGAS format (1-2 min)
python kg_to_ragas_converter.py

# Step 3: Generate test data (3-5 min)
python kg_based_testgen.py

# Step 4: Evaluate RAG system (5-15 min)
python ragas_evaluation.py
```

---

## 📁 What You Get

### Generated Files:
```
ragas_data/
├── corpus.json              # Document contexts (106+)
├── knowledge_triples.json   # KG relationships (246+)
├── qa_pairs_all.json       # Test questions (30+)
├── evaluation_results.csv  # Detailed scores per question
└── evaluation_summary.json # Overall metrics
```

### Test Data Format:
```json
{
  "question": "What does Component X depend on?",
  "answer": "",  // Filled by YOUR RAG during evaluation
  "contexts": [],  // Filled by YOUR RAG during evaluation
  "ground_truth": "Component X depends on Database Y"  // From KG
}
```

---

## 📊 Evaluation Metrics

| Metric | What It Measures | Target |
|--------|------------------|--------|
| **Faithfulness** | No hallucinations | >0.8 |
| **Answer Relevancy** | Answers the question | >0.8 |
| **Context Precision** | Retrieval quality | >0.7 |
| **Context Recall** | Retrieval coverage | >0.7 |
| **Answer Correctness** | Matches ground truth | >0.8 |

---

## 🔧 Key Scripts

### `kg_builder_dynamic.py`
Builds knowledge graph from documents
- **Input:** PDF/Word/Text files
- **Output:** Neo4j Knowledge Graph
- **Features:** Auto schema detection, entity/relationship extraction

### `kg_to_ragas_converter.py`
Extracts data from KG for RAGAS
- **Input:** Neo4j Knowledge Graph
- **Output:** `corpus.json`, `knowledge_triples.json`

### `kg_based_testgen.py`
Generates synthetic test questions
- **Input:** Corpus + Triples
- **Output:** `qa_pairs_all.json` (30+ Q&A pairs)
- **Strategies:** Single-hop, Multi-hop, Aggregation, LLM-enhanced

### `ragas_evaluation.py`
Evaluates your RAG system
- **Input:** Test dataset + Your RAG pipeline
- **Output:** Evaluation report with 5 metrics
- **Note:** Customize `retrieve_with_graphrag()` with your RAG logic

---

## 🏗️ Architecture

```
Documents → GraphRAG → Neo4j KG
              ↓
          RAGAS Converter
              ↓
    corpus.json + triples.json
              ↓
        Test Generator
              ↓
   Q&A Dataset (ground truth)
              ↓
    Your RAG Pipeline (retrieve + generate)
              ↓
        RAGAS Evaluation
              ↓
    Metrics Report (5 scores)
```

**Key Innovation:** Ground truth from Knowledge Graph (factual) vs LLM generation (prone to hallucination)

---

## ⚙️ Configuration

Edit `common.py` to customize:
- Neo4j connection
- LLM provider (OpenAI, Azure, custom)
- Embedding model
- RAG retrieval logic

---

## 🔍 Example Results

```json
{
  "faithfulness": 0.85,        // ✅ Good
  "answer_relevancy": 0.82,    // ✅ Good
  "context_precision": 0.65,   // ⚠️ Needs tuning
  "context_recall": 0.58,      // ⚠️ Needs tuning
  "answer_correctness": 0.78   // ✅ Good
}
```

**Interpretation:** Answer generation is strong, retrieval needs improvement

---

## 📝 Project Structure

```
├── kg_builder_dynamic.py           # Build KG
├── kg_to_ragas_converter.py        # Convert KG to RAGAS
├── kg_based_testgen.py             # Generate test data
├── ragas_evaluation.py             # Evaluate RAG
├── common.py                        # Shared config
├── .env                             # Environment variables
├── requirements.txt                 # Dependencies
└── ragas_data/                      # Generated outputs
```

---

## 🐛 Troubleshooting

**Neo4j connection fails?**
- Check `NEO4J_URI`, username, password in `.env`
- Verify Neo4j instance is running

**No entities extracted?**
- Verify document path is correct
- Check PDF is readable (not scanned image)

**Low RAGAS scores?**
- Customize `retrieve_with_graphrag()` in `ragas_evaluation.py`
- Add your actual RAG retrieval logic

**RAGAS evaluation error?**
- Install: `pip install langchain-openai`
- Ensure LLM configuration is correct



**Built for automated, scalable RAG testing** 🚀