# Introduction to `TaskPlannerAgent` class

In this tutorial, we will learn the `TextPlannerAgent` class, which is a subclass of the `ChatAgent` class. The `TaskPlannerAgent` class helps divide a task into subtasks based on the input task prompt.The topics covered include:
- Introduction to `TaskPlannerAgent` class
- Creating a `TaskPlannerAgent` instance
- Using the `TaskPlannerAgent` class

## Introduction
The `TaskPlannerAgent` class is a subclass of the `ChatAgent` class. The `TaskPlannerAgent` class helps divide a task into subtasks based on the input task prompt.

## Creating a `TaskPlannerAgent` instance

To create a `TaskPlannerAgent` instance, you need to provide the following arguments:
- `model`:(optional) the type of model to use for the agent. By default, it is set to `ModelType.GPT_3_5_TURBO`.
- `model_config`:(optional) The configuration for the model. By default, it is set to `None`.
- `output_language`:(str, optional) The language to be output by the agent.By default, it is set to `None`.

```python 
model = ModelType.GPT_3_5_TURBO
task_planner_agent = TaskPlannerAgent(
    model_config=ChatGPTConfig(temperature=1.0), 
    model=model
)
```

## Using the `TaskPlannerAgent` class

### The `step` method
Generate subtasks based on the input task prompt.

```python
original_task_prompt = "Modeling molecular dynamics"
print(f"Original task prompt:\n{original_task_prompt}\n")
>>> 'Original task prompt: Modeling molecular dynamics'
task_specify_agent = TaskSpecifyAgent(
    task_type=TaskType.CODE,
    model_config=ChatGPTConfig(temperature=1.0),
    model=model,
)
specified_task_prompt = task_specify_agent.step(
    original_task_prompt, meta_dict=dict(domain="Chemistry",
                                            language="Python"))
print(f"Specified task prompt:\n{specified_task_prompt}\n")
>>> '''Specified task prompt:
Develop a Python program to simulate the diffusion of nanoparticles in a solvent, taking into account the intermolecular forces, particle size, and temperature. Validate the model by comparing the simulation results with experimental data and optimize the code for large-scale simulations with efficient memory usage.'''
task_planner_agent = TaskPlannerAgent(
    model_config=ChatGPTConfig(temperature=1.0), model=model)
planned_task_prompt = task_planner_agent.step(specified_task_prompt)
print(f"Planned task prompt:\n{planned_task_prompt}\n")
>>> '''Planned task prompt:
1. Research intermolecular forces influencing nanoparticle diffusion.
2. Determine how particle size impacts diffusion rate.
3. Study the effect of temperature on nanoparticle diffusion.
4. Design and implement a Python simulation framework for nanoparticle diffusion.
5. Incorporate intermolecular forces, particle size, and temperature into the simulation.
6. Obtain experimental data for comparison with simulation results.
7. Analyze and validate the simulation model against experimental data.
8. Identify areas for code optimization to improve memory usage.
9. Implement code optimizations to enable large-scale simulations.
10. Test the optimized code for large-scale simulations.
11. Evaluate the performance and memory usage of the optimized code.
12. Make any necessary adjustments or further optimizations.'''
```