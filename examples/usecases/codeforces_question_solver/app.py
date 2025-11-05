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


import os
import re
import streamlit as st
from dotenv import load_dotenv
import json

# Import CAMEL components
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import CodeExecutionToolkit, MathToolkit
from camel.types import ModelPlatformType, ModelType
from camel.loaders import Firecrawl

load_dotenv()

class ProblemSolver:
    """Main problem solver with CAMEL agents"""
    
    def __init__(self):
        # Initialize model
        self.model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O,
            model_config_dict={"temperature": 0.1, "max_tokens": 4000}
        )
        
        # Initialize toolkits
        self.code_toolkit = CodeExecutionToolkit()
        self.code_tools = self.code_toolkit.get_tools()
        self.math_tools = MathToolkit().get_tools()
        
        # Create main agent
        self.agent = ChatAgent(
            model=self.model,
            tools=[*self.code_tools, *self.math_tools],
            system_message=self._get_system_message()
        )
        
        # Initialize Firecrawl
        self.firecrawl = Firecrawl()
    
    def _get_system_message(self):
        return """You are an expert competitive programming solver.
        
        Your role:
        1. Analyze competitive programming problems
        2. Generate clean, efficient Python solutions
        3. Fix bugs in solutions based on test failures
        
        Requirements:
        - Use only standard library imports
        - Read input using input() and print output using print()
        - Write clean, efficient code
        - Handle edge cases properly
        - Provide ONLY executable Python code when generating solutions
        """
    
    def fetch_content(self, url: str) -> str:
        """Fetch content from URL"""
        try:
            result = self.firecrawl.scrape(url, params={'formats': ['markdown']})
            if isinstance(result, dict):
                return result.get('markdown', result.get('content', ''))
            return str(result)
        except Exception as e:
            raise Exception(f"Failed to fetch content: {str(e)}")
    
    def solve_problem(self, problem_content: str) -> str:
        """Generate solution for the problem"""
        query = f"""
        Solve this competitive programming problem:
        
        {problem_content}
        
        Provide ONLY the complete, executable Python code.
        """
        
        response = self.agent.step(query)
        return self._extract_code(response.msgs[0].content.strip())
    
    def debug_solution(self, code: str, problem_content: str, failed_tests: list) -> str:
        """Debug and fix the solution"""
        query = f"""
        Fix this failing solution:
        
        PROBLEM:
        {problem_content}
        
        CURRENT CODE:
        {code}
        
        FAILED TESTS:
        {json.dumps(failed_tests, indent=2)}
        
        Provide the corrected Python code.
        """
        
        response = self.agent.step(query)
        return self._extract_code(response.msgs[0].content.strip())
    
    def run_test(self, code: str, test_input: str, expected_output: str) -> dict:
        """Run a single test case using CAMEL's code execution"""
        try:
            # Escape the test input to handle newlines and quotes properly
            escaped_input = test_input.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            
            # Create a test script that handles input/output
            test_code = f'''
import sys
from io import StringIO

# Redirect stdin to provide test input
original_stdin = sys.stdin
sys.stdin = StringIO("""{escaped_input}""")

# Redirect stdout to capture output
original_stdout = sys.stdout
sys.stdout = StringIO()

error_occurred = False
error_message = ""

try:
    # Execute the solution code
{self._indent_code(code, 4)}
    
    # Get the output
    output = sys.stdout.getvalue().strip()
    
except Exception as e:
    error_occurred = True
    error_message = str(e)
    output = ""
    
finally:
    # Restore original stdin/stdout
    sys.stdin = original_stdin
    sys.stdout = original_stdout

# Print results
if error_occurred:
    print(f"ERROR: {{error_message}}")
else:
    print(output)
'''
            
            # Use CAMEL's code execution toolkit
            execution_result = self.code_toolkit.execute_code(test_code)
            
            # Handle different return types from CAMEL
            if isinstance(execution_result, dict):
                # If it's a dictionary, use the existing logic
                if execution_result.get('error'):
                    return {
                        'passed': False,
                        'error': f"Runtime error: {execution_result['error']}",
                        'actual': execution_result.get('output', '').strip(),
                        'expected': expected_output.strip()
                    }
                actual_output = execution_result.get('output', '').strip()
            else:
                # If it's a string (more likely), use it directly
                result_str = str(execution_result).strip()
                
                # Extract actual output from CAMEL's execution result
                # Look for the pattern "> Executed Results:" and get everything after it
                if "> Executed Results:" in result_str:
                    actual_output = result_str.split("> Executed Results:")[-1].strip()
                elif "ERROR: " in result_str:
                    # Extract error message
                    error_start = result_str.find("ERROR: ")
                    error_msg = result_str[error_start + 7:].split('\n')[0]
                    return {
                        'passed': False,
                        'error': f"Runtime error: {error_msg}",
                        'actual': "",
                        'expected': expected_output.strip()
                    }
                else:
                    # Fallback: use the entire result
                    actual_output = result_str
            
            expected = expected_output.strip()
            
            return {
                'passed': actual_output == expected,
                'actual': actual_output,
                'expected': expected,
                'error': None if actual_output == expected else "Output mismatch"
            }
            
        except Exception as e:
            return {
                'passed': False,
                'error': f"Execution error: {str(e)}",
                'actual': "",
                'expected': expected_output.strip()
            }
    
    def _indent_code(self, code: str, spaces: int) -> str:
        """Indent code by specified number of spaces"""
        indent = ' ' * spaces
        return '\n'.join(indent + line if line.strip() else line for line in code.split('\n'))
    
    def _extract_code(self, response: str) -> str:
        """Extract Python code from response"""
        # Try to find code block
        patterns = [
            r'```python\s*(.*?)\s*```',
            r'```py\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                code = match.group(1).strip()
                if self._is_valid_python(code):
                    return code
        
        # If no blocks found, try the whole response
        if self._is_valid_python(response):
            return response
        
        return response
    
    def _is_valid_python(self, code: str) -> bool:
        """Check if code is valid Python"""
        try:
            compile(code, '<string>', 'exec')
            return True
        except:
            return False

class CodeforcesSolver(ProblemSolver):
    """Codeforces-specific solver"""
    
    def build_url(self, problem_id: str) -> str:
        """Build Codeforces URL from problem ID"""
        contest_id = ''.join(filter(str.isdigit, problem_id))
        index = ''.join(filter(str.isalpha, problem_id)).upper()
        return f"https://codeforces.com/contest/{contest_id}/problem/{index}"
    
    def extract_samples(self, content: str) -> list:
        """Extract test samples from problem content"""
        samples = []
        
        # Pattern to match input/output blocks
        patterns = [
            re.compile(r'###\s*Input\s*```(?:\w+)?\s*(.*?)```.*?###\s*Output\s*```(?:\w+)?\s*(.*?)```', re.DOTALL | re.IGNORECASE),
            re.compile(r'(?:Input|input)\s*(?:Copy)?\s*```(?:\w+)?\s*(.*?)```.*?(?:Output|output)\s*(?:Copy)?\s*```(?:\w+)?\s*(.*?)```', re.DOTALL | re.IGNORECASE),
        ]
        
        for pattern in patterns:
            matches = pattern.findall(content)
            for inp, out in matches:
                inp_clean = inp.strip()
                out_clean = out.strip()
                if inp_clean and out_clean:
                    samples.append((inp_clean, out_clean))
            if samples:
                break
        
        return samples[:5]  # Limit to 5 samples

class LeetCodeSolver(ProblemSolver):
    """LeetCode-specific solver"""
    
    def __init__(self):
        super().__init__()
        # Override system message for LeetCode
        self.agent = ChatAgent(
            model=self.model,
            tools=[*self.code_tools, *self.math_tools],
            system_message=self._get_leetcode_system_message()
        )
    
    def _get_leetcode_system_message(self):
        return """You are an expert LeetCode problem solver.
        
        Your role:
        1. Analyze LeetCode problems
        2. Generate clean, efficient Python solutions using class-based approach
        3. Focus on algorithmic efficiency and clean code structure
        
        Requirements:
        - Write solutions as class methods (class Solution: def method_name(self, ...))
        - Use appropriate data structures and algorithms
        - Handle edge cases properly
        - Write clean, well-commented code
        - Provide ONLY the complete Solution class when generating solutions
        """
    
    def build_url(self, problem_slug: str) -> str:
        """Build LeetCode URL from problem slug"""
        return f"https://leetcode.com/problems/{problem_slug}/"
    
    def extract_samples(self, content: str) -> list:
        """Extract test samples from LeetCode problem content"""
        samples = []
        
        # More precise patterns for LeetCode examples
        patterns = [
            # Pattern 1: Example X: Input: ... Output: ...
            re.compile(r'Example\s*\d+:\s*Input:\s*([^\n]+)\s*Output:\s*([^\n]+)', re.IGNORECASE),
            # Pattern 2: Input: ... Output: ... (without Example prefix)
            re.compile(r'(?:^|\n)Input:\s*([^\n]+)\s*Output:\s*([^\n]+)', re.IGNORECASE | re.MULTILINE),
        ]
        
        for pattern in patterns:
            matches = pattern.findall(content)
            for inp, out in matches:
                # Clean up the input and output
                inp_clean = self._clean_sample_text(inp)
                out_clean = self._clean_sample_text(out)
                
                if inp_clean and out_clean:
                    samples.append((inp_clean, out_clean))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_samples = []
        for sample in samples:
            if sample not in seen:
                seen.add(sample)
                unique_samples.append(sample)
        
        return unique_samples[:5]  # Limit to 5 samples
    
    def _clean_sample_text(self, text: str) -> str:
        """Clean sample text by removing markdown and extra formatting"""
        if not text:
            return ""
        
        # Remove markdown code blocks
        text = re.sub(r'```[^`]*```', '', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common prefixes/suffixes
        text = re.sub(r'^(Input:|Output:)\s*', '', text, flags=re.IGNORECASE)
        
        return text.strip()

def solve_problem(platform: str, problem_id: str) -> bool:
    """Main solving function"""
    try:
        # Initialize solver
        if platform == "Codeforces":
            solver = CodeforcesSolver()
            url = solver.build_url(problem_id)
        elif platform == "LeetCode":
            solver = LeetCodeSolver()
            url = solver.build_url(problem_id)
        else:
            st.error("Unsupported platform")
            return False
        
        # Store solver in session state
        st.session_state.solver = solver
        st.session_state.platform = platform
        
        # Fetch problem content
        with st.spinner("Fetching problem..."):
            content = solver.fetch_content(url)
            if not content:
                st.error("Could not fetch problem content")
                return False
        
        st.session_state.problem_content = content
        
        # Extract samples if available
        if hasattr(solver, 'extract_samples'):
            samples = solver.extract_samples(content)
            st.session_state.samples = samples
            if samples:
                st.success(f"Found {len(samples)} test cases")
        
        # Generate solution
        with st.spinner("Generating solution..."):
            code = solver.solve_problem(content)
            st.session_state.generated_code = code
        
        st.session_state.problem_solved = True
        return True
        
    except Exception as e:
        st.error(f"Solving failed: {str(e)}")
        return False

def improve_solution(max_attempts: int = 5) -> bool:
    """Iteratively improve solution (only for Codeforces)"""
    if 'solver' not in st.session_state:
        st.error("No solver available")
        return False
    
    # Only allow improvement for Codeforces
    if st.session_state.get('platform') != 'Codeforces':
        st.info("Auto-fix is only available for Codeforces problems")
        return False
    
    solver = st.session_state.solver
    samples = st.session_state.get('samples', [])
    
    if not samples:
        st.info("No test cases to validate")
        return True
    
    for attempt in range(max_attempts):
        st.info(f"Improvement attempt {attempt + 1}/{max_attempts}...")
        
        # Test current solution
        failed_tests = []
        for idx, (test_input, expected_output) in enumerate(samples):
            result = solver.run_test(st.session_state.generated_code, test_input, expected_output)
            if not result['passed']:
                failed_tests.append({
                    'test_id': idx + 1,
                    'input': test_input,
                    'expected': expected_output,
                    'actual': result['actual'],
                    'error': result['error']
                })
        
        if not failed_tests:
            st.success(f"Success! Solution works after {attempt + 1} attempts!")
            return True
        
        # Debug and improve
        with st.spinner("Debugging..."):
            improved_code = solver.debug_solution(
                st.session_state.generated_code,
                st.session_state.problem_content,
                failed_tests
            )
            st.session_state.generated_code = improved_code
    
    st.error(f"Could not fix solution after {max_attempts} attempts")
    return False

def display_results():
    """Display solution and test results"""
    if not st.session_state.get('problem_solved', False):
        return
    
    platform = st.session_state.get('platform', '')
    
    st.subheader("Generated Solution")
    st.code(st.session_state.generated_code, language='python')
    
    # Show test results
    if st.session_state.get('samples'):
        st.subheader("Test Cases")
        
        if platform == "LeetCode":
            # For LeetCode, only display test cases without running them
            for idx, (test_input, expected_output) in enumerate(st.session_state.samples):
                with st.expander(f"Test Case {idx + 1}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text("Input:")
                        st.code(test_input)
                    with col2:
                        st.text("Expected Output:")
                        st.code(expected_output)
        
        elif platform == "Codeforces":
            # For Codeforces, run and display test results
            solver = st.session_state.solver
            for idx, (test_input, expected_output) in enumerate(st.session_state.samples):
                result = solver.run_test(st.session_state.generated_code, test_input, expected_output)
                
                with st.expander(f"Test Case {idx + 1} {'✅' if result['passed'] else '❌'}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.text("Input:")
                        st.code(test_input)
                    with col2:
                        st.text("Expected:")
                        st.code(expected_output)
                    with col3:
                        st.text("Actual:")
                        st.code(result['actual'])
                    
                    if not result['passed']:
                        st.error(f"Error: {result['error']}")

def main():
    st.title("🚀 CAMEL Problem Solver")
    
    # Initialize session state
    if 'problem_solved' not in st.session_state:
        st.session_state.problem_solved = False
    
    # Input section
    col1, col2 = st.columns([1, 2])
    with col1:
        platform = st.selectbox("Platform:", ["Codeforces", "LeetCode"])
    
    with col2:
        if platform == "Codeforces":
            problem_id = st.text_input("Problem ID (e.g., 2114B):")
        elif platform == "LeetCode":
            problem_id = st.text_input("Problem slug (e.g., reverse-integer):")
    
    # Solve button
    if st.button("🚀 Solve Problem", type="primary") and problem_id:
        if solve_problem(platform, problem_id):
            st.rerun()
    
    # Display results
    display_results()
    
    # Improvement section (only for Codeforces)
    if st.session_state.get('problem_solved', False) and st.session_state.get('platform') == 'Codeforces':
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            max_attempts = st.selectbox("Max attempts:", [3, 5, 10], index=1)
        with col2:
            if st.button("🔧 Auto-Fix", type="primary"):
                if improve_solution(max_attempts):
                    st.rerun()

if __name__ == "__main__":
    main()