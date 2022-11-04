#!/bin/sh

TMP_DIR=tmp/python
Template_DIR=templates

# create dirs
mkdir -p $TMP_DIR
mkdir -p $Template_DIR

# ensure python 3.9
python3.9 -m venv $TMP_DIR/py39-venv
. $TMP_DIR/py39-venv/bin/activate
pip install --upgrade pip
# add dependencies from requirements.txt (without pandas and numpy)
pip install --target=$TMP_DIR -r requirements.txt
deactivate
rm -r $TMP_DIR/py39-venv

cd $TMP_DIR 
rm -r *.dist-info __pycache__
cd ..
pwd
zip -FSr ../$Template_DIR/layer.zip . *
cd ..

# cleanup
rm -r $TMP_DIR