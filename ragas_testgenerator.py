"""
Knowledge Graph-Based Test Data Generator

This PROPERLY uses the GraphRAG knowledge graph to generate:
1. Questions based on graph structure and relationships
2. Ground truth derived from graph traversals
3. Tests that validate graph-aware retrieval
"""

import json
import os
from typing import List, Dict, Tuple
import pandas as pd
from common import get_driver, get_llm
import random


class KGBasedTestGenerator:
    """Generate test data from Knowledge Graph structure"""
    
    def __init__(self, neo4j_driver, data_dir: str = "./ragas_data"):
        self.driver = neo4j_driver
        self.data_dir = data_dir
        self.llm = get_llm()
        
        # Load corpus for context retrieval
        corpus_path = os.path.join(data_dir, "corpus.json")
        with open(corpus_path, 'r', encoding='utf-8') as f:
            self.corpus = json.load(f)
    
    def get_kg_statistics(self):
        """Analyze KG structure to understand what questions we can ask"""
        print("\n" + "="*70)
        print("ANALYZING KNOWLEDGE GRAPH STRUCTURE")
        print("="*70)
        
        with self.driver.session() as session:
            # Get node types
            result = session.run("""
                MATCH (n)
                RETURN DISTINCT labels(n)[0] as label, count(*) as count
                ORDER BY count DESC
            """)
            
            print("\nNode Types:")
            node_types = {}
            for record in result:
                label = record['label']
                count = record['count']
                node_types[label] = count
                print(f"  • {label}: {count}")
            
            # Get relationship types
            result = session.run("""
                MATCH ()-[r]->()
                RETURN DISTINCT type(r) as rel_type, count(*) as count
                ORDER BY count DESC
            """)
            
            print("\nRelationship Types:")
            rel_types = {}
            for record in result:
                rel_type = record['rel_type']
                count = record['count']
                rel_types[rel_type] = count
                print(f"  • {rel_type}: {count}")
            
            return node_types, rel_types
    
    def generate_single_hop_questions(self, num_questions: int = 15) -> List[Dict]:
        """
        Generate questions about direct relationships in the KG
        Example: "What does Component X depend on?"
        """
        print("\n" + "="*70)
        print("GENERATING SINGLE-HOP KG QUESTIONS")
        print("="*70)
        
        qa_pairs = []
        
        with self.driver.session() as session:
            # Query for interesting single-hop patterns
            result = session.run("""
                MATCH (source)-[r]->(target)
                WHERE NOT type(r) IN ['FROM_CHUNK', 'NEXT_CHUNK', 'FROM_DOCUMENT']
                  AND source.name IS NOT NULL
                  AND target.name IS NOT NULL
                WITH source, r, target, labels(source)[0] as source_type, 
                     labels(target)[0] as target_type, type(r) as rel_type
                RETURN source.name as source_name,
                       source.description as source_desc,
                       source_type,
                       rel_type,
                       target.name as target_name,
                       target.description as target_desc,
                       target_type
                ORDER BY rand()
                LIMIT $limit
            """, limit=num_questions * 3)  # Get extras for filtering
            
            for record in result:
                source_name = record['source_name']
                source_type = record['source_type']
                rel_type = record['rel_type']
                target_name = record['target_name']
                target_type = record['target_type']
                
                # Generate natural language question
                question = self._relationship_to_question(
                    source_name, source_type, rel_type, target_name, target_type
                )
                
                # Generate ground truth answer
                ground_truth = self._relationship_to_answer(
                    source_name, source_type, rel_type, target_name, target_type
                )
                
                # Find relevant contexts from corpus
                contexts = self._find_contexts_for_entities([source_name, target_name])
                
                if question and ground_truth and contexts:
                    qa_pairs.append({
                        "question": question,
                        "answer": "",  # EMPTY - will be filled by RAG pipeline during evaluation
                        "contexts": [],  # EMPTY - will be filled by RAG retrieval
                        "ground_truth": ground_truth,
                        "expected_contexts": contexts,  # For reference only
                        "metadata": {
                            "source": "kg_single_hop",
                            "source_entity": source_name,
                            "target_entity": target_name,
                            "relationship": rel_type,
                            "hop_count": 1
                        }
                    })
                    
                    print(f"  !! [{len(qa_pairs)}/{num_questions}] {question[:70]}...")
                
                if len(qa_pairs) >= num_questions:
                    break
        
        print(f"\n!! Generated {len(qa_pairs)} single-hop questions")
        return qa_pairs
    
    def generate_multi_hop_questions(self, num_questions: int = 10) -> List[Dict]:
        """
        Generate questions requiring 2-3 hop traversals in the KG
        Example: "What technologies are used by components that depend on Database X?"
        """
        print("\n" + "="*70)
        print("GENERATING MULTI-HOP KG QUESTIONS")
        print("="*70)
        
        qa_pairs = []
        
        with self.driver.session() as session:
            # 2-hop patterns
            result = session.run("""
                MATCH (start)-[r1]->(middle)-[r2]->(end)
                WHERE NOT type(r1) IN ['FROM_CHUNK', 'NEXT_CHUNK', 'FROM_DOCUMENT']
                  AND NOT type(r2) IN ['FROM_CHUNK', 'NEXT_CHUNK', 'FROM_DOCUMENT']
                  AND start.name IS NOT NULL
                  AND middle.name IS NOT NULL
                  AND end.name IS NOT NULL
                WITH start, r1, middle, r2, end,
                     labels(start)[0] as start_type,
                     labels(middle)[0] as middle_type,
                     labels(end)[0] as end_type,
                     type(r1) as rel1_type,
                     type(r2) as rel2_type
                RETURN start.name as start_name, start_type,
                       rel1_type,
                       middle.name as middle_name, middle_type,
                       rel2_type,
                       end.name as end_name, end_type
                ORDER BY rand()
                LIMIT $limit
            """, limit=num_questions * 2)
            
            for record in result:
                start_name = record['start_name']
                middle_name = record['middle_name']
                end_name = record['end_name']
                rel1 = record['rel1_type']
                rel2 = record['rel2_type']
                
                # Generate multi-hop question
                question = f"Through its relationship with {middle_name}, what does {start_name} connect to?"
                
                # Ground truth from graph
                ground_truth = f"{start_name} {rel1.replace('_', ' ').lower()} {middle_name}, which {rel2.replace('_', ' ').lower()} {end_name}."
                
                # Find contexts
                contexts = self._find_contexts_for_entities([start_name, middle_name, end_name])
                
                if contexts:
                    qa_pairs.append({
                        "question": question,
                        "answer": "",  # EMPTY - will be filled by RAG pipeline
                        "contexts": [],  # EMPTY - will be filled by RAG retrieval
                        "ground_truth": ground_truth,
                        "expected_contexts": contexts,
                        "metadata": {
                            "source": "kg_multi_hop",
                            "entities": [start_name, middle_name, end_name],
                            "hop_count": 2
                        }
                    })
                    
                    print(f"  !! [{len(qa_pairs)}/{num_questions}] Multi-hop question")
                
                if len(qa_pairs) >= num_questions:
                    break
        
        print(f"\n!! Generated {len(qa_pairs)} multi-hop questions")
        return qa_pairs
    
    def generate_aggregation_questions(self, num_questions: int = 10) -> List[Dict]:
        """
        Generate questions requiring aggregation over graph patterns
        Example: "What are all the requirements that Feature X implements?"
        """
        print("\n" + "="*70)
        print("GENERATING AGGREGATION KG QUESTIONS")
        print("="*70)
        
        qa_pairs = []
        
        with self.driver.session() as session:
            # Pattern: Find nodes with multiple outgoing relationships
            result = session.run("""
                MATCH (source)-[r]->(targets)
                WHERE NOT type(r) IN ['FROM_CHUNK', 'NEXT_CHUNK', 'FROM_DOCUMENT']
                  AND source.name IS NOT NULL
                WITH source, type(r) as rel_type, 
                     collect(DISTINCT targets.name) as target_names,
                     count(DISTINCT targets) as target_count,
                     labels(source)[0] as source_type
                WHERE target_count >= 2
                RETURN source.name as source_name,
                       source_type,
                       rel_type,
                       target_names,
                       target_count
                ORDER BY target_count DESC
                LIMIT $limit
            """, limit=num_questions * 2)
            
            for record in result:
                source_name = record['source_name']
                source_type = record['source_type']
                rel_type = record['rel_type']
                targets = [t for t in record['target_names'] if t]
                
                if len(targets) < 2:
                    continue
                
                # Generate aggregation question
                question = f"What are all the entities that {source_name} {rel_type.replace('_', ' ').lower()}?"
                
                # Ground truth
                ground_truth = f"{source_name} {rel_type.replace('_', ' ').lower()} the following: {', '.join(targets)}."
                
                # Find contexts
                contexts = self._find_contexts_for_entities([source_name] + targets[:3])
                
                if contexts:
                    qa_pairs.append({
                        "question": question,
                        "answer": "",  # EMPTY - will be filled by RAG pipeline
                        "contexts": [],  # EMPTY - will be filled by RAG retrieval
                        "ground_truth": ground_truth,
                        "expected_contexts": contexts,
                        "metadata": {
                            "source": "kg_aggregation",
                            "source_entity": source_name,
                            "aggregation_count": len(targets),
                            "relationship": rel_type
                        }
                    })
                    
                    print(f"  !! [{len(qa_pairs)}/{num_questions}] Aggregation question")
                
                if len(qa_pairs) >= num_questions:
                    break
        
        print(f"\n!! Generated {len(qa_pairs)} aggregation questions")
        return qa_pairs
    
    def generate_llm_enhanced_kg_questions(self, num_questions: int = 10) -> List[Dict]:
        """
        Use LLM to create natural questions from KG patterns
        This combines KG structure with LLM fluency
        """
        print("\n" + "="*70)
        print("GENERATING LLM-ENHANCED KG QUESTIONS")
        print("="*70)
        
        qa_pairs = []
        
        with self.driver.session() as session:
            # Get interesting subgraphs
            result = session.run("""
                MATCH (n)-[r1]->(m)-[r2]->(o)
                WHERE NOT type(r1) IN ['FROM_CHUNK', 'NEXT_CHUNK']
                  AND NOT type(r2) IN ['FROM_CHUNK', 'NEXT_CHUNK']
                  AND n.name IS NOT NULL
                  AND m.name IS NOT NULL
                  AND o.name IS NOT NULL
                RETURN n.name as n1, labels(n)[0] as type1, type(r1) as rel1,
                       m.name as n2, labels(m)[0] as type2, type(r2) as rel2,
                       o.name as n3, labels(o)[0] as type3
                ORDER BY rand()
                LIMIT $limit
            """, limit=num_questions * 2)
            
            for record in result:
                n1, type1, rel1 = record['n1'], record['type1'], record['rel1']
                n2, type2, rel2 = record['n2'], record['type2'], record['rel2']
                n3, type3 = record['n3'], record['type3']
                
                # Use LLM to generate natural question from graph pattern
                prompt = f"""Given this knowledge graph pattern:
- {n1} (a {type1}) {rel1.replace('_', ' ').lower()} {n2} (a {type2})
- {n2} {rel2.replace('_', ' ').lower()} {n3} (a {type3})

Generate ONE natural, specific question that tests understanding of these relationships.

Return in JSON format:
{{
    "question": "natural question here",
    "answer": "answer based on the graph pattern"
}}

Return ONLY valid JSON."""

                try:
                    response = self.llm.invoke(prompt)
                    content = response.content.strip()
                    
                    if '```json' in content:
                        content = content.split('```json')[1].split('```')[0]
                    elif '```' in content:
                        content = content.split('```')[1].split('```')[0]
                    
                    result_json = json.loads(content.strip())
                    
                    question = result_json['question']
                    answer = result_json['answer']
                    
                    # Find contexts
                    contexts = self._find_contexts_for_entities([n1, n2, n3])
                    
                    if contexts:
                        qa_pairs.append({
                            "question": question,
                            "answer": "",  # EMPTY - will be filled by RAG pipeline
                            "contexts": [],  # EMPTY - will be filled by RAG retrieval
                            "ground_truth": answer,
                            "expected_contexts": contexts,
                            "metadata": {
                                "source": "kg_llm_enhanced",
                                "entities": [n1, n2, n3],
                                "graph_pattern": f"{rel1}->{rel2}"
                            }
                        })
                        
                        print(f"  !! [{len(qa_pairs)}/{num_questions}] {question[:60]}...")
                    
                except Exception as e:
                    print(f"  ⚠️  Failed: {e}")
                    continue
                
                if len(qa_pairs) >= num_questions:
                    break
        
        print(f"\n!! Generated {len(qa_pairs)} LLM-enhanced questions")
        return qa_pairs
    
    def _relationship_to_question(self, source: str, source_type: str, 
                                  rel: str, target: str, target_type: str) -> str:
        """Convert a KG relationship to a natural question"""
        
        templates = {
            "DEPENDS_ON": f"What does {source} depend on?",
            "USES": f"What does {source} use?",
            "IMPLEMENTS": f"What does {source} implement?",
            "PROVIDES": f"What does {source} provide?",
            "CONTAINS": f"What does {source} contain?",
            "MANAGES": f"What does {source} manage?",
            "SUPPORTS": f"What does {source} support?",
            "RELATED_TO": f"What is {source} related to?",
            "PART_OF": f"What is {source} part of?",
            "HAS_REQUIREMENT": f"What requirements does {source} have?",
        }
        
        return templates.get(rel, f"What is the relationship between {source} and {target}?")
    
    def _relationship_to_answer(self, source: str, source_type: str,
                               rel: str, target: str, target_type: str) -> str:
        """Convert a KG relationship to a ground truth answer"""
        return f"{source} {rel.replace('_', ' ').lower()} {target}."
    
    def _find_contexts_for_entities(self, entity_names: List[str], max_contexts: int = 3) -> List[str]:
        """Find document contexts that mention the given entities"""
        contexts = []
        
        for doc in self.corpus:
            content = doc.get('content', '')
            # Check if any entity is mentioned
            if any(entity in content for entity in entity_names if entity):
                contexts.append(content)
                if len(contexts) >= max_contexts:
                    break
        
        return contexts
    
    def save_qa_pairs(self, qa_pairs: List[Dict], output_path: str):
        """Save generated Q&A pairs"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(qa_pairs, f, indent=2, ensure_ascii=False)
        print(f"\n!! Saved to: {output_path}")
        
        # CSV version
        df = pd.DataFrame(qa_pairs)
        csv_path = output_path.replace('.json', '.csv')
        df_flat = df.copy()
        df_flat['contexts'] = df_flat['contexts'].apply(lambda x: ' | '.join(x[:2]) if x else '')
        df_flat = df_flat.drop('metadata', axis=1, errors='ignore')
        df_flat.to_csv(csv_path, index=False)
        print(f"!! Saved CSV to: {csv_path}")


def main():
    print("="*70)
    print("KNOWLEDGE GRAPH-BASED TEST GENERATOR")
    print("="*70)
    
    if not os.path.exists("./ragas_data/corpus.json"):
        print("\n⚠️  Data not found!")
        return
    
    # Connect to Neo4j
    driver = get_driver()
    generator = KGBasedTestGenerator(driver, data_dir="./ragas_data")
    
    # Analyze KG
    generator.get_kg_statistics()
    
    print("\n" + "="*70)
    print("GENERATION OPTIONS")
    print("="*70)
    print("1. Balanced Mix (15 single-hop + 10 multi-hop + 5 aggregation) - Recommended")
    print("2. Single-hop focus (25 questions) - Test basic graph retrieval")
    print("3. Multi-hop focus (20 questions) - Test complex reasoning")
    print("4. LLM-enhanced (20 natural questions from KG) - Test fluency with graph data")
    
    choice = input("\nSelect [1-4, default=1]: ").strip() or "1"
    
    all_qa = []
    
    if choice == "1":
        all_qa.extend(generator.generate_single_hop_questions(15))
        all_qa.extend(generator.generate_multi_hop_questions(10))
        all_qa.extend(generator.generate_aggregation_questions(5))
    elif choice == "2":
        all_qa.extend(generator.generate_single_hop_questions(25))
    elif choice == "3":
        all_qa.extend(generator.generate_multi_hop_questions(20))
    elif choice == "4":
        all_qa.extend(generator.generate_llm_enhanced_kg_questions(20))
    
    if all_qa:
        generator.save_qa_pairs(all_qa, "./ragas_data/qa_pairs_kg_based.json")
        generator.save_qa_pairs(all_qa, "./ragas_data/qa_pairs_all.json")  # Overwrite main file
        
        print("\n" + "="*70)
        print("!!KG-BASED TEST GENERATION COMPLETE!")
        print("="*70)
    
    driver.close()


if __name__ == "__main__":
    main()