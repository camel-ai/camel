import json
from typing import Dict, Optional

from camel.types.enums import OutputExtractionErrorType
from camel.prompts.output_format.base import (
    Extractor,
    ExtractionResult,
    OutputFormat
)

class DirectExtractor(Extractor[str]):
    """Direct extractor that returns the input text as is."""
    
    def extract(self, text: str, output_format: OutputFormat) -> ExtractionResult[str]:
        return ExtractionResult(data=text, is_success=True) 

class CodeBlockExtractor(Extractor[str]):
    """Extractor that extracts data from code blocks."""
    
    def extract(self, text: str, output_format: OutputFormat) -> ExtractionResult[str]:
        # Find content between ```xxx and ```
        start = text.find(f"```{output_format.output_format_type}")
        if start == -1:
            start = text.find("```")  # Try to find regular code block
        
        if start == -1:
            return ExtractionResult(
                is_success=False,
                error_message=f"{output_format.output_format_type} code block not found",
                error_type=OutputExtractionErrorType.EXTRACTION
            )
            
        # Skip ```xxx or ```
        start = text.find("\n", start) + 1
        end = text.find("```", start)
        
        if end == -1:
            return ExtractionResult(
                is_success=False,
                error_message=f"{output_format.output_format_type} code block not properly closed",
                error_type=OutputExtractionErrorType.EXTRACTION
            )
            
        data = text[start:end].strip()
        
        return ExtractionResult(data=data, is_success=True)


class JsonDirectExtractor(Extractor[Dict]):
    """Extractor that directly parses JSON."""
    
    def extract(self, text: str, output_format: Optional[OutputFormat]) -> ExtractionResult[Dict]:
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                return ExtractionResult(
                    is_success=False,
                    error_message="Extracted data is not a JSON object",
                    error_type=OutputExtractionErrorType.EXTRACTION
                )
            return ExtractionResult(data=data, is_success=True)
        except json.JSONDecodeError as e:
            return ExtractionResult(
                is_success=False,
                error_message=f"JSON parsing error: {str(e)}",
                error_type=OutputExtractionErrorType.EXTRACTION
            )


class JsonCodeBlockExtractor(Extractor[Dict]):
    """Extractor that extracts JSON from code blocks."""
    
    def extract(self, text: str, output_format: OutputFormat) -> ExtractionResult[Dict]:
        result = CodeBlockExtractor().extract(text, output_format)
        # If extraction failed, return the result
        if not result.is_success:
            return ExtractionResult(
                is_success=False,
                error_messages=result.error_messages,
                error_type=OutputExtractionErrorType.EXTRACTION
            )
        
        # If extraction succeeded, parse the data
        try:
            data = json.loads(result.data)
            
            if not isinstance(data, dict):
                return ExtractionResult(
                    is_success=False,
                    error_message="Extracted data is not a JSON object",
                    error_type=OutputExtractionErrorType.EXTRACTION
                )
                
            return ExtractionResult(data=data, is_success=True)
            
        except json.JSONDecodeError as e:
            return ExtractionResult(
                is_success=False,
                error_message=f"JSON parsing error: {str(e)}",
                error_type=OutputExtractionErrorType.EXTRACTION
            )

