"""
Convert GraphRAG Knowledge Graph to RAGAS Format for Synthetic Test Data Generation

This script extracts information from the Neo4j knowledge graph and converts it into
the format required by RAGAS for generating synthetic questions and ground truth answers.
"""

from common import get_driver
import json
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import pandas as pd

# ============================================
# DATA MODELS FOR RAGAS
# ============================================

@dataclass
class Document:
    """Represents a document chunk for RAGAS"""
    page_content: str
    metadata: Dict[str, Any]

@dataclass
class QAPair:
    """Question-Answer pair with context"""
    question: str
    answer: str
    contexts: List[str]
    metadata: Dict[str, Any]


# ============================================
# KNOWLEDGE GRAPH TO RAGAS CONVERTER
# ============================================

class KnowledgeGraphToRAGAS:
    """Converts Neo4j Knowledge Graph to RAGAS-compatible format"""
    
    def __init__(self, driver):
        self.driver = driver
    
    def extract_document_contexts(self) -> List[Document]:
        """
        Extract meaningful text contexts from the knowledge graph.
        These will be used as the corpus for RAGAS.
        """
        print("\n" + "="*70)
        print("EXTRACTING DOCUMENT CONTEXTS FROM KNOWLEDGE GRAPH")
        print("="*70)
        
        documents = []
        
        with self.driver.session() as session:
            # Extract requirement-based contexts
            print("\n1. Extracting Requirement contexts...")
            result = session.run("""
                MATCH (req:Requirement)
                OPTIONAL MATCH (req)-[r1:HAS_FUNCTIONALITY]-(func:Functionality)
                OPTIONAL MATCH (req)-[r2:IMPLEMENTS]-(impl)
                WHERE impl:Feature OR impl:Component OR impl:Product
                
                WITH req, 
                     collect(DISTINCT func.name) as functionalities,
                     collect(DISTINCT impl.name) as implementations
                
                RETURN req.name as requirement,
                       req.description as description,
                       functionalities,
                       implementations
                LIMIT 100
            """)
            
            for record in result:
                req_name = record['requirement']
                desc = record.get('description', '')
                funcs = [f for f in record['functionalities'] if f]
                impls = [i for i in record['implementations'] if i]
                
                # Build context text
                context = f"Requirement: {req_name}"
                if desc:
                    context += f"\nDescription: {desc}"
                if funcs:
                    context += f"\nFunctionalities: {', '.join(funcs)}"
                if impls:
                    context += f"\nImplementations: {', '.join(impls)}"
                
                documents.append(Document(
                    page_content=context,
                    metadata={
                        "type": "requirement",
                        "name": req_name,
                        "functionalities_count": len(funcs),
                        "implementations_count": len(impls)
                    }
                ))
            
            print(f"   !! Extracted {len(documents)} requirement contexts")
            
            # Extract feature-based contexts
            print("\n2. Extracting Feature contexts...")
            feature_count = len(documents)
            result = session.run("""
                MATCH (feat:Feature)
                OPTIONAL MATCH (feat)-[r1:USES]-(comp:Component)
                OPTIONAL MATCH (feat)-[r2:DEPENDS_ON]-(dep)
                
                WITH feat,
                     collect(DISTINCT comp.name) as components,
                     collect(DISTINCT dep.name) as dependencies
                
                RETURN feat.name as feature,
                       feat.description as description,
                       components,
                       dependencies
                LIMIT 50
            """)
            
            for record in result:
                feat_name = record['feature']
                desc = record.get('description', '')
                comps = [c for c in record['components'] if c]
                deps = [d for d in record['dependencies'] if d]
                
                context = f"Feature: {feat_name}"
                if desc:
                    context += f"\nDescription: {desc}"
                if comps:
                    context += f"\nComponents Used: {', '.join(comps)}"
                if deps:
                    context += f"\nDependencies: {', '.join(deps)}"
                
                documents.append(Document(
                    page_content=context,
                    metadata={
                        "type": "feature",
                        "name": feat_name,
                        "components_count": len(comps),
                        "dependencies_count": len(deps)
                    }
                ))
            
            print(f"   !! Extracted {len(documents) - feature_count} feature contexts")
            
            # Extract component architecture contexts
            print("\n3. Extracting Component architecture contexts...")
            comp_count = len(documents)
            result = session.run("""
                MATCH (comp:Component)
                OPTIONAL MATCH (comp)-[r1:DEPENDS_ON]->(dep:Component)
                OPTIONAL MATCH (comp)-[r2:PROVIDES]->(service)
                OPTIONAL MATCH (comp)-[r3:USES]->(tech)
                
                WITH comp,
                     collect(DISTINCT dep.name) as dependencies,
                     collect(DISTINCT service.name) as services,
                     collect(DISTINCT tech.name) as technologies
                
                RETURN comp.name as component,
                       comp.description as description,
                       dependencies,
                       services,
                       technologies
                LIMIT 50
            """)
            
            for record in result:
                comp_name = record['component']
                desc = record.get('description', '')
                deps = [d for d in record['dependencies'] if d]
                servs = [s for s in record['services'] if s]
                techs = [t for t in record['technologies'] if t]
                
                context = f"Component: {comp_name}"
                if desc:
                    context += f"\nDescription: {desc}"
                if deps:
                    context += f"\nDepends On: {', '.join(deps)}"
                if servs:
                    context += f"\nProvides: {', '.join(servs)}"
                if techs:
                    context += f"\nTechnologies: {', '.join(techs)}"
                
                documents.append(Document(
                    page_content=context,
                    metadata={
                        "type": "component",
                        "name": comp_name,
                        "dependencies_count": len(deps),
                        "services_count": len(servs)
                    }
                ))
            
            print(f"   !! Extracted {len(documents) - comp_count} component contexts")
            
            # Extract customer/user contexts
            print("\n4. Extracting Customer/User contexts...")
            user_count = len(documents)
            result = session.run("""
                MATCH (user)
                WHERE user:Customer OR user:User OR user:Administrator
                OPTIONAL MATCH (user)-[r:ACCESSES|MANAGES|USES]->(target)
                
                WITH user,
                     labels(user)[0] as user_type,
                     collect(DISTINCT target.name) as interactions
                
                RETURN user.name as user_name,
                       user_type,
                       user.description as description,
                       interactions
                LIMIT 30
            """)
            
            for record in result:
                user_name = record['user_name']
                user_type = record['user_type']
                desc = record.get('description', '')
                interactions = [i for i in record['interactions'] if i]
                
                context = f"{user_type}: {user_name}"
                if desc:
                    context += f"\nDescription: {desc}"
                if interactions:
                    context += f"\nInteracts With: {', '.join(interactions)}"
                
                documents.append(Document(
                    page_content=context,
                    metadata={
                        "type": "user",
                        "user_type": user_type,
                        "name": user_name,
                        "interactions_count": len(interactions)
                    }
                ))
            
            print(f"   !! Extracted {len(documents) - user_count} user contexts")
        
        print(f"\n!! Total contexts extracted: {len(documents)}")
        return documents
    
    def extract_knowledge_triples(self) -> List[Dict[str, str]]:
        """
        Extract knowledge triples (subject-relation-object) from the graph.
        These can be used to generate factual questions.
        """
        print("\n" + "="*70)
        print("EXTRACTING KNOWLEDGE TRIPLES")
        print("="*70)
        
        triples = []
        
        with self.driver.session() as session:
            # Extract all meaningful relationships
            result = session.run("""
                MATCH (n)-[r]->(m)
                WHERE type(r) <> 'FROM_CHUNK' 
                  AND type(r) <> 'NEXT_CHUNK'
                  AND type(r) <> 'FROM_DOCUMENT'
                  AND NOT 'Chunk' IN labels(n)
                  AND NOT 'Chunk' IN labels(m)
                
                RETURN n.name as subject,
                       labels(n)[0] as subject_type,
                       type(r) as relation,
                       m.name as object,
                       labels(m)[0] as object_type,
                       r.details as relation_details
                LIMIT 500
            """)
            
            for record in result:
                if record['subject'] and record['object']:
                    triple = {
                        "subject": record['subject'],
                        "subject_type": record['subject_type'],
                        "relation": record['relation'],
                        "object": record['object'],
                        "object_type": record['object_type'],
                        "details": record.get('relation_details', '')
                    }
                    triples.append(triple)
        
        print(f"!! Extracted {len(triples)} knowledge triples")
        return triples
    
    def create_ragas_dataset(self, documents: List[Document], 
                            triples: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Create a RAGAS-compatible dataset structure.
        """
        print("\n" + "="*70)
        print("CREATING RAGAS DATASET")
        print("="*70)
        
        # Convert documents to RAGAS format
        corpus = []
        for doc in documents:
            corpus.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })
        
        # Create knowledge base from triples
        knowledge_base = []
        for triple in triples:
            knowledge_base.append({
                "subject": triple['subject'],
                "subject_type": triple['subject_type'],
                "predicate": triple['relation'],
                "object": triple['object'],
                "object_type": triple['object_type']
            })
        
        dataset = {
            "corpus": corpus,
            "knowledge_graph": knowledge_base,
            "metadata": {
                "total_documents": len(corpus),
                "total_triples": len(knowledge_base),
                "document_types": list(set(doc.metadata.get('type') for doc in documents)),
            }
        }
        
        print(f"!! Dataset created with {len(corpus)} documents and {len(knowledge_base)} triples")
        return dataset
    
    def save_for_ragas(self, output_dir: str = "./ragas_data"):
        """
        Extract all data and save in formats suitable for RAGAS.
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        print("\n" + "="*70)
        print("CONVERTING KNOWLEDGE GRAPH TO RAGAS FORMAT")
        print("="*70)
        
        # Extract data
        documents = self.extract_document_contexts()
        triples = self.extract_knowledge_triples()
        dataset = self.create_ragas_dataset(documents, triples)
        
        # Save as JSON
        json_path = os.path.join(output_dir, "kg_dataset.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print(f"\n!! Saved dataset to: {json_path}")
        
        # Save corpus as separate file
        corpus_path = os.path.join(output_dir, "corpus.json")
        with open(corpus_path, 'w', encoding='utf-8') as f:
            json.dump(dataset['corpus'], f, indent=2, ensure_ascii=False)
        print(f"!! Saved corpus to: {corpus_path}")
        
        # Save knowledge triples
        triples_path = os.path.join(output_dir, "knowledge_triples.json")
        with open(triples_path, 'w', encoding='utf-8') as f:
            json.dump(dataset['knowledge_graph'], f, indent=2, ensure_ascii=False)
        print(f"!! Saved triples to: {triples_path}")
        
        # Save as CSV for easy inspection
        df_corpus = pd.DataFrame([
            {
                'content': doc['content'],
                'type': doc['metadata'].get('type'),
                'name': doc['metadata'].get('name')
            }
            for doc in dataset['corpus']
        ])
        csv_path = os.path.join(output_dir, "corpus.csv")
        df_corpus.to_csv(csv_path, index=False)
        print(f"!! Saved corpus CSV to: {csv_path}")
        
        # Save triples as CSV
        df_triples = pd.DataFrame(dataset['knowledge_graph'])
        triples_csv_path = os.path.join(output_dir, "knowledge_triples.csv")
        df_triples.to_csv(triples_csv_path, index=False)
        print(f"!! Saved triples CSV to: {triples_csv_path}")
        
        # Print summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"\nTotal Documents: {len(documents)}")
        print(f"Total Knowledge Triples: {len(triples)}")
        print(f"\nDocument Types:")
        for doc_type in dataset['metadata']['document_types']:
            count = sum(1 for doc in documents if doc.metadata.get('type') == doc_type)
            print(f"  • {doc_type}: {count}")
        
        return dataset


# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    print("="*70)
    print("GRAPHRAG TO RAGAS CONVERTER")
    print("="*70)
    
    # Connect to Neo4j
    driver = get_driver()
    
    # Create converter
    converter = KnowledgeGraphToRAGAS(driver)
    
    # Convert and save
    dataset = converter.save_for_ragas(output_dir="./ragas_data")
    
    driver.close()
    
    print("\n" + "="*70)
    print("!! CONVERSION COMPLETE!")
    print("="*70)
    print("\nNext steps:")
    print("1. Use the generated files in ./ragas_data/ with RAGAS")
    print("2. Generate synthetic test data using RAGAS testset generation")
    print("3. Use corpus.json as your document collection")
    print("4. Use knowledge_triples.json as structured knowledge base")