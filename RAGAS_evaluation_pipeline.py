"""
Evaluate GraphRAG RAG Pipeline using RAGAS with Synthetic Test Data

This script:
1. Loads the synthetic Q&A pairs
2. Runs them through your GraphRAG RAG pipeline
3. Evaluates with RAGAS metrics
4. Generates evaluation report
"""

import json
import os
import pandas as pd
from typing import List, Dict
from common import get_driver, get_llm, get_embedder

# RAGAS evaluation imports
try:
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall,
        answer_similarity,
        answer_correctness
    )
    RAGAS_AVAILABLE = True
    print("!! RAGAS evaluation metrics imported successfully")
except ImportError as e:
    RAGAS_AVAILABLE = False
    print(f"!! RAGAS not available: {e}")

# LangChain LLM for RAGAS compatibility
try:
    from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("!! LangChain not available for RAGAS")


class GraphRAGEvaluator:
    """Evaluate GraphRAG RAG pipeline using RAGAS"""
    
    def __init__(self, neo4j_driver, llm, embedder):
        self.driver = neo4j_driver
        self.llm = llm  # This is neo4j_graphrag LLM for generation
        self.embedder = embedder
        
        # Create LangChain-compatible LLM for RAGAS
        self.ragas_llm = None
        self.ragas_embedder = None
        
        if LANGCHAIN_AVAILABLE:
            try:
                import os
                
                # Use your EPAM AI Proxy configuration
                api_key = os.getenv("DIAL_API_KEY")
                azure_endpoint = "https://ai-proxy.lab.epam.com"
                
                self.ragas_llm = AzureChatOpenAI(
                    azure_endpoint=azure_endpoint,
                    api_key=api_key,
                    api_version="2024-02-01",
                    deployment_name="gpt-4o",  # Same as your get_llm
                    temperature=0
                )
                
                self.ragas_embedder = AzureOpenAIEmbeddings(
                    azure_endpoint=azure_endpoint,
                    api_key=api_key,
                    api_version="2024-02-01",
                    deployment="text-embedding-ada-002"  # Same as your get_embedder
                )
                
                print("!! Created LangChain-compatible LLM for RAGAS using EPAM AI Proxy")
            except Exception as e:
                print(f"!! Could not create LangChain LLM: {e}")
                print("Evaluation will skip RAGAS metrics")
                self.ragas_llm = None
                self.ragas_embedder = None
        else:
            print("!! LangChain not available. Install with: pip install langchain-openai")
            print("Evaluation will skip RAGAS metrics")
    
    def retrieve_with_graphrag(self, question: str, top_k: int = 3) -> List[str]:
        """
        Retrieve relevant contexts from GraphRAG using vector + Cypher queries.
        
        This is your existing GraphRAG retrieval logic.
        Customize this based on your actual retrieval implementation.
        """
        contexts = []
        
        with self.driver.session() as session:
            # Method 1: Vector similarity search on chunks/documents
            # Assuming you have embeddings stored in Neo4j
            try:
                # Generate query embedding
                query_embedding = self.embedder.embed_query(question)
                
                # Vector search query (adjust based on your schema)
                vector_result = session.run("""
                    MATCH (chunk:Chunk)
                    WHERE chunk.embedding IS NOT NULL
                    WITH chunk, 
                         gds.similarity.cosine(chunk.embedding, $query_embedding) AS similarity
                    ORDER BY similarity DESC
                    LIMIT $top_k
                    RETURN chunk.text as text, similarity
                """, query_embedding=query_embedding, top_k=top_k)
                
                for record in vector_result:
                    if record['text']:
                        contexts.append(record['text'])
                
            except Exception as e:
                print(f"  !! Vector search failed: {e}")
                # Fallback to keyword-based search
                pass
            
            # Method 2: Graph traversal for related entities
            # Extract key entities from question and traverse graph
            try:
                # Simple keyword extraction (you can improve this)
                keywords = [word for word in question.split() 
                           if len(word) > 4 and word[0].isupper()]
                
                if keywords:
                    # Find entities matching keywords
                    graph_result = session.run("""
                        MATCH (n)
                        WHERE any(keyword IN $keywords WHERE n.name CONTAINS keyword)
                        OPTIONAL MATCH (n)-[r]-(connected)
                        WITH n, connected, r
                        LIMIT 5
                        RETURN n.name as entity_name, 
                               n.description as entity_desc,
                               type(r) as relation,
                               connected.name as connected_entity
                    """, keywords=keywords)
                    
                    graph_context = []
                    for record in graph_result:
                        entity = record['entity_name']
                        desc = record.get('entity_desc', '')
                        relation = record.get('relation', '')
                        connected = record.get('connected_entity', '')
                        
                        if entity:
                            text = f"Entity: {entity}"
                            if desc:
                                text += f" - {desc}"
                            if relation and connected:
                                text += f". {relation} {connected}"
                            graph_context.append(text)
                    
                    contexts.extend(graph_context[:2])  # Add top 2 graph contexts
            
            except Exception as e:
                print(f"  !! Graph traversal failed: {e}")
                pass
            
            # Fallback: Simple text search if no contexts found
            if not contexts:
                fallback_result = session.run("""
                    MATCH (n)
                    WHERE n.name IS NOT NULL OR n.description IS NOT NULL
                    WITH n, 
                         size([word IN split(toLower($question), ' ') 
                               WHERE toLower(n.name) CONTAINS word 
                                  OR toLower(coalesce(n.description, '')) CONTAINS word]) as matches
                    WHERE matches > 0
                    RETURN n.name as name, n.description as description
                    ORDER BY matches DESC
                    LIMIT $top_k
                """, question=question.lower(), top_k=top_k)
                
                for record in fallback_result:
                    name = record.get('name', '')
                    desc = record.get('description', '')
                    if name or desc:
                        contexts.append(f"{name}: {desc}" if desc else name)
        
        # Ensure we have at least some context
        if not contexts:
            contexts = ["No relevant context found in knowledge graph."]
        
        return contexts[:top_k]
    
    def generate_answer(self, question: str, contexts: List[str]) -> str:
        """
        Generate answer using LLM based on retrieved contexts.
        """
        # Build context string
        context_str = "\n\n".join([f"Context {i+1}: {ctx}" for i, ctx in enumerate(contexts)])
        
        # Create prompt
        prompt = f"""Based on the following contexts from a knowledge graph, answer the question.

Contexts:
{context_str}

Question: {question}

Provide a clear, concise answer based only on the given contexts. If the contexts don't contain enough information, say so.

Answer:"""
        
        try:
            response = self.llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            return f"!! Error generating answer: {e}"
    
    def run_rag_pipeline(self, question: str, top_k: int = 3) -> Dict:
        """
        Run complete RAG pipeline: Retrieve + Generate
        """
        # Retrieve contexts
        contexts = self.retrieve_with_graphrag(question, top_k=top_k)
        
        # Generate answer
        answer = self.generate_answer(question, contexts)
        
        return {
            "question": question,
            "answer": answer,
            "contexts": contexts
        }
    
    def evaluate_with_ragas(self, test_data: List[Dict]) -> pd.DataFrame:
        """
        Evaluate RAG pipeline using RAGAS metrics
        
        Args:
            test_data: List of dicts with keys: question, answer, contexts, ground_truth
        """
        if not RAGAS_AVAILABLE:
            raise ImportError("RAGAS not available. Install with: pip install ragas")
        
        if not self.ragas_llm or not self.ragas_embedder:
            print("\n!! LangChain LLM not available. Cannot run RAGAS evaluation.")
            print("Install with: pip install langchain-openai")
            return None
        
        print("\n" + "="*70)
        print("RUNNING RAGAS EVALUATION")
        print("="*70)
        
        # Prepare dataset for RAGAS - need to import the Dataset class
        try:
            from datasets import Dataset
            
            eval_dataset = {
                "question": [item["question"] for item in test_data],
                "answer": [item["answer"] for item in test_data],
                "contexts": [item["contexts"] for item in test_data],
                "ground_truth": [item["ground_truth"] for item in test_data]
            }
            
            # Convert to HuggingFace Dataset (required by RAGAS)
            dataset = Dataset.from_dict(eval_dataset)
            
        except ImportError:
            print("!! 'datasets' library not found. Installing...")
            import subprocess
            subprocess.check_call(["pip", "install", "datasets"])
            from datasets import Dataset
            
            eval_dataset = {
                "question": [item["question"] for item in test_data],
                "answer": [item["answer"] for item in test_data],
                "contexts": [item["contexts"] for item in test_data],
                "ground_truth": [item["ground_truth"] for item in test_data]
            }
            dataset = Dataset.from_dict(eval_dataset)
        
        # Define metrics
        metrics = [
            faithfulness,          # Is answer faithful to contexts?
            answer_relevancy,      # Is answer relevant to question?
            context_precision,     # Are retrieved contexts relevant?
            context_recall,        # Are all relevant contexts retrieved?
            answer_correctness     # How correct is the answer?
        ]
        
        print(f"\nEvaluating {len(dataset)} samples...")
        print(f"Metrics: {', '.join([m.name for m in metrics])}")
        print(f"Using LLM: {type(self.ragas_llm).__name__}")
        
        try:
            # Run evaluation - use LangChain-compatible LLM
            result = evaluate(
                dataset=dataset,
                metrics=metrics,
                llm=self.ragas_llm,
                embeddings=self.ragas_embedder
            )
            
            return result.to_pandas()
            
        except Exception as e:
            print(f"\n!! RAGAS evaluation failed: {e}")
            import traceback
            traceback.print_exc()
            return None


def load_test_data(data_path: str = "./ragas_data/qa_pairs_all.json") -> List[Dict]:
    """Load synthetic test data"""
    print(f"\nLoading test data from: {data_path}")
    
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"!! Loaded {len(data)} test samples")
    return data


def run_evaluation(sample_size: int = None):
    """
    Main evaluation workflow
    
    Args:
        sample_size: Number of samples to evaluate (None = all)
    """
    print("="*70)
    print("GRAPHRAG RAG PIPELINE EVALUATION WITH RAGAS")
    print("="*70)
    
    # Initialize
    print("\nInitializing...")
    driver = get_driver()
    llm = get_llm()
    embedder = get_embedder()
    
    evaluator = GraphRAGEvaluator(driver, llm, embedder)
    
    # Load test data
    test_data = load_test_data()
    
    if sample_size:
        test_data = test_data[:sample_size]
        print(f"\nUsing {sample_size} samples for evaluation")
    
    # Run RAG pipeline for each question
    print("\n" + "="*70)
    print("RUNNING RAG PIPELINE")
    print("="*70)
    
    rag_results = []
    
    for i, item in enumerate(test_data, 1):
        question = item['question']
        ground_truth = item.get('ground_truth', '')
        
        # NOTE: item['answer'] and item['contexts'] should be EMPTY from test generation
        # We will fill them here with RAG pipeline output
        
        print(f"\n[{i}/{len(test_data)}] Processing: {question[:80]}...")
        
        try:
            # Run RAG pipeline to GET answer and contexts
            result = evaluator.run_rag_pipeline(question, top_k=3)
            
            rag_results.append({
                "question": question,
                "answer": result["answer"],  # Generated by YOUR RAG pipeline
                "contexts": result["contexts"],  # Retrieved by YOUR RAG pipeline
                "ground_truth": ground_truth  # From KG (the "correct" answer)
            })
            
            print(f"  !! Retrieved {len(result['contexts'])} contexts")
            print(f"  !! Generated answer: {result['answer'][:100]}...")
            print(f"  !! Ground truth: {ground_truth[:100]}...")
            
        except Exception as e:
            print(f"  !! Error: {e}")
            # Add placeholder
            rag_results.append({
                "question": question,
                "answer": "Error generating answer",
                "contexts": ["Error retrieving contexts"],
                "ground_truth": ground_truth
            })
    
    # Save RAG results
    results_path = "./ragas_data/rag_results.json"
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(rag_results, f, indent=2, ensure_ascii=False)
    print(f"\n!! Saved RAG results to: {results_path}")
    
    # Evaluate with RAGAS
    if RAGAS_AVAILABLE:
        print("\n" + "="*70)
        print("EVALUATING WITH RAGAS METRICS")
        print("="*70)
        
        eval_results = evaluator.evaluate_with_ragas(rag_results)
        
        if eval_results is not None:
            # Save evaluation results
            eval_path = "./ragas_data/evaluation_results.csv"
            eval_results.to_csv(eval_path, index=False)
            print(f"\n!! Saved evaluation results to: {eval_path}")
            
            # Display summary
            print("\n" + "="*70)
            print("EVALUATION SUMMARY")
            print("="*70)
            
            print("\nMetric Scores:")
            for col in eval_results.columns:
                if col not in ['question', 'answer', 'contexts', 'ground_truth']:
                    try:
                        mean_score = eval_results[col].mean()
                        print(f"  • {col}: {mean_score:.3f}")
                    except:
                        pass
            
            # Save summary
            summary = {
                "total_samples": len(eval_results),
                "metrics": {}
            }
            
            for col in eval_results.columns:
                if col not in ['question', 'answer', 'contexts', 'ground_truth']:
                    try:
                        summary["metrics"][col] = {
                            "mean": float(eval_results[col].mean()),
                            "std": float(eval_results[col].std()),
                            "min": float(eval_results[col].min()),
                            "max": float(eval_results[col].max())
                        }
                    except:
                        pass
            
            summary_path = "./ragas_data/evaluation_summary.json"
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
            print(f"\n!! Saved summary to: {summary_path}")
    
    else:
        print("\n!! RAGAS not available for evaluation")
        print("Generating basic statistics instead...")
        
        # Basic statistics without RAGAS
        df = pd.DataFrame(rag_results)
        df['answer_length'] = df['answer'].str.len()
        df['num_contexts'] = df['contexts'].str.len()
        
        print("\nBasic Statistics:")
        print(f"  • Average answer length: {df['answer_length'].mean():.0f} chars")
        print(f"  • Average contexts retrieved: {df['num_contexts'].mean():.1f}")
    
    driver.close()
    
    print("\n" + "="*70)
    print("!! EVALUATION COMPLETE!")
    print("="*70)


# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    import sys
    
    print("\n" + "="*70)
    print("GRAPHRAG EVALUATION PIPELINE")
    print("="*70)
    
    # Check if test data exists
    if not os.path.exists("./ragas_data/qa_pairs_all.json"):
        print("\n!! Test data not found!")
        print("Please run ragas_testgenerator.py first to generate test data.")
        sys.exit(1)
    
    # Ask for sample size
    print("\nHow many samples to evaluate?")
    print("(Smaller samples = faster evaluation, good for testing)")
    print("(Full dataset = comprehensive evaluation)")
    
    sample_input = input("\nEnter number (or press Enter for all): ").strip()
    
    if sample_input:
        try:
            sample_size = int(sample_input)
        except:
            print("Invalid input. Using all samples.")
            sample_size = None
    else:
        sample_size = None
    
    # Run evaluation
    run_evaluation(sample_size=sample_size)