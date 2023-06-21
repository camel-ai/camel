conda create --name camel python=3.10
conda activate camel
conda install pytorch torchvision torchaudio pytorch-cuda=11.7 -c pytorch -c nvidia
pip install -r requirements.txt
pre-commit install
pip install -e .