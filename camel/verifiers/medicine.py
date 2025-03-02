# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
from typing import Dict, Any, List, Optional, Set, Type
import re
from datetime import datetime
from types import TracebackType

from typing_extensions import Self

from .base import BaseVerifier
from .models import (
    Response,
    VerificationResult,
    VerificationStatus,
    TaskType,
)


class MedicalVerifier(BaseVerifier):
    """Medical domain verifier for validating medical responses.

    This verifier performs specialized checks for medical content:
    1. ICD Code validation
    2. Drug interaction checking
    3. Treatment protocol compliance
    4. Medical terminology accuracy
    5. Evidence-based practice alignment
    """

    def __init__(
        self,
        icd_code_pattern: str = r'^[A-Z][0-9]{2}(\.[0-9]{1,2})?$',
        required_fields: Optional[Set[str]] = None,
        min_confidence_score: float = 0.7,
        **kwargs,
    ):
        """Initialize the medical verifier.

        Args:
            icd_code_pattern: Regex pattern for valid ICD-10 codes
                (default: r'^[A-Z][0-9]{2}([.][0-9]{1,2})?$')
            required_fields: Set of required fields in medical responses
                (default: None, will use standard medical fields)
            min_confidence_score: Minimum confidence score for validations
                (default: 0.7)
            **kwargs: Additional verifier parameters
        """
        super().__init__(**kwargs)
        self._icd_pattern = re.compile(icd_code_pattern)
        self._min_confidence = min_confidence_score
        self._required_fields = required_fields or {
            'symptoms',
            'diagnosis',
            'treatment',
            'icd_codes',
        }

        # Initialize medical knowledge base (could be expanded)
        self._common_drug_interactions = {
            ('warfarin', 'aspirin'): 'Increased bleeding risk',
            ('ACE inhibitors', 'potassium supplements'): 'Hyperkalemia risk',
            ('clarithromycin', 'simvastatin'): 'Increased statin toxicity',
            ('metformin', 'contrast media'): 'Risk of lactic acidosis',
            ('NSAIDS', 'SSRIs'): 'Increased bleeding risk',
            ('amiodarone', 'warfarin'): 'Enhanced anticoagulation effect',
            ('fluoroquinolones', 'steroids'): 'Increased tendon rupture risk',
        }

        # 添加疾病治疗指南
        self._treatment_guidelines = {
            'STEMI': {
                'required_treatments': ['aspirin', 'pci', 'anticoagulation'],
                'recommended_timing': 'immediate',
                'confidence': 0.9,
            },
            '高血压危象': {
                'required_treatments': ['降压', '监测'],
                'recommended_drugs': ['拉贝洛尔', '硝普钠', '乌拉地尔'],
                'confidence': 0.85,
            },
            '脑梗塞': {
                'required_treatments': ['溶栓', '抗血小板'],
                'time_window': '4.5h',
                'confidence': 0.9,
            },
        }

        # 添加症状-诊断关联规则
        self._symptom_diagnosis_rules = {
            'STEMI': {
                'required_symptoms': ['胸痛', 'chest pain'],
                'supporting_evidence': ['ST抬高', 'ST elevation'],
                'key_tests': ['troponin', '肌钙蛋白'],
            },
            '高血压危象': {
                'required_symptoms': ['头痛', 'headache', '视物模糊', 'blurred vision'],
                'supporting_evidence': ['血压升高', 'high blood pressure'],
                'key_tests': ['眼底检查', 'fundus examination'],
            },
        }

    async def __aenter__(self) -> Self:
        """Async context manager entry.
        
        Returns:
            Self: The verifier instance
        """
        await self.setup()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Async context manager exit.
        
        Args:
            exc_type: Exception type if an error occurred
            exc_val: Exception instance if an error occurred
            exc_tb: Exception traceback if an error occurred
        """
        await self.cleanup()

    def _validate_icd_code(self, code: str) -> bool:
        """Validate ICD-10 code format.

        Args:
            code: ICD-10 code to validate

        Returns:
            bool: Whether the code is valid
        """
        return bool(self._icd_pattern.match(code))

    def _check_drug_interactions(
        self, medications: List[str]
    ) -> List[Dict[str, Any]]:
        """Check for known drug interactions.

        Args:
            medications: List of medications to check

        Returns:
            List[Dict[str, Any]]: List of found interactions with warnings
        """
        interactions = []
        meds_lower = [med.lower() for med in medications]
        
        for (drug1, drug2), warning in self._common_drug_interactions.items():
            if drug1.lower() in meds_lower and drug2.lower() in meds_lower:
                interactions.append({
                    'drugs': [drug1, drug2],
                    'warning': warning,
                })
        
        return interactions

    def _validate_treatment_protocol(
        self, diagnosis: str, treatment: str
    ) -> Dict[str, Any]:
        """Validate treatment protocol against standard guidelines.

        Args:
            diagnosis: The diagnosis to check
            treatment: The treatment plan to validate

        Returns:
            Dict[str, Any]: Validation results including compliance score
        """
        validation = {
            'compliant': True,
            'confidence': 0.8,
            'guidelines_referenced': [],
            'warnings': [],
        }
        
        # 转换为小写以进行比较
        diagnosis_lower = diagnosis.lower()
        treatment_lower = treatment.lower()
        
        # 查找匹配的指南
        for condition, guide in self._treatment_guidelines.items():
            if condition.lower() in diagnosis_lower:
                validation['guidelines_referenced'].append(condition)
                
                # 检查必需治疗措施
                missing_treatments = [
                    t for t in guide['required_treatments']
                    if t.lower() not in treatment_lower
                ]
                
                if missing_treatments:
                    validation.update({
                        'compliant': False,
                        'warnings': [
                            f"Missing required treatments: {', '.join(missing_treatments)}"
                        ],
                    })
                
                # 更新置信度
                validation['confidence'] = guide['confidence']
                
                # 检查推荐药物（如果有）
                if 'recommended_drugs' in guide:
                    recommended = [
                        d for d in guide['recommended_drugs']
                        if d.lower() in treatment_lower
                    ]
                    if recommended:
                        validation['confidence'] *= 1.1  # 提高置信度
                
                break
        
        return validation

    def _validate_diagnosis(
        self,
        symptoms: str,
        diagnosis: str,
        medical_content: Dict[str, Any],
    ) -> Dict[str, Any]:
        """验证诊断的准确性。

        Args:
            symptoms: 症状描述
            diagnosis: 诊断结果
            medical_content: 完整的医疗内容

        Returns:
            Dict[str, Any]: 验证结果
        """
        validation = {
            'accurate': True,
            'confidence': 0.7,
            'warnings': [],
        }

        # 转换为小写以进行比较
        symptoms_lower = symptoms.lower()
        diagnosis_lower = diagnosis.lower()

        # 查找匹配的诊断规则
        for condition, rules in self._symptom_diagnosis_rules.items():
            if condition.lower() in diagnosis_lower:
                # 检查必需症状
                required_symptoms = rules['required_symptoms']
                found_symptoms = [
                    s for s in required_symptoms
                    if s.lower() in symptoms_lower
                ]
                
                if not found_symptoms:
                    validation.update({
                        'accurate': False,
                        'warnings': ['Required symptoms not found'],
                        'confidence': 0.3,
                    })
                
                # 检查支持证据
                supporting_evidence = rules['supporting_evidence']
                found_evidence = [
                    e for e in supporting_evidence
                    if any(
                        e.lower() in str(v).lower()
                        for v in medical_content.values()
                    )
                ]
                
                # 根据找到的证据调整置信度
                if found_evidence:
                    validation['confidence'] = min(
                        1.0,
                        validation['confidence'] + 0.1 * len(found_evidence)
                    )
                
                break

        return validation

    async def _verify_implementation(
        self, response: Response
    ) -> VerificationResult:
        """Implement medical-specific verification logic.

        Args:
            response: Response object containing medical content

        Returns:
            VerificationResult: Verification results with medical-specific
                checks
        """
        if response.task_type != TaskType.MEDICINE:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                error_message="Not a medical task",
                timestamp=datetime.now(),
            )

        # Extract medical content
        medical_content = response.verification_info.get('medical_content', {})
        
        # Track validation results
        validations = []
        error_messages = []
        avg_confidence = 0.0
        
        # 1. Check required fields
        missing_fields = self._required_fields - set(medical_content.keys())
        if missing_fields:
            error_messages.append(
                f"Missing required medical fields: {missing_fields}"
            )

        # 2. Validate ICD codes
        icd_codes = medical_content.get('icd_codes', '').split(',')
        invalid_codes = [
            code.strip() for code in icd_codes
            if code.strip() and not self._validate_icd_code(code.strip())
        ]
        if invalid_codes:
            error_messages.append(f"Invalid ICD codes: {invalid_codes}")

        # 3. Check drug interactions
        medications = medical_content.get('treatment', '').split(',')
        interactions = self._check_drug_interactions(medications)
        if interactions:
            validations.append({
                'type': 'drug_interactions',
                'interactions': interactions,
            })

        # 4. Validate treatment protocol
        diagnosis = medical_content.get('diagnosis', '')
        treatment = medical_content.get('treatment', '')
        protocol_validation = self._validate_treatment_protocol(
            diagnosis, treatment
        )
        validations.append({
            'type': 'treatment_protocol',
            'validation': protocol_validation,
        })

        # 5. Validate diagnosis accuracy
        symptoms = medical_content.get('symptoms', '')
        diagnosis_validation = self._validate_diagnosis(
            symptoms, diagnosis, medical_content
        )
        validations.append({
            'type': 'diagnosis_accuracy',
            'validation': diagnosis_validation,
        })

        # Calculate overall confidence score
        confidence_scores = []
        
        # Treatment protocol confidence
        if protocol_validation.get('compliant'):
            confidence_scores.append(protocol_validation.get('confidence', 0))
        
        # Diagnosis accuracy confidence
        if diagnosis_validation.get('accurate'):
            confidence_scores.append(diagnosis_validation.get('confidence', 0))
        
        # Calculate average confidence if we have scores
        if confidence_scores:
            avg_confidence = sum(confidence_scores) / len(confidence_scores)

        # Determine status
        status = (
            VerificationStatus.SUCCESS
            if not error_messages and avg_confidence >= self._min_confidence
            else VerificationStatus.FAILURE
        )

        return VerificationResult(
            status=status,
            error_message='\n'.join(error_messages) if error_messages else None,
            metadata={
                'validations': validations,
                'confidence_score': avg_confidence,
            },
            timestamp=datetime.now(),
        )

    async def verify_batch(
        self,
        responses: List[Response],
        raise_on_error: bool = False,
    ) -> List[VerificationResult]:
        """Verify a batch of medical responses.

        Args:
            responses: List of responses to verify
            raise_on_error: Whether to raise an exception on verification error

        Returns:
            List[VerificationResult]: List of verification results
        """
        results = []
        for response in responses:
            try:
                result = await self.verify(response)
                results.append(result)
            except Exception as e:
                if raise_on_error:
                    raise
                # Create error result
                results.append(
                    VerificationResult(
                        status=VerificationStatus.ERROR,
                        error_message=str(e),
                    )
                )
        return results 