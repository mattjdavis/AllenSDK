conda update anaconada
source activate root
pip install -r requirements.txt
pip install -r test_requirements.txt
conda env create -n py27 python=2.7 -f shared/environment.yml
conda install -n py27 -c https://conda.anaconda.org/simpleitk SimpleITK
source activate py27
pip install --upgrade pip
pip install --ignore-installed -r requirements.txt
pip install --ignore-installed -r test_requirements.txt