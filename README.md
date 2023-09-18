# RoCo Cont'd

## Setup
### setup conda env and package install
```
conda create -n roco python=3.8 
conda activate roco
```
### Install mujoco and dm_control 
```
pip install mujoco==2.3.0
pip install dm_control==1.0.8 
```

### Install other packages
```
pip install -r requirements.txt
```

### Acquire OpenAI/Claude API Keys
This is required for prompting GPTs or Claude LLMs. You don't necessarily need both of them. Put your key string somewhere safely in your local repo, and provide a file path (something like `./roco/openai_key.json`) and load them in the scripts. 

###
Add mujoco into your environment path
```
export LD_LIBRARY_PATH=/home/user/mujoco-2.3.0/lib:$LD_LIBRARY_PATH
```

## Usage 

### SweepFloor
```
$ conda activate roco
(roco) $ python run_dialog.py --task sweep -llm gpt-4
```
### MoveRope
```
$ conda activate roco
(roco) $ python run_dialog.py --task rope -llm gpt-4
```
### MakeSandwich
```
$ conda activate roco
(roco) $ python run_dialog.py --task sandwich -llm gpt-4
```
### PackGrocery
```
$ conda activate roco
(roco) $ python run_dialog.py --task pack -llm gpt-4
```
### ArrangeCabinet
```
$ conda activate roco
(roco) $ python run_dialog.py --task cabinet -llm gpt-4
```
### SortCubes
```
$ conda activate roco
(roco) $ python run_dialog.py --task sort -llm gpt-4
```

## References
[Arxiv](https://arxiv.org/abs/2307.04738) | [Project Website](https://project-roco.github.io) 