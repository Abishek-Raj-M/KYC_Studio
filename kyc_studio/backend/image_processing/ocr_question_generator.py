"""
OCR Question Generator
Uses LLM to generate questions from OCR extracted documents

This creates test questions based on the actual OCR data,
rather than using pre-generated KG test questions.
"""

import json
from typing import List, Dict
from common import get_llm


class OCRQuestionGenerator:
    """Generate questions from OCR documents using LLM"""
    
    def __init__(self):
        """Initialize with LLM"""
        self.llm = get_llm()
        print("✅ OCR Question Generator initialized")
    
    def _extract_person_name(self, ocr_doc: Dict) -> str:
        """Extract person name from OCR document"""
        doc_type = ocr_doc.get('document_type', '')
        
        # Try different name structures based on doc type
        if doc_type == 'driver_license':
            name_obj = ocr_doc.get('name', {})
            first = name_obj.get('first_name', '')
            last = name_obj.get('last_name', '')
            return f"{first} {last}".strip()
        
        elif doc_type in ['passport', 'passport_card']:
            given = ocr_doc.get('given_names', '')
            surname = ocr_doc.get('surname', '')
            return f"{given} {surname}".strip()
        
        elif doc_type == 'permanent_resident_card':
            given = ocr_doc.get('given_name', '')
            surname = ocr_doc.get('surname', '')
            return f"{given} {surname}".strip()
        
        elif doc_type == 'social_security_card':
            name_obj = ocr_doc.get('name', {})
            return name_obj.get('full_name', '')
        
        elif doc_type == 'birth_certificate':
            subject = ocr_doc.get('subject', {})
            return subject.get('full_name', '')
        
        elif doc_type == 'w2':
            employee = ocr_doc.get('employee', {})
            first = employee.get('first_name', '')
            last = employee.get('last_name', '')
            return f"{first} {last}".strip()
        
        elif doc_type == 'bank_statement':
            customer = ocr_doc.get('customer', {})
            return customer.get('name', '')
        
        return "Unknown"
    
    def _build_ocr_summary(self, ocr_doc: Dict) -> str:
        """Build a clean summary of OCR document for LLM"""
        doc_type = ocr_doc.get('document_type', 'unknown')
        person_name = self._extract_person_name(ocr_doc)
        
        # Extract key fields based on document type
        summary_lines = []
        summary_lines.append(f"Document Type: {doc_type}")
        summary_lines.append(f"Person: {person_name}")
        
        # Add available fields
        if ocr_doc.get('date_of_birth') or ocr_doc.get('dob'):
            dob = ocr_doc.get('date_of_birth') or ocr_doc.get('dob')
            summary_lines.append(f"Date of Birth: {dob}")
        
        if ocr_doc.get('license_number'):
            summary_lines.append(f"License Number: {ocr_doc['license_number']}")
        
        if ocr_doc.get('passport_number'):
            summary_lines.append(f"Passport Number: {ocr_doc['passport_number']}")
        
        if ocr_doc.get('passport_card_number'):
            summary_lines.append(f"Passport Card Number: {ocr_doc['passport_card_number']}")
        
        if ocr_doc.get('uscis_number'):
            summary_lines.append(f"USCIS Number: {ocr_doc['uscis_number']}")
        
        if ocr_doc.get('ssn'):
            summary_lines.append(f"SSN: {ocr_doc['ssn']}")
        
        if ocr_doc.get('nationality'):
            summary_lines.append(f"Nationality: {ocr_doc['nationality']}")
        
        if ocr_doc.get('country_of_birth') or ocr_doc.get('place_of_birth'):
            country = ocr_doc.get('country_of_birth') or ocr_doc.get('place_of_birth')
            summary_lines.append(f"Country of Birth: {country}")
        
        if ocr_doc.get('sex'):
            summary_lines.append(f"Sex: {ocr_doc['sex']}")
        
        if ocr_doc.get('issue_date') or ocr_doc.get('date_of_issue'):
            issue = ocr_doc.get('issue_date') or ocr_doc.get('date_of_issue')
            summary_lines.append(f"Issue Date: {issue}")
        
        if ocr_doc.get('expiration_date') or ocr_doc.get('date_of_expiration'):
            exp = ocr_doc.get('expiration_date') or ocr_doc.get('date_of_expiration')
            summary_lines.append(f"Expiration Date: {exp}")
        
        if ocr_doc.get('resident_since'):
            summary_lines.append(f"Resident Since: {ocr_doc['resident_since']}")
        
        # Address
        address = ocr_doc.get('address', {})
        if address and isinstance(address, dict):
            city = address.get('city')
            state = address.get('state')
            if city or state:
                summary_lines.append(f"Location: {city}, {state}")
        
        return "\n".join(summary_lines)
    
    def generate_questions_from_ocr(
        self,
        ocr_doc: Dict,
        num_questions: int = 5,
        include_reasoning: bool = False
    ) -> List[Dict]:
        """
        Generate questions from OCR document using LLM
        
        Args:
            ocr_doc: OCR extracted document (JSON)
            num_questions: Number of questions to generate (min 5)
            include_reasoning: Include reasoning questions (default: factual only)
        
        Returns:
            List of question dictionaries with metadata
        """
        # Ensure minimum questions
        num_questions = max(5, num_questions)
        
        doc_type = ocr_doc.get('document_type', 'unknown')
        person_name = self._extract_person_name(ocr_doc)
        
        # Skip error documents
        if doc_type == 'error':
            print(f"  ⚠️  Skipping error document")
            return []
        
        print(f"\n  📝 Generating {num_questions} questions for {doc_type} ({person_name})...")
        
        # Build OCR summary for LLM
        ocr_summary = self._build_ocr_summary(ocr_doc)
        
        # Create prompt based on question type preference
        if include_reasoning:
            question_types = """
Generate a MIX of question types:
1. Factual questions (60%): Direct questions about fields
   - "What is {name}'s license number?"
   - "What is {name}'s date of birth?"
   
2. Reasoning questions (30%): Questions requiring inference
   - "Is {name} a naturalized citizen?" (requires comparing birth country vs nationality)
   - "Is {name}'s passport valid?" (requires checking expiration date vs today)
   
3. Verification questions (10%): Questions about document validity
   - "Can we verify {name}'s identity with these documents?"
   - "What documents does {name} have on file?"
"""
        else:
            question_types = """
Generate FACTUAL questions only:
- Direct questions about specific fields in the document
- "What is {name}'s license number?"
- "What is {name}'s date of birth?"
- "When does {name}'s document expire?"
- "What is {name}'s nationality?"
"""
        
        prompt = f"""You are generating test questions from OCR extracted document data.

OCR Document Summary:
{ocr_summary}

Task: Generate {num_questions} questions based on this OCR data.

{question_types}

Requirements:
1. Use the actual person name: "{person_name}"
2. Only ask about fields that ARE present in the OCR data
3. Make questions clear and specific
4. Each question should be answerable from the OCR data shown above
5. For each question, identify which field it's asking about

Return ONLY valid JSON in this exact format:
{{
  "questions": [
    {{
      "question": "What is {person_name}'s license number?",
      "field": "license_number",
      "question_type": "factual"
    }},
    {{
      "question": "What is {person_name}'s date of birth?",
      "field": "date_of_birth",
      "question_type": "factual"
    }}
  ]
}}

Generate exactly {num_questions} questions. Return ONLY the JSON, no other text."""

        try:
            # Call LLM
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            
            # Clean JSON
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]
            
            # Parse JSON
            result = json.loads(content.strip())
            questions_data = result.get('questions', [])
            
            # Add metadata
            enriched_questions = []
            for q in questions_data:
                enriched_questions.append({
                    "question": q['question'],
                    "field": q.get('field', 'unknown'),
                    "question_type": q.get('question_type', 'factual'),
                    "person_name": person_name,
                    "document_type": doc_type,
                    "source": "ocr_generated"
                })
            
            print(f"  ✅ Generated {len(enriched_questions)} questions")
            
            return enriched_questions
            
        except Exception as e:
            print(f"  ❌ Failed to generate questions: {e}")
            return []
    
    def generate_questions_from_all_docs(
        self,
        ocr_documents: List[Dict],
        num_questions: int = 5,
        include_reasoning: bool = False
    ) -> List[Dict]:
        """
        Generate questions from all OCR documents
        
        Returns:
            List of all generated questions with metadata
        """
        print("\n" + "="*70)
        print("GENERATING QUESTIONS FROM OCR DOCUMENTS")
        print("="*70)
        print(f"Settings: {num_questions} questions per doc, reasoning={include_reasoning}")
        
        all_questions = []
        
        for idx, ocr_doc in enumerate(ocr_documents, 1):
            print(f"\n[{idx}/{len(ocr_documents)}] Processing document...")
            
            questions = self.generate_questions_from_ocr(
                ocr_doc=ocr_doc,
                num_questions=num_questions,
                include_reasoning=include_reasoning
            )
            
            all_questions.extend(questions)
        
        print("\n" + "="*70)
        print(f"✅ Generated {len(all_questions)} total questions from {len(ocr_documents)} documents")
        print("="*70)
        
        return all_questions


def main():
    """Test the question generator"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python ocr_question_generator.py <ocr_json_path>")
        print("Example: python ocr_question_generator.py ocr_test_results/all_extracted_documents.json")
        return
    
    ocr_json_path = sys.argv[1]
    
    # Load OCR data
    with open(ocr_json_path, 'r', encoding='utf-8') as f:
        ocr_documents = json.load(f)
    
    print(f"Loaded {len(ocr_documents)} OCR documents")
    
    # Generate questions
    generator = OCRQuestionGenerator()
    questions = generator.generate_questions_from_all_docs(
        ocr_documents=ocr_documents,
        num_questions=5,
        include_reasoning=False
    )
    
    # Save questions
    output_path = "generated_questions.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Saved questions to: {output_path}")
    
    # Show samples
    print("\n📋 Sample Questions:")
    for q in questions[:5]:
        print(f"  • {q['question']}")


if __name__ == "__main__":
    main()