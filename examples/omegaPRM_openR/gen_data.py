import json
import logging
from datetime import datetime
import yaml
from module import Node, perform_rollouts, process_annotations, calculate_mc_score
from model_utils import LM


def load_config(config_path):
    """
    Load configuration from a YAML file.
    
    Args:
        config_path (str): Path to the YAML configuration file.
        
    Returns:
        dict: A dictionary containing the configuration.
    """
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def load_json_file(file_path):
    """
    Load data from a JSON file.
    
    Args:
        file_path (str): Path to the JSON file.
        
    Returns:
        list: A list of dictionaries containing the problem and final answer.
    """
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def setup_logging(log_file):
    """
    Set up logging configuration to output to file and console.
    
    Args:
        log_file (str): Path to the log file.
    """
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)

    logging.getLogger("openai").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.WARNING)

def main():
    # Load configuration
    config = load_config('config.yaml')
    
    # Get parameters from config
    json_file_path = config['input']['json_file_path']
    log_file_path = config['output']['log_file_path']
    file_prefix = config['output']['file_prefix']
    num_rollouts = config['processing']['num_rollouts']
    initial_rollouts = config['processing']['initial_rollouts']
    max_iterations = config['processing']['max_iterations']
    
    lm_model = LM(model_type=config['model']['model_type'], model_name=config['model']['model_name'], num_rollouts=num_rollouts, **config['model']['model_args'])
    
    # Set up logging
    setup_logging(log_file_path)
    
    # Start the process and log it
    logging.info("Started processing the JSON file.")
    
    # Load the JSON data
    data = load_json_file(json_file_path)
    
    # Process each problem and its final answer
    for i, item in enumerate(data):
        problem = item.get('problem', 'No problem found')
        final_answer = item.get('final_answer', 'No answer found')
        
        # Log each problem and answer
        logging.info(f"Processed Problem {i + 1}: {problem}")
        logging.info(f"Final Answer: {final_answer}")
        
        # Initialize the root node and perform rollouts
        nodes = []
        root_node = Node(problem, "", final_answer)
        rollouts, correctness_flags = perform_rollouts(root_node, lm_model, initial_rollouts)
        mc_score = calculate_mc_score(root_node)
        root_node.mc_score = mc_score

        nodes.append(root_node)

        # Check if further processing is needed
        if 0 < sum(correctness_flags) < initial_rollouts:
            print("Processing annotations ...\n")
            filename = f"{file_prefix}_{i+1}_nodes_data.json"
            process_annotations(problem, nodes, lm_model, filename, max_iterations)
        
    # Log completion
    logging.info("Finished processing the JSON file.")

if __name__ == "__main__":
    main()
