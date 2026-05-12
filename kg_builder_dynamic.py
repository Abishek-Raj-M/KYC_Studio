# Dynamic Knowledge Graph Builder for Any Document Type - CORRECTED VERSION
import neo4j
import asyncio
import json
from common import get_driver, get_llm, get_embedder

from neo4j_graphrag.llm import LLMInterface, LLMResponse
from neo4j_graphrag.embeddings.openai import OpenAIEmbeddings
from neo4j_graphrag.experimental.components.text_splitters.fixed_size_splitter import FixedSizeSplitter
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline

# ==========================
# Configuration
# ===========================
PDF_PATH = ["C:\\Users\\SatyaprasadDakinedi\\Desktop\\SRS.pdf"]
REBUILD_KG = True
VECTOR_INDEX_NAME = "chunk_embeddings"
EMBEDDING_DIM = 1536

# ================================
# Neo4j Driver
# ==================================
print("Connecting to Neo4j...")
driver = get_driver()
print("Connected to Neo4j successfully.")

print("\nInitializing LLM & Embedder...")
llm = get_llm()
embedder = get_embedder()

print("LLM:", type(llm))
print("Embedder:", type(embedder))


# ==========================
# JSON CLEANING WRAPPER (ONLY FIX NEEDED)
# ==========================
class CleanJSONLLM(LLMInterface):
    """Wrapper that removes markdown code blocks from Azure OpenAI responses"""
    
    def __init__(self, base_llm: LLMInterface):
        self.base_llm = base_llm
        if hasattr(base_llm, 'model_name'):
            self.model_name = base_llm.model_name
    
    def invoke(self, input: str) -> LLMResponse:
        response = self.base_llm.invoke(input)
        content = self._clean_json(response.content)
        return LLMResponse(content=content)
    
    async def ainvoke(self, input: str) -> LLMResponse:
        if hasattr(self.base_llm, 'ainvoke'):
            response = await self.base_llm.ainvoke(input)
        else:
            response = self.base_llm.invoke(input)
        content = self._clean_json(response.content)
        return LLMResponse(content=content)
    
    def _clean_json(self, content: str) -> str:
        """Remove markdown code blocks and extract JSON"""
        content = content.strip()
        
        if '```json' in content:
            start = content.find('```json') + 7
            end = content.find('```', start)
            if end > start:
                content = content[start:end].strip()
        elif '```' in content:
            start = content.find('```') + 3
            end = content.find('```', start)
            if end > start:
                content = content[start:end].strip()
        
        # Extract JSON by finding first { and last }
        first_brace = content.find('{')
        last_brace = content.rfind('}')
        if first_brace != -1 and last_brace != -1:
            content = content[first_brace:last_brace+1]
        
        return content


# Wrap the LLM (ONLY FIX)
llm = CleanJSONLLM(llm)


# ==========================
# DYNAMIC SCHEMA EXTRACTION (YOUR ORIGINAL CODE)
# ==========================

def get_dynamic_schema_prompt(sample_text: str) -> dict:
    """
    Uses LLM to analyze document and suggest appropriate entities and relationships
    """
    schema_extraction_prompt = f"""
Analyze the following sample text from a document and identify:
1. The main types of entities (nodes) that should be extracted
2. The types of relationships between these entities

Sample text:
{sample_text[:3000]}

You MUST return ONLY a valid JSON object with no additional text, markdown formatting, or explanations.

Return ONLY this JSON structure:
{{
    "node_labels": ["Entity1", "Entity2"],
    "relationship_types": ["REL_TYPE_1", "REL_TYPE_2"],
    "document_type": "SRS"
}}

Guidelines:
- Node labels should be PascalCase (e.g., Customer, Product)
- Relationship types should be UPPER_SNAKE_CASE (e.g., PURCHASES, CONTAINS)
- Suggest 10-20 node types and 10-15 relationship types
- Be specific to the document domain
- Return ONLY valid JSON, no markdown code blocks or extra text
"""
    
    try:
        response = llm.invoke(schema_extraction_prompt)
        
        # Clean response - remove markdown code blocks if present
        content = response.content.strip()
        
        # Remove markdown code blocks
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        
        content = content.strip()
        
        schema_info = json.loads(content)
        return schema_info
    except Exception as e:
        print(f"Error extracting schema: {e}")
        if 'response' in locals():
            print(f"LLM Response was: {response.content[:500]}")
        # Fallback to generic schema
        return {
            "node_labels": ["Entity", "Concept", "Person", "Organization", "Location", "Event", "Document"],
            "relationship_types": ["RELATED_TO", "PART_OF", "CONNECTED_TO", "MENTIONS", "CONTAINS"],
            "document_type": "Generic"
        }


def extract_sample_text(file_path: str) -> str:
    """Extract first few pages/chunks from document for schema analysis"""
    try:
        if file_path.lower().endswith('.pdf'):
            import PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                sample = ""
                for i in range(min(3, len(pdf_reader.pages))):
                    sample += pdf_reader.pages[i].extract_text()
                return sample
        else:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read(5000)
    except Exception as e:
        print(f"Error reading sample: {e}")
        return ""


def get_dynamic_prompt_template(node_labels: list, rel_types: list, document_type: str) -> str:
    """Generate prompt template based on detected document type"""
    
    domain_instructions = {
        "SRS": "You are analyzing a Software Requirements Specification document.",
        "Legal": "You are analyzing a legal document (contract, agreement, policy).",
        "Medical": "You are analyzing a medical/healthcare document.",
        "Financial": "You are analyzing a financial document (report, statement, invoice).",
        "Scientific": "You are analyzing a scientific research document.",
        "Generic": "You are analyzing a document to extract structured information."
    }
    
    instruction = domain_instructions.get(document_type, domain_instructions["Generic"])
    
    # Build prompt without f-string to avoid formatting issues
    prompt_template = instruction + '''

Extract the entities (nodes) and specify their type from the following Input text.
Also extract the relationships between these nodes. The relationship direction goes from the start node to the end node.

Return result as JSON using the following format:
{{"nodes": [ {{"id": "0", "label": "the type of entity", "properties": {{"name": "name of entity" }} }}],
  "relationships": [{{"type": "TYPE_OF_RELATIONSHIP", "start_node_id": "0", "end_node_id": "1", "properties": {{"details": "Description of the relationship"}} }}] }}

Use only the following nodes and relationships:
{schema}

Assign a unique ID (string) to each node, and reuse it to define relationships.
Do respect the source and target node types for relationship and the relationship direction.

Do not return any additional information other than the JSON in it.

Examples:
{examples}

Input text:

{text}
'''
    
    return prompt_template


# ==========================
# MAIN PROCESSING FUNCTION (YOUR ORIGINAL LOGIC)
# ==========================

async def process_documents_dynamically(file_paths: list, use_dynamic_schema: bool = True):
    """
    Process documents with dynamic schema extraction
    """
    
    node_labels = []
    rel_types = []
    prompt_template = ""
    
    if use_dynamic_schema:
        print("\n" + "="*50)
        print("DYNAMIC SCHEMA EXTRACTION MODE")
        print("="*50)
        
        # Step 1: Extract sample from first document
        print("\nStep 1: Extracting sample text from first document...")
        sample_text = extract_sample_text(file_paths[0])
        
        if not sample_text:
            print("Warning: Could not extract sample. Falling back to predefined schema.")
            use_dynamic_schema = False
        else:
            # Step 2: Get schema suggestions from LLM
            print("\nStep 2: Analyzing document to extract schema...")
            schema_info = get_dynamic_schema_prompt(sample_text)
            
            node_labels = schema_info.get("node_labels", [])
            rel_types = schema_info.get("relationship_types", [])
            document_type = schema_info.get("document_type", "Generic")
            
            if document_type == "Generic" and len(node_labels) <= 7:
                print("\nDynamic extraction returned generic schema. Falling back to predefined schema.")
                use_dynamic_schema = False
            else:
                print(f"\nDetected Document Type: {document_type}")
                print(f"\nExtracted Node Labels ({len(node_labels)}):")
                print(", ".join(node_labels))
                print(f"\nExtracted Relationship Types ({len(rel_types)}):")
                print(", ".join(rel_types))
                
                # Step 3: Generate dynamic prompt template
                print("\nStep 3: Generating dynamic prompt template...")
                try:
                    prompt_template = get_dynamic_prompt_template(node_labels, rel_types, document_type)
                except Exception as e:
                    print(f"Error generating prompt template: {e}")
                    print("Falling back to predefined schema.")
                    use_dynamic_schema = False
    
    if not use_dynamic_schema:
        print("\n" + "="*50)
        print("USING PREDEFINED SCHEMA (FALLBACK)")
        print("="*50)
        
        # Fallback generic schema
        node_labels = ["Entity", "Document", "Section", "Concept", "Person", "Organization", 
                       "Location", "Event", "Product", "Service", "Technology"]
        rel_types = ["RELATED_TO", "PART_OF", "CONTAINS", "MENTIONS", "USES", 
                     "CONNECTED_TO", "DEPENDS_ON", "PROVIDES"]
        
        prompt_template = '''Extract entities and relationships from the text as JSON.

Return result as JSON using the following format:
{{"nodes": [ {{"id": "0", "label": "Entity", "properties": {{"name": "name" }} }}],
  "relationships": [{{"type": "RELATED_TO", "start_node_id": "0", "end_node_id": "1"}} ] }}

Schema:
{{schema}}

Examples:
{{examples}}

Input text:
{{text}}
'''
    
    # Step 4: Initialize KG Pipeline
    print("\nStep 4: Initializing KG Pipeline...")
    kg_builder = SimpleKGPipeline(
        llm=llm,
        driver=driver,
        text_splitter=FixedSizeSplitter(chunk_size=1000, chunk_overlap=150),
        embedder=embedder,
        entities=node_labels,
        relations=rel_types,
        prompt_template=prompt_template,
        from_pdf=True
    )
    print("KG Pipeline initialized successfully.")
    
    # Step 5: Process documents
    print("\nStep 5: Processing documents...")
    for idx, path in enumerate(file_paths, 1):
        print(f"\n{'#'*60}")
        print(f"Processing Document {idx}/{len(file_paths)}: {path}")
        print(f"{'#'*60}")
        
        try:
            result = await kg_builder.run_async(file_path=path)
            print(f"\n!! Processing completed!")
            print(f"Result: {result}")
        except Exception as e:
            print(f"\n✗ Error processing {path}")
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("ALL DOCUMENTS PROCESSED!")
    print("="*60)
    
    return kg_builder, node_labels, rel_types


# ==========================
# EXECUTION
# ==========================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("DYNAMIC GRAPHRAG KNOWLEDGE GRAPH BUILDER")
    print("="*60)
    
    # Use our ORIGINAL TOGGLE
    USE_DYNAMIC_SCHEMA = True  # Set to False to use fallback schema
    
    print(f"\nMode: {'DYNAMIC SCHEMA EXTRACTION' if USE_DYNAMIC_SCHEMA else 'FALLBACK SCHEMA'}")
    print(f"Documents to process: {len(PDF_PATH)}")
    
    # Run processing
    kg_builder, node_labels, rel_types = asyncio.run(
        process_documents_dynamically(PDF_PATH, use_dynamic_schema=USE_DYNAMIC_SCHEMA)
    )
    
    print("\n" + "="*60)
    print("KNOWLEDGE GRAPH READY")
    print("="*60)
    print(f"\nNode types in KG: {len(node_labels)}")
    print(f"Relationship types in KG: {len(rel_types)}")