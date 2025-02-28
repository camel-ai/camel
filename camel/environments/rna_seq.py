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

import asyncio
import random
from typing import Any, Dict, List, Optional, Tuple

from camel.agents import ChatAgent
from camel.datasets.rna_seq import RNASeqDataset
from camel.environments.base import BaseEnvironment, Observation, StepResult
from camel.extractors.rna_seq import RNASeqExtractor
from camel.logger import get_logger
from camel.verifiers.models import Response, TaskType, VerificationResult, VerificationStatus
from camel.verifiers.rna_seq import RNASeqVerifier

logger = get_logger(__name__)


class RNASeqEnvironment(BaseEnvironment):
    r"""Environment for RNA-seq analysis tasks.
    
    This environment manages the complete workflow for RNA-seq analysis:
    1. Data loading and preprocessing
    2. Differential expression analysis
    3. Pathway enrichment analysis
    4. Quality control verification
    5. Chain-of-thought reasoning validation
    
    Key Features:
    - Specialized RNA-seq dataset handling
    - Bioinformatics-aware verification
    - Automated quality control checks
    - Pathway enrichment validation
    - Statistical significance testing
    """
    
    def __init__(
        self,
        dataset: RNASeqDataset,
        verifier: Optional[RNASeqVerifier] = None,
        extractor: Optional[RNASeqExtractor] = None,
        max_steps: Optional[int] = None,
        teacher_agent: Optional[ChatAgent] = None,
        generator_agent: Optional[ChatAgent] = None,
        p_value_threshold: float = 0.05,
        fold_change_threshold: float = 1.5,
        min_pathway_genes: int = 5,
        curriculum_config: Optional[Dict[str, Any]] = None,
        practice_env_config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        r"""Initialize the RNA-seq environment.
        
        Args:
            dataset: RNA-seq dataset to sample from
            verifier: Verifier for RNA-seq analysis results
            extractor: Extractor for RNA-seq outputs
            max_steps: Maximum steps per episode
            teacher_agent: Agent for providing hints and feedback
            generator_agent: Agent for generating new RNA-seq problems
            p_value_threshold: Threshold for statistical significance
            fold_change_threshold: Minimum fold change for DE genes
            min_pathway_genes: Minimum genes for pathway enrichment
            curriculum_config: Configuration for curriculum learning
            practice_env_config: Configuration for practice environments
            **kwargs: Additional environment parameters
        """
        # Create default components if not provided
        if verifier is None:
            verifier = RNASeqVerifier(
                p_value_threshold=p_value_threshold,
                fold_change_threshold=fold_change_threshold,
                min_pathway_genes=min_pathway_genes,
            )
        
        if extractor is None:
            extractor = RNASeqExtractor()
        
        super().__init__(
            dataset=dataset,
            verifier=verifier,
            extractor=extractor,
            max_steps=max_steps,
            task_type=TaskType.COMPUTATIONAL_BIOLOGY,
            teacher_agent=teacher_agent,
            generator_agent=generator_agent,
            curriculum_config=curriculum_config,
            practice_env_config=practice_env_config,
            **kwargs,
        )
        
        # RNA-seq specific parameters
        self.p_value_threshold = p_value_threshold
        self.fold_change_threshold = fold_change_threshold
        self.min_pathway_genes = min_pathway_genes
        
        # Track analysis progress
        self._analysis_state = {
            "quality_control_passed": False,
            "differential_expression_completed": False,
            "pathway_analysis_completed": False,
            "reasoning_validated": False,
        }
    
    async def setup(self) -> None:
        r"""Set up the RNA-seq environment."""
        await super().setup()
        
        # Additional RNA-seq specific setup
        logger.info("Setting up RNA-seq environment")
        
        # Initialize analysis state
        self._analysis_state = {
            "quality_control_passed": False,
            "differential_expression_completed": False,
            "pathway_analysis_completed": False,
            "reasoning_validated": False,
        }
    
    async def teardown(self) -> None:
        r"""Clean up RNA-seq environment resources."""
        logger.info("Tearing down RNA-seq environment")
        await super().teardown()
    
    async def reset(self) -> Observation:
        r"""Reset the RNA-seq environment.
        
        Returns:
            Initial observation with RNA-seq problem
        """
        observation = await super().reset()
        
        # Reset RNA-seq specific state
        self._analysis_state = {
            "quality_control_passed": False,
            "differential_expression_completed": False,
            "pathway_analysis_completed": False,
            "reasoning_validated": False,
        }
        
        logger.info("RNA-seq environment reset with new problem")
        return observation
    
    def _get_initial_state(self) -> Dict[str, Any]:
        r"""Get initial RNA-seq environment state."""
        state = super()._get_initial_state()
        
        # Add RNA-seq specific state
        state.update({
            "p_value_threshold": self.p_value_threshold,
            "fold_change_threshold": self.fold_change_threshold,
            "min_pathway_genes": self.min_pathway_genes,
            "analysis_progress": 0.0,
            "quality_metrics": {},
        })
        
        return state
    
    def _get_next_observation(self) -> Observation:
        r"""Get the next RNA-seq problem observation."""
        observation = super()._get_next_observation()
        
        # Add RNA-seq specific context
        if observation and hasattr(observation, 'context'):
            observation.context.update({
                "p_value_threshold": self.p_value_threshold,
                "fold_change_threshold": self.fold_change_threshold,
                "min_pathway_genes": self.min_pathway_genes,
                "analysis_state": self._analysis_state,
            })
        
        return observation
    
    def _get_terminal_observation(self) -> Observation:
        r"""Get terminal observation for RNA-seq environment."""
        observation = super()._get_terminal_observation()
        
        # Add RNA-seq specific terminal information
        if observation:
            observation.context["analysis_summary"] = {
                "completed": all(self._analysis_state.values()),
                "progress": sum(1 for v in self._analysis_state.values() if v) / len(self._analysis_state),
                "state": self._analysis_state.copy(),
            }
        
        return observation
    
    async def step(self, response: Response) -> StepResult:
        r"""Take a step in the RNA-seq environment.
        
        Args:
            response: Response containing RNA-seq analysis
            
        Returns:
            StepResult with next observation, rewards, and info
        """
        # Process the step using parent implementation
        step_result = await super().step(response)
        
        # Update RNA-seq specific state based on verification results
        if "verification_result" in step_result.info:
            verification_result = step_result.info["verification_result"]
            self._update_analysis_state(verification_result, step_result.info.get("extraction_result", {}))
        
        # Update progress in state
        self._state["analysis_progress"] = sum(1 for v in self._analysis_state.values() if v) / len(self._analysis_state)
        
        return step_result
    
    def _update_analysis_state(self, verification_result: VerificationResult, extraction_result: Dict[str, Any]) -> None:
        r"""Update RNA-seq analysis state based on verification results.
        
        Args:
            verification_result: Result from the verifier
            extraction_result: Extracted components from response
        """
        # Check if verification was successful
        if verification_result.status == VerificationStatus.SUCCESS:
            # Update quality control status
            if "quality_control" in extraction_result and extraction_result["quality_control"]:
                self._analysis_state["quality_control_passed"] = True
            
            # Update differential expression status
            if "differential_expression" in extraction_result and extraction_result["differential_expression"]:
                self._analysis_state["differential_expression_completed"] = True
            
            # Update pathway analysis status
            if "pathway_analysis" in extraction_result and extraction_result["pathway_analysis"]:
                self._analysis_state["pathway_analysis_completed"] = True
            
            # Update reasoning validation status
            if "reasoning" in extraction_result and extraction_result["reasoning"]:
                self._analysis_state["reasoning_validated"] = True
    
    async def compute_reward(self, response: Response, extraction_result: Dict[str, Any], verification_result: VerificationResult) -> Dict[str, float]:
        r"""Compute rewards for RNA-seq analysis.
        
        Args:
            response: The response containing RNA-seq analysis
            extraction_result: Extracted components from response
            verification_result: Result from the verifier
            
        Returns:
            Dictionary of reward scores for different aspects
        """
        # Get base rewards from parent implementation
        rewards = await super().compute_reward(response, extraction_result, verification_result)
        
        # Add RNA-seq specific rewards
        if verification_result.score:
            # Add component-specific rewards if available
            for component, score in verification_result.score.items():
                rewards[component] = score
        
        # Reward for completing analysis steps
        analysis_progress = sum(1 for v in self._analysis_state.values() if v) / len(self._analysis_state)
        rewards["analysis_progress"] = analysis_progress
        
        # Bonus for completing all analysis steps
        if all(self._analysis_state.values()):
            rewards["completion_bonus"] = 1.0
        
        return rewards
    
    def _is_done(self) -> bool:
        r"""Check if RNA-seq analysis episode is complete."""
        # Check parent termination conditions
        if super()._is_done():
            return True
        
        # Episode is done if all analysis steps are completed
        return all(self._analysis_state.values())
    
    async def generate_hint(self, response: Response) -> str:
        r"""Generate a hint for RNA-seq analysis.
        
        Args:
            response: Current response with analysis attempt
            
        Returns:
            Hint text for improving the analysis
        """
        if not self.teacher_agent:
            return "No teacher agent available for hints."
        
        # Determine which analysis step needs help
        missing_steps = [step for step, completed in self._analysis_state.items() if not completed]
        
        if not missing_steps:
            return "All analysis steps are completed successfully!"
        
        # Focus hint on the first missing step
        focus_step = missing_steps[0]
        
        # Create a prompt for the teacher agent
        prompt = f"""The student is working on RNA-seq analysis and needs help with {focus_step}.
        
        Current analysis state:
        {self._analysis_state}
        
        Their current response:
        {response.llm_response}
        
        Please provide a helpful hint to improve their {focus_step} without giving away the complete solution.
        """
        
        # Get hint from teacher agent
        self.teacher_agent.reset()
        teacher_response = await self.teacher_agent.step(prompt)
        
        return teacher_response.msg.content
    
    async def generate_practice_problem(self) -> Dict[str, Any]:
        r"""Generate a practice RNA-seq problem.
        
        Returns:
            Dictionary with practice problem data
        """
        if not self.generator_agent:
            return {"error": "No generator agent available for practice problems."}
        
        # Determine which analysis step needs practice
        missing_steps = [step for step, completed in self._analysis_state.items() if not completed]
        
        if not missing_steps:
            # If all steps completed, randomly choose one to practice more
            focus_step = random.choice(list(self._analysis_state.keys()))
        else:
            # Focus on the first missing step
            focus_step = missing_steps[0]
        
        # Create a prompt for the generator agent
        prompt = f"""Generate a practice RNA-seq analysis problem focusing on {focus_step}.
        
        The problem should include:
        1. A brief description of the experimental setup
        2. Sample RNA-seq data relevant to {focus_step}
        3. Expected analysis steps
        4. A ground truth solution
        
        Make the problem appropriate for someone who is struggling with {focus_step}.
        """
        
        # Get practice problem from generator agent
        self.generator_agent.reset()
        generator_response = await self.generator_agent.step(prompt)
        
        # Extract problem components
        extraction_result = await self.extractor.extract(generator_response.msg.content)
        
        return {
            "problem": extraction_result.get("question", ""),
            "data": extraction_result.get("differential_expression", {}),
            "ground_truth": extraction_result.get("ground_truth", ""),
            "focus_step": focus_step,
            "raw_response": generator_response.msg.content,
        }